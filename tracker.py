"""
tracker.py — حفظ وتتبع الطلبات في ملف JSON
"""
import json
import random
import string
from pathlib import Path
from datetime import datetime

TRACKER_FILE = Path(__file__).parent / "data" / "requests.json"


def _load() -> dict:
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(data: dict):
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_request_id() -> str:
    """يولد رقم طلب فريد مثل: LV-20250427-A3K9"""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    date_str = datetime.now().strftime("%Y%m%d")
    return f"LV-{date_str}-{suffix}"


def save_request(request_id: str, emp: dict, leave_data: dict, status: str = "pending"):
    """يحفظ الطلب في الـ tracker"""
    data = _load()
    data[request_id] = {
        "request_id":   request_id,
        "emp_id":       str(emp.get("Employee Code", "")),
        "emp_name":     str(emp.get("Employee Name Eng", "")),
        "leave_type":   leave_data.get("leave_type", ""),
        "start_date":   leave_data.get("start_date", ""),
        "return_date":  leave_data.get("return_date", ""),
        "destination":  leave_data.get("destination", ""),
        "city_from":    leave_data.get("city_from", ""),
        "country_to":   leave_data.get("country_to", ""),
        "duration":     leave_data.get("duration", ""),
        "status":       status,  # pending | approved | rejected
        "submitted_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "updated_at":   datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    _save(data)
    return data[request_id]


def get_request(request_id: str) -> dict | None:
    """بيجيب بيانات طلب بالـ ID"""
    data = _load()
    return data.get(request_id.upper())


def get_requests_by_emp(emp_id: str) -> list[dict]:
    """بيجيب كل طلبات موظف معين"""
    data = _load()
    emp_id = emp_id.lower()
    return [
        v for v in data.values()
        if str(v.get("emp_id", "")).lower() == emp_id
    ]


def format_request_status(req: dict) -> str:
    """يرجع نص مقروء عن حالة الطلب"""
    status_map = {
        "pending":  "⏳ قيد المراجعة",
        "approved": "✅ تمت الموافقة",
        "rejected": "❌ مرفوض",
    }
    leave_type_map = {
        "annual": "إجازة سنوية",
        "sick":   "إجازة مرضية",
        "unpaid": "إجازة بدون راتب",
    }
    dest = "خارج المملكة" if req.get("destination") == "outside" else "داخل المملكة"
    if req.get("destination") == "outside" and req.get("country_to"):
        dest += f" ({req['country_to']})"

    return (
        f"📋 *رقم الطلب:* `{req['request_id']}`\n"
        f"👤 *الموظف:* {req['emp_name']}\n"
        f"🏖 *النوع:* {leave_type_map.get(req['leave_type'], req['leave_type'])}\n"
        f"📅 *من:* {req['start_date']}  →  *حتى:* {req['return_date']}\n"
        f"🌍 *الوجهة:* {dest}\n"
        f"📊 *الحالة:* {status_map.get(req['status'], req['status'])}\n"
        f"🕐 *قُدِّم في:* {req['submitted_at']}"
    )
