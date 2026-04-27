"""
bot.py — IKK Group HR Bot
"""
import os
import logging
import tempfile
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

LANG, IDENTIFY, MAIN_MENU, LEAVE_TYPE, LEAVE_START, LEAVE_RETURN, LEAVE_DEST, LEAVE_CITY_FROM, LEAVE_COUNTRY, LEAVE_CONFIRM, SIGNATURE, TRACK_ID = range(12)

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
    await update.message.reply_text(t(ctx, "welcome_emp", name=get_display_name(emp)), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return MAIN_MENU

async def main_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "menu_leave":
        kb = [
            [InlineKeyboardButton(t(ctx, "leave_annual"), callback_data="leave_annual")],
            [InlineKeyboardButton(t(ctx, "leave_sick"), callback_data="leave_sick")],
            [InlineKeyboardButton(t(ctx, "leave_unpaid"), callback_data="leave_unpaid")],
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

async def leave_start_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        datetime.strptime(update.message.text.strip(), "%Y-%m-%d")
        ctx.user_data["start_date"] = update.message.text.strip()
        await update.message.reply_text(t(ctx, "enter_return"))
        return LEAVE_RETURN
    except ValueError:
        await update.message.reply_text(t(ctx, "invalid_date"))
        return LEAVE_START

async def leave_return_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        ret = datetime.strptime(update.message.text.strip(), "%Y-%m-%d").date()
        start = datetime.strptime(ctx.user_data["start_date"], "%Y-%m-%d").date()
        if ret <= start:
            await update.message.reply_text(t(ctx, "return_before"))
            return LEAVE_RETURN
        ctx.user_data["return_date"] = update.message.text.strip()
        ctx.user_data["duration"] = (ret - start).days
        kb = [
            [InlineKeyboardButton(t(ctx, "dest_inside"), callback_data="dest_inside")],
            [InlineKeyboardButton(t(ctx, "dest_outside"), callback_data="dest_outside")],
        ]
        await update.message.reply_text(t(ctx, "select_dest"), reply_markup=InlineKeyboardMarkup(kb))
        return LEAVE_DEST
    except ValueError:
        await update.message.reply_text(t(ctx, "invalid_date"))
        return LEAVE_RETURN

async def select_destination(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data["destination"] = "inside" if q.data == "dest_inside" else "outside"
    if ctx.user_data["destination"] == "outside":
        await q.edit_message_text(t(ctx, "enter_city_from"))
        return LEAVE_CITY_FROM
    return await show_confirm_cb(q, ctx)

async def leave_city_from(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["city_from"] = update.message.text.strip()
    await update.message.reply_text(t(ctx, "enter_country"))
    return LEAVE_COUNTRY

async def leave_country(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["country_to"] = update.message.text.strip()
    return await show_confirm_msg(update, ctx)

def build_summary(ctx):
    ud = ctx.user_data
    emp = ud.get("emp", {})
    lmap = {"annual": "سنوية/Annual", "sick": "مرضية/Sick", "unpaid": "بدون راتب/Unpaid"}
    dest = "داخل المملكة" if ud.get("destination") == "inside" else f"خارج المملكة - {ud.get('city_from','')} → {ud.get('country_to','')}"
    return f"👤 *{emp.get('Employee Name Eng','')}*\n🏖 {lmap.get(ud.get('leave_type',''),'')}\n📅 {ud.get('start_date')} → {ud.get('return_date')}\n⏱ {ud.get('duration')} يوم\n🌍 {dest}"

async def show_confirm_cb(q, ctx):
    kb = [[InlineKeyboardButton(t(ctx,"confirm_yes"),callback_data="confirm_yes"),(InlineKeyboardButton(t(ctx,"confirm_no"),callback_data="confirm_no"))]]
    await q.edit_message_text(t(ctx,"confirm_title")+build_summary(ctx), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return LEAVE_CONFIRM

async def show_confirm_msg(update, ctx):
    kb = [[(InlineKeyboardButton(t(ctx,"confirm_yes"),callback_data="confirm_yes")),(InlineKeyboardButton(t(ctx,"confirm_no"),callback_data="confirm_no"))]]
    await update.message.reply_text(t(ctx,"confirm_title")+build_summary(ctx), reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return LEAVE_CONFIRM

async def confirm_leave(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "confirm_no":
        await q.edit_message_text(t(ctx, "cancel"))
        return ConversationHandler.END
    ud = ctx.user_data
    emp = ud.get("emp", {})
    request_id = generate_request_id()
    ctx.user_data["request_id"] = request_id
    leave_data = {
        "leave_type": ud.get("leave_type","annual"),
        "start_date": ud.get("start_date",""),
        "return_date": ud.get("return_date",""),
        "destination": ud.get("destination","inside"),
        "city_from": ud.get("city_from",""),
        "country_to": ud.get("country_to",""),
        "duration": ud.get("duration",0),
    }
    token = sig_srv.create_signature_token(q.message.chat_id, emp, leave_data, request_id)
    sig_url = sig_srv.get_signature_url(token, emp.get("Employee Name Eng",""), request_id, ud.get("leave_type","annual"))
    lang = ud.get("lang","ar")
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

def main():
    import asyncio
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not found!")
    base_url = os.getenv("BASE_URL", "")
    port = int(os.getenv("PORT", "8080"))

    ptb_app = Application.builder().token(token).build()
    sig_srv.BOT_APP = ptb_app

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [CallbackQueryHandler(select_language, pattern="^lang_")],
            IDENTIFY: [MessageHandler(filters.TEXT & ~filters.COMMAND, identify_employee)],
            MAIN_MENU: [CallbackQueryHandler(main_menu, pattern="^menu_")],
            LEAVE_TYPE: [CallbackQueryHandler(select_leave_type, pattern="^leave_")],
            LEAVE_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_start_date)],
            LEAVE_RETURN: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_return_date)],
            LEAVE_DEST: [CallbackQueryHandler(select_destination, pattern="^dest_")],
            LEAVE_CITY_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_city_from)],
            LEAVE_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, leave_country)],
            LEAVE_CONFIRM: [CallbackQueryHandler(confirm_leave, pattern="^confirm_")],
            SIGNATURE: [MessageHandler(filters.PHOTO, receive_signature)],
            TRACK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, track_request)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    ptb_app.add_handler(conv)

    async def telegram_webhook(request):
        try:
            data = await request.json()
            update = Update.de_json(data, ptb_app.bot)
            await ptb_app.process_update(update)
            return web.Response(text="OK")
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return web.Response(text="OK")

    async def run_all():
        # شغّل الـ web server الأول عشان Railway يشوفه
        web_app = sig_srv.create_app()
        web_app.router.add_post("/telegram", telegram_webhook)
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Server on port {port}")

        # شغّل البوت
        await ptb_app.initialize()
        await ptb_app.start()
        logger.info("Bot started")

        # سجّل الـ webhook
        if base_url:
            webhook_url = f"{base_url}/telegram"
            await ptb_app.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
            logger.info(f"Webhook: {webhook_url}")

        await asyncio.Event().wait()

    asyncio.run(run_all())

if __name__ == "__main__":
    main()
