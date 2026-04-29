"""
signature_server.py — سيرفر صغير يعرض صفحة التوقيع ويستقبله
يشتغل جنب البوت على نفس السيرفر
"""
import os
import base64
import asyncio
import uuid
from pathlib import Path
from aiohttp import web

SIGNATURES_DIR = Path(__file__).parent / "signatures"
SIGNATURES_DIR.mkdir(exist_ok=True)

# dict مؤقت: token → chat_id + request_data
PENDING_SIGNATURES: dict = {}

# الـ bot application (يتسيت من bot.py)
BOT_APP = None


def get_base_url() -> str:
    """رابط السيرفر — يتجيب من الـ Environment"""
    return os.getenv("BASE_URL", "http://localhost:8080")


def create_signature_token(chat_id: int, emp: dict, leave_data: dict, request_id: str) -> str:
    """يولد token فريد للتوقيع ويحفظ البيانات"""
    token = str(uuid.uuid4()).replace("-", "")[:16]
    PENDING_SIGNATURES[token] = {
        "chat_id":    chat_id,
        "emp":        emp,
        "leave_data": leave_data,
        "request_id": request_id,
    }
    return token


def get_signature_url(token: str, emp_name: str, req_id: str, leave_type: str) -> str:
    """يرجع الرابط الكامل لصفحة التوقيع"""
    base = get_base_url()
    return (
        f"{base}/sign-page"
        f"?token={token}"
        f"&name={emp_name.replace(' ', '+')}"
        f"&req={req_id}"
        f"&type={leave_type}"
    )


# ===== Routes =====

async def signature_page(request: web.Request) -> web.Response:
    """يعرض صفحة HTML للتوقيع"""
    html_path = Path(__file__).parent / "signature.html"
    html = html_path.read_text(encoding="utf-8")
    return web.Response(text=html, content_type="text/html")


async def receive_signature(request: web.Request) -> web.Response:
    """يستقبل التوقيع من الصفحة ويبعته للبوت"""
    try:
        data = await request.json()
        token   = data.get("token", "")
        sig_b64 = data.get("signature", "")

        pending = PENDING_SIGNATURES.get(token)
        if not pending:
            return web.Response(status=404, text="Token not found")

        # حفظ صورة التوقيع
        sig_data = sig_b64.split(",")[1] if "," in sig_b64 else sig_b64
        sig_bytes = base64.b64decode(sig_data)
        sig_path = SIGNATURES_DIR / f"sig_{token}.png"
        sig_path.write_bytes(sig_bytes)

        # مسح الـ token
        del PENDING_SIGNATURES[token]

        # ملء الـ PDF وإرسال الإيميل
        if BOT_APP:
            chat_id    = pending["chat_id"]
            request_id = pending["request_id"]
            emp        = pending["emp"]
            leave_data = pending["leave_data"]

            asyncio.create_task(
                process_signed_request(chat_id, emp, leave_data, request_id, str(sig_path))
            )

        return web.Response(text="OK")

    except Exception as e:
        return web.Response(status=500, text=str(e))


async def health(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def process_signed_request(chat_id: int, emp: dict, leave_data: dict, request_id: str, sig_path: str):
    """يملأ الـ PDF ويبعت الإيميل ويبعت رسالة تأكيد للموظف"""
    import tempfile
    from pathlib import Path
    from pdf_filler import fill_leave_form, fill_declaration_form
    from email_sender import send_leave_request
    from tracker import save_request

    try:
        tmp_dir = Path(tempfile.mkdtemp())

        from pdf_filler import add_signature_to_pdf

        # ملء فورم الإجازة + إضافة التوقيع
        leave_pdf_filled = tmp_dir / f"leave_filled_{request_id}.pdf"
        fill_leave_form(emp, leave_data, leave_pdf_filled)
        leave_pdf = tmp_dir / f"leave_{request_id}.pdf"
        add_signature_to_pdf(leave_pdf_filled, Path(sig_path), leave_pdf)
        pdf_paths = [leave_pdf]

        # فورم الإقرار لو السفر برة المملكة + إضافة التوقيع
        if leave_data.get("destination") == "outside":
            decl_pdf_filled = tmp_dir / f"declaration_filled_{request_id}.pdf"
            fill_declaration_form(emp, leave_data, decl_pdf_filled)
            decl_pdf = tmp_dir / f"declaration_{request_id}.pdf"
            add_signature_to_pdf(decl_pdf_filled, Path(sig_path), decl_pdf, field_id="Signature4")
            pdf_paths.append(decl_pdf)

        # حفظ الطلب
        save_request(request_id, emp, leave_data)

        # إرسال الإيميل
        try:
            send_leave_request(emp, leave_data, pdf_paths, request_id)
            email_status = "✅ تم إرسال طلبك لقسم الموارد البشرية"
        except Exception as e:
            email_status = "⚠️ تم حفظ طلبك — سيتم إرساله قريباً"

        # رسالة تأكيد للموظف في تيليجرام
        if BOT_APP:
            emp_name   = emp.get("Employee Name Eng", "")
            start_date = leave_data.get("start_date", "")
            end_date   = leave_data.get("return_date", "")
            lang       = leave_data.get("lang", "ar")
            if lang == "en":
                done_msg = f"Your request has been submitted successfully!\n\nRequest ID: {request_id}\n{emp_name}\n{start_date} - {end_date}\n\n{email_status}\n\nKeep your request ID for follow-up."
            elif lang == "ur":
                done_msg = f"آپ کی درخواست کامیابی سے جمع ہو گئی!\n\nدرخواست نمبر: {request_id}\n{emp_name}\n{start_date} - {end_date}\n\n{email_status}\n\nپیروی کے لیے نمبر محفوظ رکھیں۔"
            else:
                done_msg = f"تم تقديم طلبك بنجاح!\n\nرقم الطلب: {request_id}\n{emp_name}\n{start_date} - {end_date}\n\n{email_status}\n\nاحتفظ برقم الطلب للمتابعة"
            await BOT_APP.bot.send_message(chat_id=chat_id, text=done_msg)
    except Exception as e:
        print(f"Error processing request {request_id}: {e}")
        if BOT_APP:
            await BOT_APP.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ حدث خطأ في معالجة طلبك. تواصل مع HR مع رقم الطلب: {request_id}"
            )


async def telegram_webhook(request: web.Request) -> web.Response:
    """يستقبل updates من تيليجرام عبر webhook"""
    if BOT_APP is None:
        return web.Response(status=503)
    try:
        data = await request.json()
        from telegram import Update
        update = Update.de_json(data, BOT_APP.bot)
        await BOT_APP.process_update(update)
    except Exception as e:
        print(f"Webhook error: {e}")
    return web.Response(text="OK")


@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        return web.Response(
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
        )
    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


def create_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/sign-page", signature_page)
    app.router.add_post("/sign", receive_signature)
    app.router.add_options("/sign", lambda r: web.Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }))
    app.router.add_get("/health", health)
    # ✅ الـ telegram webhook مسجل هنا مباشرة
    app.router.add_post("/telegram", telegram_webhook)
    return app


async def start_server():
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Signature server running on port {port}")
    return runner
