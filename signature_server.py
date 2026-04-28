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

PENDING_SIGNATURES: dict = {}
BOT_APP = None


def get_base_url() -> str:
    return os.getenv("BASE_URL", "http://localhost:8080")


def create_signature_token(chat_id: int, emp: dict, leave_data: dict, request_id: str) -> str:
    token = str(uuid.uuid4()).replace("-", "")[:16]
    PENDING_SIGNATURES[token] = {
        "chat_id":    chat_id,
        "emp":        emp,
        "leave_data": leave_data,
        "request_id": request_id,
    }
    return token


def get_signature_url(token: str, emp_name: str, req_id: str, leave_type: str) -> str:
    base = get_base_url()
    return (
        f"{base}/sign-page"
        f"?token={token}"
        f"&name={emp_name.replace(' ', '+')}"
        f"&req={req_id}"
        f"&type={leave_type}"
    )


async def signature_page(request: web.Request) -> web.Response:
    html_path = Path(__file__).parent / "signature.html"
    html = html_path.read_text(encoding="utf-8")
    return web.Response(text=html, content_type="text/html")


async def receive_signature(request: web.Request) -> web.Response:
    try:
        data    = await request.json()
        token   = data.get("token", "")
        sig_b64 = data.get("signature", "")

        pending = PENDING_SIGNATURES.get(token)
        if not pending:
            return web.Response(status=404, text="Token not found")

        sig_data  = sig_b64.split(",")[1] if "," in sig_b64 else sig_b64
        sig_bytes = base64.b64decode(sig_data)
        sig_path  = SIGNATURES_DIR / f"sig_{token}.png"
        sig_path.write_bytes(sig_bytes)

        del PENDING_SIGNATURES[token]

        if BOT_APP:
            asyncio.create_task(
                process_signed_request(
                    pending["chat_id"],
                    pending["emp"],
                    pending["leave_data"],
                    pending["request_id"],
                    str(sig_path)
                )
            )

        return web.Response(text="OK")

    except Exception as e:
        return web.Response(status=500, text=str(e))


async def health(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def telegram_webhook(request: web.Request) -> web.Response:
    """يستقبل updates من تيليجرام عبر webhook"""
    if BOT_APP is None:
        return web.Response(status=503, text="Bot not ready")
    try:
        data   = await request.json()
        from telegram import Update
        update = Update.de_json(data, BOT_APP.bot)
        await BOT_APP.process_update(update)
    except Exception as e:
        print(f"Webhook error: {e}")
    return web.Response(text="OK")


async def process_signed_request(chat_id: int, emp: dict, leave_data: dict, request_id: str, sig_path: str):
    import tempfile
    from pdf_filler import fill_leave_form, fill_declaration_form, add_signature_to_pdf
    from email_sender import send_leave_request
    from tracker import save_request

    try:
        tmp_dir   = Path(tempfile.mkdtemp())
        from pdf_filler import add_signature_to_pdf

        # ملء فورم الإجازة
        leave_pdf_filled = tmp_dir / f"leave_filled_{request_id}.pdf"
        fill_leave_form(emp, leave_data, leave_pdf_filled)

        # إضافة التوقيع
        leave_pdf = tmp_dir / f"leave_{request_id}.pdf"
        add_signature_to_pdf(leave_pdf_filled, Path(sig_path), leave_pdf)
        pdf_paths = [leave_pdf]

        if leave_data.get("destination") == "outside":
            decl_pdf = tmp_dir / f"declaration_{request_id}.pdf"
            fill_declaration_form(emp, leave_data, decl_pdf)
            pdf_paths.append(decl_pdf)

        save_request(request_id, emp, leave_data)

        try:
            send_leave_request(emp, leave_data, pdf_paths, request_id)
            email_status = "✅ تم إرسال طلبك لقسم الموارد البشرية"
        except Exception:
            email_status = "⚠️ تم حفظ طلبك — سيتم إرساله قريباً"

        if BOT_APP:
            msg = (
                "تم تقديم طلبك بنجاح!\n\n"
                f"رقم الطلب: {request_id}\n"
                f"{emp.get('Employee Name Eng', '')}\n"
                f"{leave_data.get('start_date', '')} - {leave_data.get('return_date', '')}\n\n"
                f"{email_status}\n\n"
                "احتفظ برقم الطلب للمتابعة"
            )
            await BOT_APP.bot.send_message(chat_id=chat_id, text=msg)

    except Exception as e:
        print(f"Error processing request {request_id}: {e}")
        if BOT_APP:
            await BOT_APP.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ حدث خطأ. تواصل مع HR برقم الطلب: {request_id}"
            )


@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })
    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


def create_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/sign-page", signature_page)
    app.router.add_post("/sign",     receive_signature)
    app.router.add_options("/sign",  lambda r: web.Response(headers={
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }))
    app.router.add_get("/health",       health)
    app.router.add_post("/telegram",    telegram_webhook)
    return app
