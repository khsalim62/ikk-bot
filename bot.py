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

LANG, IDENTIFY, MAIN_MENU, LEAVE_TYPE, LEAVE_START, LEAVE_RETURN, LEAVE_DEST, LEAVE_CITY_FROM, LEAVE_COUNTRY, LEAVE_PHONE, LEAVE_CONFIRM, LEAVE_DECLARATION, SIGNATURE, TRACK_ID, SICK_PHOTO, BTR_MENAME, BTR_MENAME_PHOTO, BTR_SERVICE, BTR_DATE_FROM, BTR_DATE_TO, BTR_CITY_FROM, BTR_CITY_TO, BTR_IQAMA_PHOTO, BTR_PHONE, BTR_EMAIL, SALARY_DOB = range(26)

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
        "not_found": "❌ الرقم غير موجود. تأكد وحاول مجدداً، أو اكتب /start للبدء من جديد.",
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
        "sick_photo": "📸 أرسل صورة واضحة من التقرير الطبي:",
        "sick_done": "✅ تم استلام طلب إجازتك المرضية بنجاح!\n\nرقم الطلب: {req_id}\n{name}\n{start} - {end}\n\nاحتفظ برقم الطلب للمتابعة.",
        "menu_btr": "✈️ حجز رحلة عمل (BTR)",
        "btr_mename_q": "❓ هل تم تقديم طلبك على نظام MENAME؟",
        "btr_mename_yes": "✅ نعم، تم التقديم",
        "btr_mename_no": "❌ لا",
        "btr_mename_required": "⚠️ يجب تقديم طلبك على نظام MENAME أولاً قبل المتابعة هنا.\nبعد التقديم، عد وابدأ الطلب مجدداً.",
        "btr_mename_photo": "📸 أرسل صورة من حالة طلبك على نظام MENAME:",
        "btr_service": "🏨 اختر نوع الحجز المطلوب:",
        "btr_hotel": "🏨 حجز فندق فقط",
        "btr_flight": "✈️ حجز طيران فقط",
        "btr_hotel_flight": "🏨✈️ حجز فندق وطيران",
        "btr_date_from": "📅 تاريخ السفر (مثال: 2026-06-01):",
        "btr_date_to": "📅 تاريخ العودة (مثال: 2026-06-10):",
        "btr_city_from": "🏙 من أي مدينة ستسافر؟",
        "btr_city_to": "🏙 إلى أي مدينة؟",
        "btr_iqama_photo": "📸 أرسل صورة من الإقامة:",
        "btr_phone": "📱 أدخل رقم موبايلك للتواصل:",
        "btr_email": "📧 أدخل بريدك الإلكتروني للتواصل:",
        "btr_done": "✅ تم استلام طلب حجز رحلة العمل بنجاح!\n\nرقم الطلب: {req_id}\nسيتم التواصل معك قريباً لتأكيد الحجز.",
        "back": "🔙 رجوع",
        "restart": "🔄 بدء من جديد",
        "idle_msg": "👋 اضغط الزرار للبدء:",
        "menu_salary": "💰 كشف الراتب",
        "salary_dob": "📅 أدخل تاريخ ميلادك للتحقق (مثال: 1984-10-30):",
        "salary_dob_wrong": "❌ تاريخ الميلاد غير صحيح. حاول مجدداً:",
        "salary_not_found": "❌ لم يتم العثور على كشف راتبك. تواصل مع HR.",
        "salary_found": "✅ تم العثور على كشف راتبك:",
        "enter_track_id": "🔍 أدخل رقم الطلب:",
        "track_not_found": "❌ رقم الطلب غير موجود.",
    },
    "en": {
        "welcome": "👋 Welcome to HR Self-Service Bot\nChoose your language / اختر لغتك / اپنی زبان منتخب کریں",
        "enter_id": "🔢 Enter your Employee ID or Iqama number:",
        "not_found": "❌ ID not found. Please try again, or type /start to restart.",
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
        "sick_photo": "📸 Please send a clear photo of your medical report:",
        "sick_done": "✅ Your sick leave request has been received!\n\nRequest ID: {req_id}\n{name}\n{start} - {end}\n\nKeep your request ID for follow-up.",
        "menu_btr": "✈️ Business Trip Request (BTR)",
        "btr_mename_q": "❓ Have you submitted your request on MENAME System?",
        "btr_mename_yes": "✅ Yes, submitted",
        "btr_mename_no": "❌ No",
        "btr_mename_required": "⚠️ You must submit your request on MENAME System first.\nAfter submitting, come back and start again.",
        "btr_mename_photo": "📸 Send a screenshot of your MENAME request status:",
        "btr_service": "🏨 Select booking type:",
        "btr_hotel": "🏨 Hotel only",
        "btr_flight": "✈️ Flight only",
        "btr_hotel_flight": "🏨✈️ Hotel & Flight",
        "btr_date_from": "📅 Travel date (e.g. 2026-06-01):",
        "btr_date_to": "📅 Return date (e.g. 2026-06-10):",
        "btr_city_from": "🏙 Departing from which city?",
        "btr_city_to": "🏙 Traveling to which city?",
        "btr_iqama_photo": "📸 Send a photo of your Iqama:",
        "btr_phone": "📱 Enter your mobile number:",
        "btr_email": "📧 Enter your email address:",
        "btr_done": "✅ Your BTR has been received!\n\nRequest ID: {req_id}\nWe will contact you soon to confirm the booking.",
        "back": "🔙 Back",
        "restart": "🔄 Start Over",
        "idle_msg": "👋 Press the button to start:",
        "menu_salary": "💰 Salary Slip",
        "salary_dob": "📅 Enter your date of birth to verify (e.g. 1984-10-30):",
        "salary_dob_wrong": "❌ Incorrect date of birth. Please try again:",
        "salary_not_found": "❌ Salary slip not found. Contact HR.",
        "salary_found": "✅ Your salary slip:",
        "enter_track_id": "🔍 Enter request ID:",
        "track_not_found": "❌ Request ID not found.",
    },
    "ur": {
        "welcome": "👋 HR سیلف سروس بوٹ میں خوش آمدید\nاپنی زبان منتخب کریں",
        "enter_id": "🔢 ملازم نمبر یا اقامہ نمبر درج کریں:",
        "not_found": "❌ نمبر نہیں ملا۔ /start لکھیں۔",
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
        "sick_photo": "📸 طبی رپورٹ کی واضح تصویر بھیجیں:",
        "sick_done": "✅ آپ کی بیماری چھٹی کی درخواست موصول ہوئی!\n\nدرخواست نمبر: {req_id}\n{name}\n{start} - {end}\n\nپیروی کے لیے نمبر محفوظ رکھیں۔",
        "menu_btr": "✈️ کاروباری سفر کی درخواست (BTR)",
        "btr_mename_q": "❓ کیا آپ نے MENAME سسٹم پر درخواست دی ہے؟",
        "btr_mename_yes": "✅ ہاں",
        "btr_mename_no": "❌ نہیں",
        "btr_mename_required": "⚠️ پہلے MENAME سسٹم پر درخواست دیں۔",
        "btr_mename_photo": "📸 MENAME درخواست کی تصویر بھیجیں:",
        "btr_service": "🏨 بکنگ کی قسم منتخب کریں:",
        "btr_hotel": "🏨 صرف ہوٹل",
        "btr_flight": "✈️ صرف پرواز",
        "btr_hotel_flight": "🏨✈️ ہوٹل اور پرواز",
        "btr_date_from": "📅 سفر کی تاریخ:",
        "btr_date_to": "📅 واپسی کی تاریخ:",
        "btr_city_from": "🏙 روانگی کا شہر؟",
        "btr_city_to": "🏙 منزل کا شہر؟",
        "btr_iqama_photo": "📸 اقامہ کی تصویر بھیجیں:",
        "btr_phone": "📱 موبائل نمبر:",
        "btr_email": "📧 ای میل:",
        "btr_done": "✅ BTR موصول ہوئی!\n\nدرخواست نمبر: {req_id}\nجلد رابطہ کیا جائے گا۔",
        "back": "🔙 واپس",
        "restart": "🔄 دوبارہ شروع",
        "idle_msg": "👋 شروع کرنے کے لیے بٹن دبائیں:",
        "menu_salary": "💰 تنخواہ سلپ",
        "salary_dob": "📅 تصدیق کے لیے تاریخ پیدائش (مثال: 1984-10-30):",
        "salary_dob_wrong": "❌ غلط تاریخ پیدائش۔ دوبارہ کوشش کریں:",
        "salary_not_found": "❌ تنخواہ سلپ نہیں ملی۔ HR سے رابطہ کریں۔",
        "salary_found": "✅ آپ کی تنخواہ سلپ:",
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
    welcome_msg = (
        "👋 أهلاً بك في الخدمة الذاتية لموظفي CRES\n\n"
        "من خلال هذا البوت يمكنك إنجاز معاملاتك الوظيفية بسهولة وسرعة في أي وقت.\n\n"
        "اختر لغتك / Choose your language / اپنی زبان منتخب کریں"
    )
    kb = [
        [InlineKeyboardButton("🇸🇦 عربي", callback_data="lang_ar")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇵🇰 اردو", callback_data="lang_ur")],
    ]
    await update.message.reply_text(welcome_msg, reply_markup=InlineKeyboardMarkup(kb))
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
    ctx.user_data["emp"] = {k: str(v) if v is not None else "" for k, v in emp.items()}
    if is_labor(emp):
        kb = [
            [InlineKeyboardButton(t(ctx, "menu_leave"),   callback_data="menu_leave")],
            [InlineKeyboardButton(t(ctx, "menu_salary"),  callback_data="menu_salary")],
            [InlineKeyboardButton(t(ctx, "menu_track"),   callback_data="menu_track")],
        ]
    else:
        kb = [
            [InlineKeyboardButton(t(ctx, "menu_btr"), callback_data="menu_btr")],
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
        ctx.user_data.clear()
        ctx.user_data["emp"] = emp
        ctx.user_data["lang"] = lang
        if is_labor(emp):
            kb = [
                [InlineKeyboardButton(t(ctx, "menu_leave"),   callback_data="menu_leave")],
                [InlineKeyboardButton(t(ctx, "menu_salary"),  callback_data="menu_salary")],
                [InlineKeyboardButton(t(ctx, "menu_track"),   callback_data="menu_track")],
            ]
        else:
            kb = [
                [InlineKeyboardButton(t(ctx, "menu_btr"), callback_data="menu_btr")],
                [InlineKeyboardButton(t(ctx, "menu_track"), callback_data="menu_track")],
            ]
        await q.edit_message_text(t(ctx, "welcome_emp", name=emp.get("Employee Name Eng", "")), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return MAIN_MENU
    if q.data == "menu_btr":
        kb = [
            [InlineKeyboardButton(t(ctx, "btr_mename_yes"), callback_data="btr_mename_yes")],
            [InlineKeyboardButton(t(ctx, "btr_mename_no"),  callback_data="btr_mename_no")],
        ]
        await q.edit_message_text(t(ctx, "btr_mename_q"), reply_markup=InlineKeyboardMarkup(kb))
        return BTR_MENAME
    if q.data == "menu_salary":
        await q.edit_message_text(t(ctx, "salary_dob"))
        return SALARY_DOB
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
    leave_type = q.data.replace("leave_", "")
    ctx.user_data["leave_type"] = leave_type
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
        from datetime import date as today_date
        start_date = datetime.strptime(update.message.text.strip(), "%Y-%m-%d").date()

        # تحقق من التاريخ حسب نوع الإجازة
        leave_type = ctx.user_data.get("leave_type", "annual")
        today = today_date.today()

        if leave_type == "sick":
            # الإجازة المرضية: أي تاريخ في نفس السنة الحالية
            if start_date.year != today.year:
                lang = ctx.user_data.get("lang", "ar")
                msgs = {
                    "ar": "❌ يجب أن يكون التاريخ في سنة " + str(today.year) + ". أدخل تاريخاً صحيحاً:",
                    "en": "❌ Date must be in " + str(today.year) + ". Please enter a valid date:",
                    "ur": "❌ تاریخ " + str(today.year) + " میں ہونی چاہیے:",
                }
                await update.message.reply_text(msgs.get(lang, msgs["ar"]))
                return LEAVE_START
        else:
            # باقي الإجازات: لا يمكن تاريخ في الماضي
            if start_date < today:
                lang = ctx.user_data.get("lang", "ar")
                msgs = {
                    "ar": "❌ لا يمكن اختيار تاريخ في الماضي. أدخل تاريخاً من اليوم أو بعده:",
                    "en": "❌ Date cannot be in the past. Please enter today or a future date:",
                    "ur": "❌ ماضی کی تاریخ نہیں ہو سکتی۔ آج یا آنے والی تاریخ درج کریں:",
                }
                await update.message.reply_text(msgs.get(lang, msgs["ar"]))
                return LEAVE_START
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

        # لو إجازة مرضية — نطلب الصورة مباشرة
        if ctx.user_data.get("leave_type") == "sick":
            await update.message.reply_text(t(ctx, "sick_photo"))
            return SICK_PHOTO

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

async def sick_leave_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """يستقبل صورة التقرير الطبي ويبعت الإيميل"""
    if not update.message.photo:
        await update.message.reply_text(t(ctx, "sick_photo"))
        return SICK_PHOTO

    ud = ctx.user_data
    emp = ud.get("emp", {})
    request_id = generate_request_id()

    # حفظ الطلب
    leave_data = {
        "leave_type":  "sick",
        "start_date":  ud.get("start_date", ""),
        "return_date": ud.get("return_date", ""),
        "destination": "inside",
        "duration":    ud.get("duration", 0),
    }
    save_request(request_id, emp, leave_data)

    # إرسال الإيميل مع الصورة
    try:
        from email_sender import send_sick_leave
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        import tempfile, os
        tmp = tempfile.mktemp(suffix=".jpg")
        await photo_file.download_to_drive(tmp)
        send_sick_leave(emp, leave_data, tmp, request_id)
        os.unlink(tmp)
        email_status = "✅ تم إرسال طلبك لقسم الموارد البشرية"
    except Exception as e:
        print(f"Sick leave email error: {e}")
        email_status = "⚠️ تم حفظ طلبك — سيتم إرساله قريباً"

    lang = ud.get("lang", "ar")
    msg = t(ctx, "sick_done",
        req_id=request_id,
        name=emp.get("Employee Name Eng", ""),
        start=ud.get("start_date", ""),
        end=ud.get("return_date", "")
    ) + "\n\n" + email_status

    await update.message.reply_text(msg)
    return ConversationHandler.END

async def btr_mename(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "btr_mename_no":
        await q.edit_message_text(t(ctx, "btr_mename_required"))
        return ConversationHandler.END
    await q.edit_message_text(t(ctx, "btr_mename_photo"))
    return BTR_MENAME_PHOTO

async def btr_mename_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(t(ctx, "btr_mename_photo"))
        return BTR_MENAME_PHOTO
    ctx.user_data["btr_mename_photo"] = update.message.photo[-1].file_id
    kb = [
        [InlineKeyboardButton(t(ctx, "btr_hotel"),        callback_data="btr_hotel")],
        [InlineKeyboardButton(t(ctx, "btr_flight"),       callback_data="btr_flight")],
        [InlineKeyboardButton(t(ctx, "btr_hotel_flight"), callback_data="btr_hotel_flight")],
    ]
    await update.message.reply_text(t(ctx, "btr_service"), reply_markup=InlineKeyboardMarkup(kb))
    return BTR_SERVICE

async def btr_service(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["btr_service"] = q.data.replace("btr_", "")
    await q.edit_message_text(t(ctx, "btr_date_from"))
    return BTR_DATE_FROM

async def btr_date_from(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        from datetime import date as d
        date_from = datetime.strptime(update.message.text.strip(), "%Y-%m-%d").date()
        if date_from < d.today():
            lang = ctx.user_data.get("lang", "ar")
            msgs = {"ar": "❌ لا يمكن اختيار تاريخ في الماضي:", "en": "❌ Date cannot be in the past:", "ur": "❌ ماضی کی تاریخ نہیں:"}
            await update.message.reply_text(msgs.get(lang, msgs["ar"]))
            return BTR_DATE_FROM
        ctx.user_data["btr_date_from"] = update.message.text.strip()
        await update.message.reply_text(t(ctx, "btr_date_to"))
        return BTR_DATE_TO
    except ValueError:
        await update.message.reply_text(t(ctx, "invalid_date"))
        return BTR_DATE_FROM

async def btr_date_to(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        date_to = datetime.strptime(update.message.text.strip(), "%Y-%m-%d").date()
        date_from = datetime.strptime(ctx.user_data["btr_date_from"], "%Y-%m-%d").date()
        if date_to <= date_from:
            await update.message.reply_text(t(ctx, "return_before"))
            return BTR_DATE_TO
        ctx.user_data["btr_date_to"] = update.message.text.strip()
        await update.message.reply_text(t(ctx, "btr_city_from"))
        return BTR_CITY_FROM
    except ValueError:
        await update.message.reply_text(t(ctx, "invalid_date"))
        return BTR_DATE_TO

async def btr_city_from(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    if any(char.isdigit() for char in city):
        lang = ctx.user_data.get("lang", "ar")
        msgs = {"ar": "❌ أدخل اسم المدينة بالحروف فقط:", "en": "❌ Letters only:", "ur": "❌ صرف حروف:"}
        await update.message.reply_text(msgs.get(lang, msgs["ar"]))
        return BTR_CITY_FROM
    ctx.user_data["btr_city_from"] = city
    await update.message.reply_text(t(ctx, "btr_city_to"))
    return BTR_CITY_TO

async def btr_city_to(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    if any(char.isdigit() for char in city):
        lang = ctx.user_data.get("lang", "ar")
        msgs = {"ar": "❌ أدخل اسم المدينة بالحروف فقط:", "en": "❌ Letters only:", "ur": "❌ صرف حروف:"}
        await update.message.reply_text(msgs.get(lang, msgs["ar"]))
        return BTR_CITY_TO
    ctx.user_data["btr_city_to"] = city
    await update.message.reply_text(t(ctx, "btr_iqama_photo"))
    return BTR_IQAMA_PHOTO

async def btr_iqama_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(t(ctx, "btr_iqama_photo"))
        return BTR_IQAMA_PHOTO
    ctx.user_data["btr_iqama_photo"] = update.message.photo[-1].file_id
    await update.message.reply_text(t(ctx, "btr_phone"))
    return BTR_PHONE

async def btr_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    if not phone.isdigit() or len(phone) < 10:
        lang = ctx.user_data.get("lang", "ar")
        msgs = {"ar": "❌ أدخل رقم موبايل صحيح (10 أرقام على الأقل):", "en": "❌ Enter valid mobile (min 10 digits):", "ur": "❌ درست نمبر درج کریں:"}
        await update.message.reply_text(msgs.get(lang, msgs["ar"]))
        return BTR_PHONE
    ctx.user_data["btr_phone"] = phone
    await update.message.reply_text(t(ctx, "btr_email"))
    return BTR_EMAIL

async def btr_email(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    if "@" not in email or "." not in email:
        lang = ctx.user_data.get("lang", "ar")
        msgs = {"ar": "❌ أدخل بريد إلكتروني صحيح:", "en": "❌ Enter valid email:", "ur": "❌ درست ای میل:"}
        await update.message.reply_text(msgs.get(lang, msgs["ar"]))
        return BTR_EMAIL
    ctx.user_data["btr_email"] = email

    ud = ctx.user_data
    emp = ud.get("emp", {})
    request_id = generate_request_id().replace("LV-", "BTR-")

    # إرسال الإيميل
    try:
        from email_sender import send_btr_request
        import tempfile, os
        from telegram import Bot

        # تحميل الصور
        bot = ctx.bot
        tmp_mename = tempfile.mktemp(suffix=".jpg")
        tmp_iqama  = tempfile.mktemp(suffix=".jpg")

        mename_file = await bot.get_file(ud["btr_mename_photo"])
        await mename_file.download_to_drive(tmp_mename)

        iqama_file = await bot.get_file(ud["btr_iqama_photo"])
        await iqama_file.download_to_drive(tmp_iqama)

        btr_data = {
            "service":   ud.get("btr_service", ""),
            "date_from": ud.get("btr_date_from", ""),
            "date_to":   ud.get("btr_date_to", ""),
            "city_from": ud.get("btr_city_from", ""),
            "city_to":   ud.get("btr_city_to", ""),
            "phone":     ud.get("btr_phone", ""),
            "email":     ud.get("btr_email", ""),
        }

        send_btr_request(emp, btr_data, tmp_mename, tmp_iqama, request_id)
        os.unlink(tmp_mename)
        os.unlink(tmp_iqama)
        status = "✅ تم إرسال طلبك لفريق السفر"
    except Exception as e:
        print(f"BTR email error: {e}")
        status = "⚠️ تم حفظ طلبك — سيتم إرساله قريباً"

    msg = t(ctx, "btr_done", req_id=request_id) + "\n\n" + status
    await update.message.reply_text(msg)
    return ConversationHandler.END

async def salary_dob(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """يتحقق من تاريخ الميلاد ويبعت كشف الراتب"""
    dob_input = update.message.text.strip()
    emp = ctx.user_data.get("emp", {})
    
    # نجيب تاريخ الميلاد من الشيت
    emp_dob = str(emp.get("Date of Birth", "") or emp.get("DOB", "") or emp.get("Birth Date", "") or "").strip()
    
    # نحول input من YYYY-MM-DD لـ DD/MM/YYYY للمقارنة
    try:
        from datetime import datetime
        dob_converted = datetime.strptime(dob_input, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        await update.message.reply_text(t(ctx, "salary_dob_wrong"))
        return SALARY_DOB

    if not emp_dob or dob_converted != emp_dob:
        await update.message.reply_text(t(ctx, "salary_dob_wrong"))
        return SALARY_DOB
    
    # نبحث عن صفحة الموظف في الـ PDF
    emp_code = emp.get("Employee Code", "").strip()
    SALARY_PDF_URL = "https://drive.google.com/uc?export=download&id=1ysRx0f71AXtX2zr--IuH7eRSN4oRZ1zT"
    
    try:
        from pypdf import PdfReader, PdfWriter
        import tempfile
        import httpx
        import io

        # تحميل الـ PDF من Google Drive
        await update.message.reply_text("⏳ جاري التحقق...")
        response = httpx.get(SALARY_PDF_URL, follow_redirects=True, timeout=30)
        pdf_bytes = io.BytesIO(response.content)
        reader = PdfReader(pdf_bytes)
        page_num = -1
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if emp_code.lower() in text.lower():
                page_num = i
                break
        
        if page_num == -1:
            await update.message.reply_text(t(ctx, "salary_not_found"))
            return ConversationHandler.END
        
        # نعمل PDF بصفحة واحدة
        writer = PdfWriter()
        writer.add_page(reader.pages[page_num])
        
        tmp = tempfile.mktemp(suffix=".pdf")
        with open(tmp, "wb") as f:
            writer.write(f)
        
        await update.message.reply_text(t(ctx, "salary_found"))
        with open(tmp, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"salary_{emp_code}.pdf"
            )
        import os
        os.unlink(tmp)
        
    except Exception as e:
        print(f"Salary error: {e}")
        await update.message.reply_text(t(ctx, "salary_not_found"))
    
    return ConversationHandler.END

def build_summary(ctx):
    ud   = ctx.user_data
    emp  = ud.get("emp", {})
    lang = ud.get("lang", "ar")

    lmap = {
        "ar": {"annual": "إجازة سنوية", "sick": "إجازة مرضية",  "unpaid": "إجازة بدون راتب"},
        "en": {"annual": "Annual Leave", "sick": "Sick Leave",    "unpaid": "Unpaid Leave"},
        "ur": {"annual": "سالانہ چھٹی",  "sick": "بیمار چھٹی",   "unpaid": "بغیر تنخواہ"},
    }
    dest_inside  = {"ar": "داخل المملكة", "en": "Inside KSA",    "ur": "سعودی عرب میں"}
    dest_outside = {"ar": "خارج المملكة", "en": "Outside KSA",   "ur": "باہر"}
    dur_label    = {"ar": "يوم",           "en": "days",          "ur": "دن"}
    title        = {"ar": "ملخص الطلب",   "en": "Request Summary", "ur": "خلاصہ"}

    leave_str = lmap.get(lang, lmap["ar"]).get(ud.get("leave_type", ""), "")
    if ud.get("destination") == "outside":
        dest_str = dest_outside.get(lang, dest_outside["ar"])
        dest_str += " - " + ud.get("city_from", "") + " → " + ud.get("country_to", "")
    else:
        dest_str = dest_inside.get(lang, dest_inside["ar"])

    return (
        "📋 *" + title.get(lang, title["ar"]) + "*\n\n"
        "👤 *" + emp.get("Employee Name Eng", "") + "*\n"
        "🏖 " + leave_str + "\n"
        "📅 " + str(ud.get("start_date", "")) + " → " + str(ud.get("return_date", "")) + "\n"
        "⏱ " + str(ud.get("duration", "")) + " " + dur_label.get(lang, "يوم") + "\n"
        "🌍 " + dest_str
    )


async def show_confirm_cb(q, ctx):
    kb = [[
        InlineKeyboardButton(t(ctx, "confirm_yes"), callback_data="confirm_yes"),
        InlineKeyboardButton(t(ctx, "confirm_no"),  callback_data="confirm_no"),
    ]]
    await q.edit_message_text(
        build_summary(ctx),
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
        build_summary(ctx),
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
        "lang":        ud.get("lang", "ar"),
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

async def invalid_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """يرد على أي إدخال غير صحيح"""
    lang = ctx.user_data.get("lang", "ar")
    msgs = {
        "ar": "لم يتم إدخال قيمة صحيحة للبدء — اكتب /start",
        "en": "Invalid input — type /start to begin",
        "ur": "غلط قدر — /start لکھیں",
    }
    await update.message.reply_text(msgs.get(lang, msgs["ar"]))


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
            MAIN_MENU:       [CallbackQueryHandler(main_menu, pattern="^(menu_|back_to_menu)")],
            LEAVE_TYPE:      [CallbackQueryHandler(select_leave_type, pattern="^leave_"), CallbackQueryHandler(main_menu, pattern="^(back_to_menu|menu_)")],
            LEAVE_START:     [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_start_date)],
            LEAVE_RETURN:    [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_return_date)],
            LEAVE_DEST:      [CallbackQueryHandler(select_destination, pattern="^dest_"), CallbackQueryHandler(main_menu, pattern="^back_to_menu$")],
            LEAVE_CITY_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_city_from)],
            LEAVE_COUNTRY:   [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_country)],
            LEAVE_PHONE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_phone)],
            LEAVE_DECLARATION: [CallbackQueryHandler(declaration_agreed, pattern="^decl_agree$")],
            LEAVE_CONFIRM:   [CallbackQueryHandler(confirm_leave,      pattern="^confirm_")],
            SIGNATURE:       [MessageHandler(filters.PHOTO,            receive_signature)],
            SICK_PHOTO:      [MessageHandler(filters.PHOTO, sick_leave_photo), MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: u.message.reply_text(t(c, "sick_photo")))],
            SALARY_DOB:      [MessageHandler(filters.TEXT & ~filters.COMMAND, salary_dob)],
            BTR_MENAME:      [CallbackQueryHandler(btr_mename, pattern="^btr_mename_")],
            BTR_MENAME_PHOTO:[MessageHandler(filters.PHOTO, btr_mename_photo)],
            BTR_SERVICE:     [CallbackQueryHandler(btr_service, pattern="^btr_(hotel|flight|hotel_flight)$")],
            BTR_DATE_FROM:   [MessageHandler(filters.TEXT & ~filters.COMMAND, btr_date_from)],
            BTR_DATE_TO:     [MessageHandler(filters.TEXT & ~filters.COMMAND, btr_date_to)],
            BTR_CITY_FROM:   [MessageHandler(filters.TEXT & ~filters.COMMAND, btr_city_from)],
            BTR_CITY_TO:     [MessageHandler(filters.TEXT & ~filters.COMMAND, btr_city_to)],
            BTR_IQAMA_PHOTO: [MessageHandler(filters.PHOTO, btr_iqama_photo)],
            BTR_PHONE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, btr_phone)],
            BTR_EMAIL:       [MessageHandler(filters.TEXT & ~filters.COMMAND, btr_email)],
            TRACK_ID:        [MessageHandler(filters.TEXT & ~filters.COMMAND, track_request)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start), CallbackQueryHandler(restart_bot, pattern="^restart_bot$"), MessageHandler(filters.TEXT & ~filters.COMMAND, invalid_input)],
        allow_reentry=True,
    )
    ptb_app.add_handler(conv, group=0)
    ptb_app.add_handler(CommandHandler("restart", start), group=1)

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
