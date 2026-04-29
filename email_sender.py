"""
email_sender.py — إرسال إيميل لـ HR عبر SendGrid
"""
import os
import base64
from pathlib import Path
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Cc, Attachment, FileContent, FileName,
    FileType, Disposition
)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SMTP_USER        = os.getenv("SMTP_USER", "cres.hr1@gmail.com")
HR_EMAIL         = os.getenv("HR_EMAIL", "Yassir.Mohammad@ikkgroup.com")
HR_EMAIL_WESTERN = "Muhammad.Younis@ikkgroup.com"

CC_EMAILS = [
    "syed.moin@ikkgroup.com",
    "Amr.Hegazy@ikkgroup.com",
    "Khaled.Salim@ikkgroup.com",
]


def send_leave_request(emp: dict, leave_data: dict, pdf_paths: list[Path], request_id: str):
    emp_name = emp.get("Employee Name Eng", "")
    emp_id   = emp.get("Employee Code", "")
    emp_pos  = emp.get("Postition E", "")

    region = str(emp.get("Region E", "")).strip().lower()
    to_email = HR_EMAIL_WESTERN if region == "western" else HR_EMAIL
    print(f"📧 Region: {region} → TO: {to_email}")

    leave_type_ar = {
        "annual": "إجازة سنوية",
        "sick":   "إجازة مرضية",
        "unpaid": "إجازة بدون راتب",
    }.get(leave_data.get("leave_type", ""), "إجازة")

    dest_ar = "خارج المملكة" if leave_data.get("destination") == "outside" else "داخل المملكة"
    if leave_data.get("destination") == "outside":
        dest_ar += f" — {leave_data.get('city_from', '')} -> {leave_data.get('country_to', '')}"

    subject = f"[طلب إجازة #{request_id}] {emp_name} — {leave_type_ar}"

    body = f"""مرحباً،

تم استلام طلب إجازة جديد من خلال البوت.

بيانات الموظف:
الاسم: {emp_name}
الرقم الوظيفي: {emp_id}
المسمى: {emp_pos}
الجنسية: {emp.get('Nationality E', '')}
الشركة/المنطقة: {emp.get('Business Unit', '')} - {emp.get('Region E', '')}

تفاصيل الإجازة:
نوع الإجازة: {leave_type_ar}
تاريخ الذهاب: {leave_data.get('start_date', '')}
تاريخ العودة: {leave_data.get('return_date', '')}
المدة: {leave_data.get('duration', '')} يوم
الوجهة: {dest_ar}

رقم الطلب: #{request_id}
تاريخ التقديم: {datetime.now().strftime('%d/%m/%Y %H:%M')}

تحياتي،
نظام إدارة الطلبات — IKK Group"""

    message = Mail(
        from_email=SMTP_USER,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body,
    )

    for cc in CC_EMAILS:
        message.add_cc(Cc(cc))

    for pdf_path in pdf_paths:
        with open(pdf_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        attachment = Attachment(
            FileContent(data),
            FileName(pdf_path.name),
            FileType("application/pdf"),
            Disposition("attachment"),
        )
        message.add_attachment(attachment)

    print(f"📧 Sending via SendGrid to {to_email} + CC")

    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    print(f"✅ Email sent! Status: {response.status_code}")
