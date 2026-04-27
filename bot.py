"""
bot.py — البوت الرئيسي على تيليجرام
IKK Group — HR Self-Service Bot

تشغيل:
    python bot.py

متطلبات:
    pip install python-telegram-bot openpyxl pypdf pillow
"""
import os
import io
import logging
import tempfile
from datetime import datetime, date
from pathlib import Path

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters,
    ContextTypes
)

from employees import load_employees, find_employee, is_labor, get_display_name
from pdf_filler import fill_leave_form, fill_declaration_form, merge_pdfs
from email_sender import send_leave_request
from tracker import generate_request_id, save_request, get_request, get_requests_by_emp, format_request_status

# ===== إعداد اللوج =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== حالات المحادثة =====
(
    LANG, IDENTIFY, MAIN_MENU,
    LEAVE_TYPE, LEAVE_START, LEAVE_RETURN,
    LEAVE_DEST, LEAVE_CITY_FROM, LEAVE_COUNTRY,
    LEAVE_CONFIRM, SIGNATURE,
    TRACK_ID
) = range(12)

# ===== الترجمات =====
TEXTS = {
    "ar": {
        "welcome":          "👋 أهلاً بك في بوت خدمات الموارد البشرية\nاختر لغتك / Choose your language / اپنی زبان منتخب کریں",
        "enter_id":         "🔢 من فضلك أدخل رقمك الوظيفي أو رقم إقامتك:",
        "not_found":        "❌ الرقم غير موجود في النظام. تأكد من الرقم وحاول مجدداً.",
        "not_labor":        "⚠️ هذه الخدمة متاحة للعمال فقط (Labor). للمزيد تواصل مع HR.",
        "welcome_emp":      "✅ مرحباً {name}!\nاختر الخدمة المطلوبة:",
        "menu_leave":       "🏖 طلب إجازة",
        "menu_track":       "🔍 تتبع طلب",
        "select_leave_type":"اختر نوع الإجازة:",
        "leave_annual":     "📅 إجازة سنوية",
        "leave_sick":       "🤒 إجازة مرضية",
        "leave_unpaid":     "💼 إجازة بدون راتب",
        "enter_start":      "📅 أدخل تاريخ بداية الإجازة (مثال: 2025-06-01):",
        "enter_return":     "📅 أدخل تاريخ العودة (مثال: 2025-06-21):",
        "invalid_date":     "❌ تاريخ غير صحيح. استخدم الصيغة: YYYY-MM-DD",
        "return_before":    "❌ تاريخ العودة يجب أن يكون بعد تاريخ البداية.",
        "select_dest":      "🌍 وجهة الإجازة:",
        "dest_inside":      "🇸🇦 داخل المملكة",
        "dest_outside":     "✈️ خارج المملكة",
        "enter_city_from":  "🏙 من أي مدينة ستغادر؟ (مثال: Riyadh / Jeddah / Dammam)",
        "enter_country":    "🌍 ما البلد الذي ستسافر إليه؟",
        "confirm_title":    "📋 *ملخص طلب الإجازة*\n\n",
        "confirm_yes":      "✅ تأكيد وإرسال",
        "confirm_no":       "❌ إلغاء",
        "sign_request":     "✍️ الآن ارسم توقيعك بإصبعك وأرسله كصورة:",
        "processing":       "⏳ جاري معالجة طلبك...",
        "success":          "✅ *تم تقديم طلبك بنجاح!*\n\nرقم طلبك: `{req_id}`\nاحتفظ بهذا الرقم لمتابعة الطلب.",
        "enter_track_id":   "🔍 أدخل رقم الطلب للمتابعة:",
        "track_not_found":  "❌ رقم الطلب غير موجود.",
        "cancel":           "تم الإلغاء. اكتب /start للبدء من جديد.",
    },
    "en": {
        "welcome":          "👋 Welcome to HR Self-Service Bot\nChoose your language / اختر لغتك / اپنی زبان منتخب کریں",
        "enter_id":         "🔢 Please enter your Employee ID or Iqama number:",
        "not_found":        "❌ ID not found. Please check and try again.",
        "not_labor":        "⚠️ This service is for Labor employees only. Contact HR for assistance.",
        "welcome_emp":      "✅ Welcome {name}!\nPlease select a service:",
        "menu_leave":       "🏖 Leave Request",
        "menu_track":       "🔍 Track Request",
        "select_leave_type":"Select leave type:",
        "leave_annual":     "📅 Annual Leave",
        "leave_sick":       "🤒 Sick Leave",
        "leave_unpaid":     "💼 Unpaid Leave",
        "enter_start":      "📅 Enter leave start date (e.g. 2025-06-01):",
        "enter_return":     "📅 Enter return date (e.g. 2025-06-21):",
        "invalid_date":     "❌ Invalid date. Use format: YYYY-MM-DD",
        "return_before":    "❌ Return date must be after start date.",
        "select_dest":      "🌍 Leave destination:",
        "dest_inside":      "🇸🇦 Inside KSA",
        "dest_outside":     "✈️ Outside KSA",
        "enter_city_from":  "🏙 Which city are you departing from? (e.g. Riyadh / Jeddah / Dammam)",
        "enter_country":    "🌍 Which country are you travelling to?",
        "confirm_title":    "📋 *Leave Request Summary*\n\n",
        "confirm_yes":      "✅ Confirm & Submit",
        "confirm_no":       "❌ Cancel",
        "sign_request":     "✍️ Please draw your signature with your finger and send it as an image:",
        "processing":       "⏳ Processing your request...",
        "success":          "✅ *Request submitted successfully!*\n\nYour request ID: `{req_id}`\nSave this ID to track your request.",
        "enter_track_id":   "🔍 Enter your request ID to track it:",
        "track_not_found":  "❌ Request ID not found.",
        "cancel":           "Cancelled. Type /start to begin again.",
    },
    "ur": {
        "welcome":          "👋 HR سیلف سروس بوٹ میں خوش آمدید\nاپنی زبان منتخب کریں / Choose your language / اختر لغتك",
        "enter_id":         "🔢 براہ کرم اپنا ملازم نمبر یا اقامہ نمبر درج کریں:",
        "not_found":        "❌ نمبر نہیں ملا۔ دوبارہ کوشش کریں۔",
        "not_labor":        "⚠️ یہ سروس صرف مزدور ملازمین کے لیے ہے۔",
        "welcome_emp":      "✅ خوش آمدید {name}!\nخدمت منتخب کریں:",
        "menu_leave":       "🏖 چھٹی کی درخواست",
        "menu_track":       "🔍 درخواست ٹریک کریں",
        "select_leave_type":"چھٹی کی قسم منتخب کریں:",
        "leave_annual":     "📅 سالانہ چھٹی",
        "leave_sick":       "🤒 بیمار چھٹی",
        "leave_unpaid":     "💼 بغیر تنخواہ چھٹی",
        "enter_start":      "📅 چھٹی شروع ہونے کی تاریخ درج کریں (مثال: 2025-06-01):",
        "enter_return":     "📅 واپسی کی تاریخ درج کریں (مثال: 2025-06-21):",
        "invalid_date":     "❌ غلط تاریخ۔ YYYY-MM-DD فارمیٹ استعمال کریں",
        "return_before":    "❌ واپسی کی تاریخ شروع کی تاریخ کے بعد ہونی چاہیے۔",
        "select_dest":      "🌍 منزل:",
        "dest_inside":      "🇸🇦 سعودی عرب میں",
        "dest_outside":     "✈️ سعودی عرب سے باہر",
        "enter_city_from":  "🏙 روانگی کا شہر؟ (مثال: Riyadh / Jeddah)",
        "enter_country":    "🌍 کس ملک جا رہے ہیں؟",
        "confirm_title":    "📋 *چھٹی درخواست خلاصہ*\n\n",
        "confirm_yes":      "✅ تصدیق کریں",
        "confirm_no":       "❌ منسوخ کریں",
        "sign_request":     "✍️ اپنی انگلی سے دستخط کریں اور تصویر بھیجیں:",
        "processing":       "⏳ درخواست پر کارروائی ہو رہی ہے...",
        "success":          "✅ *درخواست کامیابی سے جمع ہو گئی!*\n\nآپ کا نمبر: `{req_id}`",
        "enter_track_id":   "🔍 ٹریکنگ نمبر درج کریں:",
        "track_not_found":  "❌ درخواست نمبر نہیں ملا۔",
        "cancel":           "منسوخ۔ /start لکھیں۔",
    },
}

def t(context: ContextTypes.DEFAULT_TYPE, key: str, **kwargs) -> str:
    lang = context.user_data.get("lang", "ar")
    text = TEXTS.get(lang, TEXTS["ar"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


# ===== بيانات الموظفين (تتحمل مرة واحدة) =====
EMPLOYEES: dict = {}

def get_employees() -> dict:
    global EMPLOYEES
    if not EMPLOYEES:
        EMPLOYEES = load_employees()
    return EMPLOYEES


# ===== handlers =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("🇸🇦 عربي",   callback_data="lang_ar")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇵🇰 اردو",    callback_data="lang_ur")],
    ]
    await update.message.reply_text(
        TEXTS["ar"]["welcome"],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return LANG


async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1]
    context.user_data["lang"] = lang
    await query.edit_message_text(t(context, "enter_id"))
    return IDENTIFY


async def identify_employee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    identifier = update.message.text.strip()
    employees = get_employees()
    emp = find_employee(identifier, employees)

    if not emp:
        await update.message.reply_text(t(context, "not_found"))
        return IDENTIFY

    if not is_labor(emp):
        await update.message.reply_text(t(context, "not_labor"))
        return IDENTIFY

    # حفظ بيانات الموظف بشكل آمن (strings فقط)
    context.user_data["emp"] = {k: str(v) if v is not None else "" for k, v in emp.items()}
    name = get_display_name(emp)

    keyboard = [
        [InlineKeyboardButton(t(context, "menu_leave"), callback_data="menu_leave")],
        [InlineKeyboardButton(t(context, "menu_track"), callback_data="menu_track")],
    ]
    await update.message.reply_text(
        t(context, "welcome_emp", name=name),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return MAIN_MENU


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "menu_leave":
        keyboard = [
            [InlineKeyboardButton(t(context, "leave_annual"), callback_data="leave_annual")],
            [InlineKeyboardButton(t(context, "leave_sick"),   callback_data="leave_sick")],
            [InlineKeyboardButton(t(context, "leave_unpaid"), callback_data="leave_unpaid")],
        ]
        await query.edit_message_text(
            t(context, "select_leave_type"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return LEAVE_TYPE

    if action == "menu_track":
        await query.edit_message_text(t(context, "enter_track_id"))
        return TRACK_ID


async def select_leave_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    leave_type = query.data.replace("leave_", "")  # annual / sick / unpaid
    context.user_data["leave_type"] = leave_type
    await query.edit_message_text(t(context, "enter_start"))
    return LEAVE_START


async def leave_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        d = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        await update.message.reply_text(t(context, "invalid_date"))
        return LEAVE_START
    context.user_data["start_date"] = text
    await update.message.reply_text(t(context, "enter_return"))
    return LEAVE_RETURN


async def leave_return_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        ret = datetime.strptime(text, "%Y-%m-%d").date()
        start = datetime.strptime(context.user_data["start_date"], "%Y-%m-%d").date()
    except ValueError:
        await update.message.reply_text(t(context, "invalid_date"))
        return LEAVE_RETURN

    if ret <= start:
        await update.message.reply_text(t(context, "return_before"))
        return LEAVE_RETURN

    context.user_data["return_date"] = text
    context.user_data["duration"] = (ret - start).days

    keyboard = [
        [InlineKeyboardButton(t(context, "dest_inside"),  callback_data="dest_inside")],
        [InlineKeyboardButton(t(context, "dest_outside"), callback_data="dest_outside")],
    ]
    await update.message.reply_text(
        t(context, "select_dest"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return LEAVE_DEST


async def select_destination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    dest = "inside" if query.data == "dest_inside" else "outside"
    context.user_data["destination"] = dest

    if dest == "outside":
        await query.edit_message_text(t(context, "enter_city_from"))
        return LEAVE_CITY_FROM
    else:
        return await _show_confirmation(query, context)


async def leave_city_from(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["city_from"] = update.message.text.strip()
    await update.message.reply_text(t(context, "enter_country"))
    return LEAVE_COUNTRY


async def leave_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["country_to"] = update.message.text.strip()
    return await _show_confirmation_msg(update, context)


async def _show_confirmation(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """عرض ملخص الطلب للتأكيد (من callback)"""
    summary = _build_summary(context)
    keyboard = [
        [InlineKeyboardButton(t(context, "confirm_yes"), callback_data="confirm_yes")],
        [InlineKeyboardButton(t(context, "confirm_no"),  callback_data="confirm_no")],
    ]
    await query.edit_message_text(
        t(context, "confirm_title") + summary,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return LEAVE_CONFIRM


async def _show_confirmation_msg(update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """عرض ملخص الطلب للتأكيد (من message)"""
    summary = _build_summary(context)
    keyboard = [
        [InlineKeyboardButton(t(context, "confirm_yes"), callback_data="confirm_yes")],
        [InlineKeyboardButton(t(context, "confirm_no"),  callback_data="confirm_no")],
    ]
    await update.message.reply_text(
        t(context, "confirm_title") + summary,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return LEAVE_CONFIRM


def _build_summary(context: ContextTypes.DEFAULT_TYPE) -> str:
    ud = context.user_data
    lang = ud.get("lang", "ar")
    leave_map = {"annual": "سنوية / Annual", "sick": "مرضية / Sick", "unpaid": "بدون راتب / Unpaid"}
    dest = "داخل المملكة / Inside KSA" if ud.get("destination") == "inside" else "خارج المملكة / Outside KSA"
    if ud.get("destination") == "outside":
        dest += f"\n   {ud.get('city_from', '')} → {ud.get('country_to', '')}"

    emp = ud.get("emp", {})
    return (
        f"👤 *{emp.get('Employee Name Eng', '')}*\n"
        f"🏖 {leave_map.get(ud.get('leave_type', ''), '')}\n"
        f"📅 {ud.get('start_date')} → {ud.get('return_date')}\n"
        f"⏱ {ud.get('duration')} يوم / days\n"
        f"🌍 {dest}"
    )


async def confirm_leave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        await query.edit_message_text(t(context, "cancel"))
        return ConversationHandler.END

    # توليد رابط التوقيع
    ud = context.user_data
    emp = ud.get("emp", {})
    request_id = generate_request_id()
    context.user_data["request_id"] = request_id

    from signature_server import create_signature_token, get_signature_url
    leave_data_tmp = {
        "leave_type":  ud.get("leave_type", "annual"),
        "start_date":  ud.get("start_date", ""),
        "return_date": ud.get("return_date", ""),
        "destination": ud.get("destination", "inside"),
        "city_from":   ud.get("city_from", ""),
        "country_to":  ud.get("country_to", ""),
        "duration":    ud.get("duration", 0),
    }
    token = create_signature_token(
        chat_id    = query.message.chat_id,
        emp        = emp,
        leave_data = leave_data_tmp,
        request_id = request_id,
    )
    sig_url = get_signature_url(
        token      = token,
        emp_name   = emp.get("Employee Name Eng", ""),
        req_id     = request_id,
        leave_type = ud.get("leave_type", "annual"),
    )
    lang = ud.get("lang", "ar")
    sign_msgs = {
        "ar": f"✍️ *اضغط الرابط أدناه لتوقيع طلبك:*\n\n[📝 افتح صفحة التوقيع]({sig_url})\n\n_افتح الرابط، ارسم توقيعك بإصبعك، ثم اضغط إرسال_",
        "en": f"✍️ *Tap the link below to sign:*\n\n[📝 Open Signature Page]({sig_url})\n\n_Draw your signature then tap Submit_",
        "ur": f"✍️ *لنک دبائیں اور دستخط کریں:*\n\n[📝 صفحہ کھولیں]({sig_url})\n\n_دستخط کریں پھر بھیجیں_",
    }
    await query.edit_message_text(
        sign_msgs.get(lang, sign_msgs["ar"]),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    return SIGNATURE


async def receive_signature(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال صورة التوقيع ومعالجة الطلب"""
    await update.message.reply_text(t(context, "processing"))

    ud = context.user_data
    emp = ud["emp"]

    leave_data = {
        "leave_type":  ud.get("leave_type", "annual"),
        "start_date":  ud.get("start_date", ""),
        "return_date": ud.get("return_date", ""),
        "destination": ud.get("destination", "inside"),
        "city_from":   ud.get("city_from", ""),
        "country_to":  ud.get("country_to", ""),
        "duration":    ud.get("duration", 0),
    }

    request_id = generate_request_id()
    tmp_dir = Path(tempfile.mkdtemp())

    # تحميل التوقيع
    sig_path = None
    if update.message.photo:
        photo = update.message.photo[-1]
        sig_file = await photo.get_file()
        sig_path = tmp_dir / "signature.jpg"
        await sig_file.download_to_drive(str(sig_path))

    # ملء فورم الإجازة
    leave_pdf_path = tmp_dir / f"leave_{request_id}.pdf"
    fill_leave_form(emp, leave_data, leave_pdf_path)

    pdf_paths = [leave_pdf_path]

    # فورم الإقرار لو السفر برة المملكة
    if leave_data["destination"] == "outside":
        decl_pdf_path = tmp_dir / f"declaration_{request_id}.pdf"
        fill_declaration_form(emp, leave_data, decl_pdf_path)
        pdf_paths.append(decl_pdf_path)

    # حفظ الطلب في الـ tracker
    save_request(request_id, emp, leave_data)

    # إرسال الإيميل لـ HR
    try:
        send_leave_request(emp, leave_data, pdf_paths, request_id)
    except Exception as e:
        logger.error(f"Email error: {e}")

    # رسالة نجاح للموظف
    await update.message.reply_text(
        t(context, "success", req_id=request_id),
        parse_mode="Markdown"
    )

    return ConversationHandler.END


async def track_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    req_id = update.message.text.strip().upper()
    req = get_request(req_id)
    if not req:
        await update.message.reply_text(t(context, "track_not_found"))
        return TRACK_ID

    await update.message.reply_text(
        format_request_status(req),
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(t(context, "cancel"))
    return ConversationHandler.END


# ===== تشغيل البوت =====
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN غير موجود في البيئة!")

    app = Application.builder().token(token).build()

    # ربط الـ bot app بالـ signature server
    import signature_server
    signature_server.BOT_APP = app

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG:         [CallbackQueryHandler(select_language, pattern="^lang_")],
            IDENTIFY:     [MessageHandler(filters.TEXT & ~filters.COMMAND, identify_employee)],
            MAIN_MENU:    [CallbackQueryHandler(main_menu, pattern="^menu_")],
            LEAVE_TYPE:   [CallbackQueryHandler(select_leave_type, pattern="^leave_")],
            LEAVE_START:  [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_start_date)],
            LEAVE_RETURN: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_return_date)],
            LEAVE_DEST:   [CallbackQueryHandler(select_destination, pattern="^dest_")],
            LEAVE_CITY_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_city_from)],
            LEAVE_COUNTRY:   [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_country)],
            LEAVE_CONFIRM:   [CallbackQueryHandler(confirm_leave, pattern="^confirm_")],
            SIGNATURE:    [MessageHandler(filters.PHOTO, receive_signature)],
            TRACK_ID:     [MessageHandler(filters.TEXT & ~filters.COMMAND, track_request)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    logger.info("✅ البوت شغال...")
    app.run_polling()


if __name__ == "__main__":
    main()
