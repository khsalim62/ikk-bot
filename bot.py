"""
bot.py — IKK Group HR Bot
"""
import os
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters,
    ContextTypes
)
from employees import load_employees, find_employee, is_labor, get_display_name
from pdf_filler import fill_leave_form, fill_declaration_form
from email_sender import send_leave_request
from tracker import generate_request_id, save_request, get_request, format_request_status
import signature_server as sig_srv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LANG, IDENTIFY, MAIN_MENU, LEAVE_TYPE, LEAVE_START, LEAVE_RETURN, LEAVE_DEST, LEAVE_CITY_FROM, LEAVE_COUNTRY, LEAVE_PHONE, LEAVE_CONFIRM, LEAVE_DECLARATION, SIGNATURE, TRACK_ID = range(14)

EMPLOYEES = {}
def get_employees():
    global EMPLOYEES
    if not EMPLOYEES:
        EMPLOYEES = load_employees()
    return EMPLOYEES

TEXTS = {
    "ar": {
        "welcome": "👋 أهلاً بك في بوت خدمات الموارد البشرية\nاختر لغتك / Choose your language / اپنی زبان منتخب کریں",
        "enter_id": "🔢 أدخل رقمك الوظيفي أو رقم إقامتك:",
        "not_found": "❌ الرقم غير موجود. تأكد وحاول مجدداً.",
        "not_labor": "⚠️ هذه الخدمة للعمال فقط.",
        "welcome_emp": "✅ مرحباً {name}!\nاختر الخدمة:",
        "menu_leave": "🏖 طلب إجازة",
        "menu_track": "🔍 تتبع طلب",
        "select_leave_type": "اختر نوع الإجازة:",
        "leave_annual": "📅 إجازة سنوية",
        "leave_sick": "🤒 إجازة مرضية",
        "leave_unpaid": "💼 إجازة بدون راتب",
        "enter_start": "📅 تاريخ بداية الإجازة (مثال: 2025-06-01):",
        "enter_return": "📅 تاريخ العودة (مثال: 2025-06-21):",
        "invalid_date": "❌ تاريخ غير صحيح. استخدم: YYYY-MM-DD",
        "return_before": "❌ تاريخ العودة يجب أن يكون بعد تاريخ البداية.",
        "select_dest": "🌍 وجهة الإجازة:",
        "dest_inside": "🇸🇦 داخل المملكة",
        "dest_outside": "✈️ خارج المملكة",
        "enter_city_from": "🏙 من أي مدينة ستغادر؟",
        "enter_country": "🌍 ما البلد المقصود؟",
        "confirm_title": "📋 *ملخص الطلب*\n\n",
        "confirm_yes": "✅ تأكيد",
        "confirm_no": "❌ إلغاء",
        "cancel": "تم الإلغاء. اكتب /start للبدء.",
        "decl_text": "📄 نموذج إقرار — سفر خارج المملكة\n\nأنا الموقع أدناه أقر وأتعهد بأنه في حالة حدوث أي تأخير في عودتي من إجازتي بسبب وضع الحرب الحالي، فإنني سأكون مسؤولاً بالكامل عن أي مصاريف تتحملها الشركة. تشمل: تمديد تأشيرة الخروج والعودة، تغيير تذكرة الطيران، تجديد الإقامة، أو أي تكاليف إدارية أخرى. أفوض الشركة بخصم هذه المصاريف من راتبي. تم تقديم هذا الإقرار طواعية وبفهم كامل.",
        "decl_confirm": "✅ تمت القراءة والموافقة على الإقرار",
        "enter_phone": "📱 أدخل رقم موبايلك:",
        "back": "🔙 رجوع",
        "restart": "🔄 بدء من جديد",
        "idle_msg": "👋 اضغط الزرار للبدء:",
        "enter_track_id": "🔍 أدخل رقم الطلب:",
        "track_not_found": "❌ رقم الطلب غير موجود.",
    },
    "en": {
        "welcome": "👋 Welcome to HR Self-Service Bot\nChoose your language / اختر لغتك / اپنی زبان منتخب کریں",
        "enter_id": "🔢 Enter your Employee ID or Iqama number:",
        "not_found": "❌ ID not found. Please try again.",
        "not_labor": "⚠️ This service is for Labor employees only.",
        "welcome_emp": "✅ Welcome {name}!\nSelect a service:",
        "menu_leave": "🏖 Leave Request",
        "menu_track": "🔍 Track Request",
        "select_leave_type": "Select leave type:",
        "leave_annual": "📅 Annual Leave",
        "leave_sick": "🤒 Sick Leave",
        "leave_unpaid": "💼 Unpaid Leave",
        "enter_start": "📅 Leave start date (e.g. 2025-06-01):",
        "enter_return": "📅 Return date (e.g. 2025-06-21):",
        "invalid_date": "❌ Invalid date. Use: YYYY-MM-DD",
        "return_before": "❌ Return date must be after start date.",
        "select_dest": "🌍 Destination:",
        "dest_inside": "🇸🇦 Inside KSA",
        "dest_outside": "✈️ Outside KSA",
        "enter_city_from": "🏙 Departing city?",
        "enter_country": "🌍 Destination country?",
        "confirm_title": "📋 *Request Summary*\n\n",
        "confirm_yes": "✅ Confirm",
        "confirm_no": "❌ Cancel",
        "cancel": "Cancelled. Type /start to begin.",
        "decl_text": "📄 Declaration Form — Travel Outside KSA\n\nI hereby declare that in the event of any delay in my return from vacation due to the current war situation or any related circumstances, I shall be fully responsible for any expenses incurred by the Company on my behalf. Such expenses may include: ERE visa extension, air ticket changes, Iqama renewal, or any other administrative costs. I authorize the Company to deduct such expenses from my salary. This declaration is made voluntarily and with full understanding of the above terms.",
        "decl_confirm": "✅ I have read and agree to the declaration",
        "enter_phone": "📱 Enter your mobile number:",
        "back": "🔙 Back",
        "restart": "🔄 Start Over",
        "idle_msg": "👋 Press the button to start:",
        "enter_track_id": "🔍 Enter request ID:",
        "track_not_found": "❌ Request ID not found.",
    },
    "ur": {
        "welcome": "👋 HR سیلف سروس بوٹ میں خوش آمدید\nاپنی زبان منتخب کریں",
        "enter_id": "🔢 ملازم نمبر یا اقامہ نمبر درج کریں:",
        "not_found": "❌ نمبر نہیں ملا۔",
        "not_labor": "⚠️ صرف مزدور ملازمین کے لیے۔",
        "welcome_emp": "✅ خوش آمدید {name}!\nخدمت منتخب کریں:",
        "menu_leave": "🏖 چھٹی کی درخواست",
        "menu_track": "🔍 ٹریک کریں",
        "select_leave_type": "چھٹی کی قسم:",
        "leave_annual": "📅 سالانہ چھٹی",
        "leave_sick": "🤒 بیمار چھٹی",
        "leave_unpaid": "💼 بغیر تنخواہ",
        "enter_start": "📅 شروع تاریخ (مثال: 2025-06-01):",
        "enter_return": "📅 واپسی تاریخ (مثال: 2025-06-21):",
        "invalid_date": "❌ غلط تاریخ۔ YYYY-MM-DD",
        "return_before": "❌ واپسی بعد میں ہونی چاہیے۔",
        "select_dest": "🌍 منزل:",
        "dest_inside": "🇸🇦 سعودی عرب میں",
        "dest_outside": "✈️ باہر",
        "enter_city_from": "🏙 روانگی کا شہر؟",
        "enter_country": "🌍 منزل کا ملک؟",
        "confirm_title": "📋 *خلاصہ*\n\n",
        "confirm_yes": "✅ تصدیق",
        "confirm_no": "❌ منسوخ",
        "cancel": "منسوخ۔ /start لکھیں۔",
        "decl_text": "📄 اقرارنامہ — سعودی عرب سے باہر سفر\n\nمیں اعلان کرتا ہوں کہ موجودہ صورتحال کی وجہ سے واپسی میں تاخیر کی صورت میں، میں کمپنی کے تمام اخراجات کا ذمہ دار ہوں گا۔ ان میں ERE ویزا، ہوائی ٹکٹ، اقامہ تجدید شامل ہیں۔ میں کمپنی کو یہ اخراجات تنخواہ سے کاٹنے کا اختیار دیتا ہوں۔ یہ اقرار رضاکارانہ طور پر کیا گیا ہے۔",
        "decl_confirm": "✅ میں نے پڑھ لیا اور اقرار سے متفق ہوں",
        "enter_phone": "📱 موبائل نمبر درج کریں:",
        "back": "🔙 واپس",
        "restart": "🔄 دوبارہ شروع",
        "idle_msg": "👋 شروع کرنے کے لیے بٹن دبائیں:",
        "enter_track_id": "🔍 درخواست نمبر:",
        "track_not_found": "❌ نہیں ملا۔",
    },
}

def t(ctx, key, **kw):
    lang = ctx.user_data.get("lang", "ar")
    txt = TEXTS.get(lang, TEXTS["ar"]).get(key, key)
    return txt.format(**kw) if kw else txt

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    kb = [
        [InlineKeyboardButton("🇸🇦 عربي", callback_data="lang_ar")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇵🇰 اردو", callback_data="lang_ur")],
    ]
    await update.message.reply_text(TEXTS["ar"]["welcome"], reply_markup=InlineKeyboardMarkup(kb))
    return LANG

async def select_language(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["lang"] = q.data.split("_")[1]
    await q.edit_message_text(t(ctx, "enter_id"))
    return IDENTIFY

async def identify_employee(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    emp = find_employee(update.message.text.strip(), get_employees())
    if not emp:
        await update.message.reply_text(t(ctx, "not_found"))
        return IDENTIFY
    if not is_labor(emp):
        await update.message.reply_text(t(ctx, "not_labor"))
        return IDENTIFY
    ctx.user_data["emp"] = {k: str(v) if v is not None else "" for k, v in emp.items()}
    kb = [
        [InlineKeyboardButton(t(ctx, "menu_leave"), callback_data="menu_leave")],
        [InlineKeyboardButton(t(ctx, "menu_track"), callback_data="menu_track")],
    ]
    await update.message.reply_text(
        t(ctx, "welcome_emp", name=get_display_name(emp)),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )
    return MAIN_MENU

async def main_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "back_to_menu":
        emp = ctx.user_data.get("emp", {})
        lang = ctx.user_data.get("lang", "ar")
        # نحتفظ ببيانات الموظف واللغة فقط
        ctx.user_data.clear()
        ctx.user_data["emp"] = emp
        ctx.user_data["lang"] = lang
        kb = [
            [InlineKeyboardButton(t(ctx, "menu_leave"), callback_data="menu_leave")],
            [InlineKeyboardButton(t(ctx, "menu_track"), callback_data="menu_track")],
        ]
        await q.edit_message_text(t(ctx, "welcome_emp", name=emp.get("Employee Name Eng", "")), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return MAIN_MENU
    if q.data == "menu_leave":
        kb = [
            [InlineKeyboardButton(t(ctx, "leave_annual"), callback_data="leave_annual")],
            [InlineKeyboardButton(t(ctx, "leave_sick"),   callback_data="leave_sick")],
            [InlineKeyboardButton(t(ctx, "leave_unpaid"), callback_data="leave_unpaid")],
            [InlineKeyboardButton(t(ctx, "back"), callback_data="back_to_menu")],
        ]
        await q.edit_message_text(t(ctx, "select_leave_type"), reply_markup=InlineKeyboardMarkup(kb))
        return LEAVE_TYPE
    await q.edit_message_text(t(ctx, "enter_track_id"))
    return TRACK_ID

async def select_leave_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["leave_type"] = q.data.replace("leave_", "")
    await q.edit_message_text(t(ctx, "enter_start"))
    return LEAVE_START

async def _check_two_years(emp: dict, start_date) -> tuple:
    """يتحقق إن الموظف أكمل سنتين — يرجع (True, None, None) لو مؤهل"""
    hiring_date_str = ""
    for key in ["Hiring date", "HiringDate", "Hiring Date", "hiring date"]:
        val = str(emp.get(key, "") or "").strip()
        if val and val not in ("None", ""):
            hiring_date_str = val
            break
    if not hiring_date_str:
        return True, None, None
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]:
        try:
            from dateutil.relativedelta import relativedelta
            hd = datetime.strptime(hiring_date_str, fmt).date()
            two_years = hd + relativedelta(years=2)
            if start_date < two_years:
                return False, hd.strftime("%d/%m/%Y"), two_years.strftime("%d/%m/%Y")
            return True, None, None
        except:
            continue
    return True, None, None

async def leave_start_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        start_date = datetime.strptime(update.message.text.strip(), "%Y-%m-%d").date()
        emp = ctx.user_data.get("emp", {})
        eligible, hired, eligible_date = await _check_two_years(emp, start_date)
        if not eligible:
            lang = ctx.user_data.get("lang", "ar")
            if lang == "en":
                msg = "Sorry, you have not completed 2 years (hired: " + hired + "). Eligible after: " + eligible_date + ". Please contact your regional HR officer."
            elif lang == "ur":
                msg = "معذرت، 2 سال مکمل نہیں (تقرری: " + hired + ")۔ اہلیت: " + eligible_date + "۔ HR افسر سے رابطہ کریں۔"
            else:
                msg = "عذراً، لم تكتمل سنتان من تاريخ التحاقك (" + hired + "). ستكون مؤهلاً بعد: " + eligible_date + ". يرجى التواصل مع موظف HR في منطقتك."
            await update.message.reply_text("⚠️ " + msg)
            return LEAVE_START
        ctx.user_data["start_date"] = update.message.text.strip()
        await update.message.reply_text(t(ctx, "enter_return"))
        return LEAVE_RETURN
    except ValueError:
        await update.message.reply_text(t(ctx, "invalid_date"))
        return LEAVE_START

async def leave_return_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        ret   = datetime.strptime(update.message.text.strip(), "%Y-%m-%d").date()
        start = datetime.strptime(ctx.user_data["start_date"], "%Y-%m-%d").date()
        if ret <= start:
            await update.message.reply_text(t(ctx, "return_before"))
            return LEAVE_RETURN
        ctx.user_data["return_date"] = update.message.text.strip()
        ctx.user_data["duration"]    = (ret - start).days
        kb = [
            [InlineKeyboardButton(t(ctx, "dest_inside"),  callback_data="dest_inside")],
            [InlineKeyboardButton(t(ctx, "dest_outside"), callback_data="dest_outside")],
            [InlineKeyboardButton(t(ctx, "back"), callback_data="back_to_leave_type")],
        ]
        await update.message.reply_text(t(ctx, "select_dest"), reply_markup=InlineKeyboardMarkup(kb))
        return LEAVE_DEST
    except ValueError:
        await update.message.reply_text(t(ctx, "invalid_date"))
        return LEAVE_RETURN

async def back_to_leave_type_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = [
        [InlineKeyboardButton(t(ctx, "leave_annual"), callback_data="leave_annual")],
        [InlineKeyboardButton(t(ctx, "leave_sick"),   callback_data="leave_sick")],
        [InlineKeyboardButton(t(ctx, "leave_unpaid"), callback_data="leave_unpaid")],
        [InlineKeyboardButton(t(ctx, "back"), callback_data="back_to_menu")],
    ]
    await q.edit_message_text(t(ctx, "select_leave_type"), reply_markup=InlineKeyboardMarkup(kb))
    return LEAVE_TYPE

async def select_destination(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["destination"] = "inside" if q.data == "dest_inside" else "outside"
    if ctx.user_data["destination"] == "outside":
        await q.edit_message_text(t(ctx, "enter_city_from"))
        return LEAVE_CITY_FROM
    await q.edit_message_text(t(ctx, "enter_phone"))
    return LEAVE_PHONE

async def leave_city_from(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    if any(char.isdigit() for char in city):
        msgs = {
            "ar": "❌ اسم المدينة يجب أن يحتوي على حروف فقط. أدخله مجدداً:",
            "en": "❌ City name must contain letters only. Please re-enter:",
            "ur": "❌ شہر کا نام صرف حروف پر مشتمل ہونا چاہیے:",
        }
        lang = ctx.user_data.get("lang", "ar")
        await update.message.reply_text(msgs.get(lang, msgs["ar"]))
        return LEAVE_CITY_FROM
    ctx.user_data["city_from"] = city
    await update.message.reply_text(t(ctx, "enter_country"))
    return LEAVE_COUNTRY

async def leave_country(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    country = update.message.text.strip()
    if any(char.isdigit() for char in country):
        msgs = {
            "ar": "❌ اسم البلد يجب أن يحتوي على حروف فقط. أدخله مجدداً:",
            "en": "❌ Country name must contain letters only. Please re-enter:",
            "ur": "❌ ملک کا نام صرف حروف پر مشتمل ہونا چاہیے:",
        }
        lang = ctx.user_data.get("lang", "ar")
        await update.message.reply_text(msgs.get(lang, msgs["ar"]))
        return LEAVE_COUNTRY
    ctx.user_data["country_to"] = country
    return await show_declaration(update, ctx, is_callback=False)

async def leave_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    if not phone.isdigit() or len(phone) < 10:
        msgs = {
            "ar": "❌ رقم الموبايل يجب أن يكون 10 أرقام على الأقل. أدخله مجدداً:",
            "en": "❌ Mobile number must be at least 10 digits. Please re-enter:",
            "ur": "❌ موبائل نمبر کم از کم 10 ہندسے ہونے چاہئیں:",
        }
        lang = ctx.user_data.get("lang", "ar")
        await update.message.reply_text(msgs.get(lang, msgs["ar"]))
        return LEAVE_PHONE
    ctx.user_data["phone"] = phone
    return await show_confirm_msg(update, ctx)

async def show_declaration(update_or_q, ctx, is_callback=False):
    """يعرض نص الإقرار للموظف مع زرار الموافقة"""
    kb = [[InlineKeyboardButton(t(ctx, "decl_confirm"), callback_data="decl_agree")]]
    text = t(ctx, "decl_text")
    if is_callback:
        await update_or_q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update_or_q.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
    return LEAVE_DECLARATION

async def declaration_agreed(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """الموظف وافق على الإقرار"""
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(t(ctx, "enter_phone"))
    return LEAVE_PHONE

def build_summary(ctx):
    ud  = ctx.user_data
    emp = ud.get("emp", {})
    lmap = {"annual": "سنوية/Annual", "sick": "مرضية/Sick", "unpaid": "بدون راتب/Unpaid"}
    dest = "داخل المملكة" if ud.get("destination") == "inside" else f"خارج المملكة - {ud.get('city_from','')} → {ud.get('country_to','')}"
    return (
        f"👤 *{emp.get('Employee Name Eng','')}*\n"
        f"🏖 {lmap.get(ud.get('leave_type',''),'')}\n"
        f"📅 {ud.get('start_date')} → {ud.get('return_date')}\n"
        f"⏱ {ud.get('duration')} يوم\n"
        f"🌍 {dest}"
    )

async def show_confirm_cb(q, ctx):
    kb = [[
        InlineKeyboardButton(t(ctx, "confirm_yes"), callback_data="confirm_yes"),
        InlineKeyboardButton(t(ctx, "confirm_no"),  callback_data="confirm_no"),
    ]]
    await q.edit_message_text(
        t(ctx, "confirm_title") + build_summary(ctx),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )
    return LEAVE_CONFIRM

async def show_confirm_msg(update, ctx):
    kb = [[
        InlineKeyboardButton(t(ctx, "confirm_yes"), callback_data="confirm_yes"),
        InlineKeyboardButton(t(ctx, "confirm_no"),  callback_data="confirm_no"),
    ]]
    await update.message.reply_text(
        t(ctx, "confirm_title") + build_summary(ctx),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )
    return LEAVE_CONFIRM

async def confirm_leave(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "confirm_no":
        await q.edit_message_text(t(ctx, "cancel"))
        return ConversationHandler.END
    ud  = ctx.user_data
    emp = ud.get("emp", {})
    request_id = generate_request_id()
    ctx.user_data["request_id"] = request_id
    leave_data = {
        "leave_type":  ud.get("leave_type", "annual"),
        "start_date":  ud.get("start_date", ""),
        "return_date": ud.get("return_date", ""),
        "destination": ud.get("destination", "inside"),
        "city_from":   ud.get("city_from", ""),
        "country_to":  ud.get("country_to", ""),
        "duration":    ud.get("duration", 0),
        "phone":       ud.get("phone", ""),
    }
    token   = sig_srv.create_signature_token(q.message.chat_id, emp, leave_data, request_id)
    sig_url = sig_srv.get_signature_url(token, emp.get("Employee Name Eng", ""), request_id, ud.get("leave_type", "annual"))
    lang    = ud.get("lang", "ar")
    msgs = {
        "ar": f"✍️ اضغط الرابط لتوقيع طلبك:\n\n{sig_url}\n\nارسم توقيعك بإصبعك ثم اضغط إرسال",
        "en": f"✍️ Tap to sign:\n\n{sig_url}\n\nDraw your signature then tap Submit",
        "ur": f"✍️ لنک دبائیں:\n\n{sig_url}\n\nدستخط کریں پھر بھیجیں",
    }
    await q.edit_message_text(msgs.get(lang, msgs["ar"]))
    return SIGNATURE

async def receive_signature(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ جاري المعالجة...")
    return ConversationHandler.END

async def track_request(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    req = get_request(update.message.text.strip().upper())
    if not req:
        await update.message.reply_text(t(ctx, "track_not_found"))
        return TRACK_ID
    await update.message.reply_text(format_request_status(req), parse_mode="Markdown")
    return ConversationHandler.END

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t(ctx, "cancel"))
    return ConversationHandler.END


async def unknown_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """يرد على أي رسالة خارج الـ conversation"""
    lang = ctx.user_data.get("lang", "ar")
    msgs = {
        "ar": "👋 اضغط الزرار للبدء من جديد:",
        "en": "👋 Press the button to start over:",
        "ur": "👋 دوبارہ شروع کرنے کے لیے بٹن دبائیں:",
    }
    kb = [[InlineKeyboardButton(
        {"ar": "🔄 بدء من جديد", "en": "🔄 Start Over", "ur": "🔄 دوبارہ شروع"}.get(lang, "🔄 بدء من جديد"),
        callback_data="restart_bot"
    )]]
    await update.message.reply_text(msgs.get(lang, msgs["ar"]), reply_markup=InlineKeyboardMarkup(kb))

async def restart_bot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """يبدأ من جديد"""
    q = update.callback_query
    await q.answer()
    ctx.user_data.clear()
    kb = [
        [InlineKeyboardButton("🇸🇦 عربي", callback_data="lang_ar")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇵🇰 اردو", callback_data="lang_ur")],
    ]
    await q.edit_message_text(TEXTS["ar"]["welcome"], reply_markup=InlineKeyboardMarkup(kb))
    return LANG

def main():
    token    = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found!")
    base_url = os.getenv("BASE_URL", "")
    port     = int(os.getenv("PORT", "8080"))

    ptb_app = Application.builder().token(token).build()
    sig_srv.BOT_APP = ptb_app

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG:            [CallbackQueryHandler(select_language,   pattern="^lang_")],
            IDENTIFY:        [MessageHandler(filters.TEXT & ~filters.COMMAND, identify_employee)],
            MAIN_MENU:       [CallbackQueryHandler(main_menu,          pattern="^menu_")],
            LEAVE_TYPE:      [CallbackQueryHandler(select_leave_type, pattern="^leave_"), CallbackQueryHandler(main_menu, pattern="^back_to_menu$")],
            LEAVE_START:     [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_start_date)],
            LEAVE_RETURN:    [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_return_date)],
            LEAVE_DEST:      [CallbackQueryHandler(select_destination, pattern="^dest_"), CallbackQueryHandler(main_menu, pattern="^back_to_menu$")],
            LEAVE_CITY_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_city_from)],
            LEAVE_COUNTRY:   [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_country)],
            LEAVE_PHONE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_phone)],
            LEAVE_DECLARATION: [CallbackQueryHandler(declaration_agreed, pattern="^decl_agree$")],
            LEAVE_CONFIRM:   [CallbackQueryHandler(confirm_leave,      pattern="^confirm_")],
            SIGNATURE:       [MessageHandler(filters.PHOTO,            receive_signature)],
            TRACK_ID:        [MessageHandler(filters.TEXT & ~filters.COMMAND, track_request)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    ptb_app.add_handler(conv)
    # handler للرسائل خارج الـ conversation
    ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))
    ptb_app.add_handler(CallbackQueryHandler(restart_bot, pattern="^restart_bot$"))

    async def run_all():
        # ✅ السيرفر يشتغل أولاً
        web_app = sig_srv.create_app()
        runner  = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"✅ Server running on port {port}")

        # ✅ البوت يشتغل بعد السيرفر
        await ptb_app.initialize()
        await ptb_app.start()
        logger.info("✅ Bot started")

        # ✅ تسجيل الـ webhook
        if base_url:
            webhook_url = f"{base_url}/telegram"
            try:
                await ptb_app.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
                logger.info(f"✅ Webhook set: {webhook_url}")
            except Exception as e:
                logger.error(f"❌ Webhook error: {e}")

        try:
            await asyncio.Event().wait()
        finally:
            await ptb_app.stop()
            await ptb_app.shutdown()
            await runner.cleanup()

    asyncio.run(run_all())


if __name__ == "__main__":
    main()
