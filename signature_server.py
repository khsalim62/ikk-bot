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
        token     = data.get("token", "")
        sig_b64   = data.get("signature", "")

        pending = PENDING_SIGNATURES.get(token)
        if not pending:
            return web.Response(status=404, text="Token not found")

        # حفظ صورة التوقيع
        sig_data = sig_b64.split(",")[1] if "," in sig_b64 else sig_b64
        sig_bytes = base64.b64decode(sig_data)
        sig_path = SIGNATURES_DIR / f"sig_{token}.png"
        sig_path.write_bytes(sig_bytes)

        # إرسال للبوت عبر queue
        if BOT_APP:
            await BOT_APP.update_queue.put({
                "type":       "signature_received",
                "token":      token,
                "sig_path":   str(sig_path),
                "pending":    pending,
            })

        # مسح الـ token
        del PENDING_SIGNATURES[token]

        return web.Response(text="OK")

    except Exception as e:
        return web.Response(status=500, text=str(e))


async def health(request: web.Request) -> web.Response:
    return web.Response(text="OK")


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/sign-page", signature_page)
    app.router.add_post("/sign", receive_signature)
    app.router.add_get("/health", health)
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
