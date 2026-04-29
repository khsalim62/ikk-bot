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


def send_sick_leave(emp: dict, leave_data: dict, photo_path: str, request_id: str):
    """يبعت إيميل إجازة مرضية مع صورة التقرير الطبي"""
    import base64
    from pathlib import Path

    emp_name = emp.get("Employee Name Eng", "")
    emp_id   = emp.get("Employee Code", "")

    region = str(emp.get("Region E", "")).strip().lower()
    to_email = HR_EMAIL_WESTERN if region == "western" else HR_EMAIL

    subject = f"[إجازة مرضية #{request_id}] {emp_name}"

    body = f"""مرحباً،

تم استلام طلب إجازة مرضية جديد.

بيانات الموظف:
الاسم: {emp_name}
الرقم الوظيفي: {emp_id}
الجنسية: {emp.get('Nationality E', '')}
الشركة/المنطقة: {emp.get('Business Unit', '')} - {emp.get('Region E', '')}

تفاصيل الإجازة:
تاريخ الذهاب: {leave_data.get('start_date', '')}
تاريخ العودة: {leave_data.get('return_date', '')}
المدة: {leave_data.get('duration', '')} يوم

رقم الطلب: #{request_id}

مرفق: صورة التقرير الطبي

تحياتي،
نظام إدارة الطلبات — IKK Group"""

    from datetime import datetime
    with open(photo_path, "rb") as f:
        data = base64.b64encode(f.read()).decode()

    from sendgrid.helpers.mail import Mail, Cc, Attachment, FileContent, FileName, FileType, Disposition
    message = Mail(
        from_email=SMTP_USER,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body,
    )
    for cc in CC_EMAILS:
        message.add_cc(Cc(cc))

    attachment = Attachment(
        FileContent(data),
        FileName("medical_report.jpg"),
        FileType("image/jpeg"),
        Disposition("attachment"),
    )
    message.add_attachment(attachment)

    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    print(f"✅ Sick leave email sent! Status: {response.status_code}")


BTR_EMAIL         = "Maryam.Almuslim@ikkgroup.com"
BTR_EMAIL_WESTERN = "Muhammad.Younis@ikkgroup.com"
BTR_CC            = ["Khaled.salim@ikkgroup.com"]

def send_btr_request(emp: dict, btr_data: dict, mename_photo: str, iqama_photo: str, request_id: str):
    """يبعت إيميل BTR مع صور MENAME والإقامة"""
    import base64
    from sendgrid.helpers.mail import Mail, Cc, Attachment, FileContent, FileName, FileType, Disposition

    emp_name = emp.get("Employee Name Eng", "")
    emp_id   = emp.get("Employee Code", "")

    service_map = {
        "hotel":        "حجز فندق فقط",
        "flight":       "حجز طيران فقط",
        "hotel_flight": "حجز فندق وطيران",
    }

    subject = "[BTR #" + request_id + "] " + emp_name + " — " + service_map.get(btr_data.get("service",""), "")

    body = """مرحباً،

تم استلام طلب حجز رحلة عمل جديد.

بيانات الموظف:
الاسم: """ + emp_name + """
الرقم الوظيفي: """ + emp_id + """
الجنسية: """ + emp.get("Nationality E", "") + """
الشركة/المنطقة: """ + emp.get("Business Unit", "") + " - " + emp.get("Region E", "") + """

تفاصيل الرحلة:
نوع الحجز: """ + service_map.get(btr_data.get("service",""), "") + """
تاريخ السفر: """ + btr_data.get("date_from", "") + """
تاريخ العودة: """ + btr_data.get("date_to", "") + """
من: """ + btr_data.get("city_from", "") + """
إلى: """ + btr_data.get("city_to", "") + """

بيانات التواصل:
الموبايل: """ + btr_data.get("phone", "") + """
الإيميل: """ + btr_data.get("email", "") + """

رقم الطلب: #""" + request_id + """

مرفق: صورة MENAME + صورة الإقامة

تحياتي،
نظام إدارة الطلبات — IKK Group"""

    region = str(emp.get("Region E", "")).strip().lower()
    to_email = BTR_EMAIL_WESTERN if region == "western" else BTR_EMAIL
    print("📧 BTR Region: " + region + " → TO: " + to_email)

    message = Mail(
        from_email=SMTP_USER,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body,
    )

    for cc in BTR_CC:
        message.add_cc(Cc(cc))

    # إرفاق صورة MENAME
    with open(mename_photo, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    message.add_attachment(Attachment(FileContent(data), FileName("mename_status.jpg"), FileType("image/jpeg"), Disposition("attachment")))

    # إرفاق صورة الإقامة
    with open(iqama_photo, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    message.add_attachment(Attachment(FileContent(data), FileName("iqama.jpg"), FileType("image/jpeg"), Disposition("attachment")))

    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    print("✅ BTR email sent! Status: " + str(response.status_code))
