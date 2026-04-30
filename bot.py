"""
email_sender.py — Send emails via SendGrid (all content in English)
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

SIGNATURE_TEXT = """

--
Regards,
CRES Administration Team
IKK Group"""

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SMTP_USER        = os.getenv("SMTP_USER", "cres.hr1@gmail.com")
HR_EMAIL         = os.getenv("HR_EMAIL", "Yassir.Mohammad@ikkgroup.com")
HR_EMAIL_WESTERN = "Muhammad.Younis@ikkgroup.com"

CC_EMAILS = [
    "syed.moin@ikkgroup.com",
    "Amr.Hegazy@ikkgroup.com",
    "Khaled.Salim@ikkgroup.com",
]

LEAVE_TYPE_MAP = {
    "annual": "Annual Leave",
    "sick":   "Sick Leave",
    "unpaid": "Unpaid Leave",
}

DEST_MAP = {
    "inside":  "Inside KSA",
    "outside": "Outside KSA",
}


def send_leave_request(emp: dict, leave_data: dict, pdf_paths: list[Path], request_id: str):
    emp_name = emp.get("Employee Name Eng", "")
    emp_id   = emp.get("Employee Code", "")
    emp_pos  = emp.get("Postition E", "")

    region = str(emp.get("Region E", "")).strip().lower()
    to_email = HR_EMAIL_WESTERN if region == "western" else HR_EMAIL
    print(f"📧 Region: {region} → TO: {to_email}")

    leave_type = LEAVE_TYPE_MAP.get(leave_data.get("leave_type", ""), "Leave")
    dest = DEST_MAP.get(leave_data.get("destination", "inside"), "Inside KSA")
    if leave_data.get("destination") == "outside":
        dest += f" — {leave_data.get('city_from', '')} -> {leave_data.get('country_to', '')}"

    subject = f"[Leave Request #{request_id}] {emp_name} — {leave_type}"

    body = f"""Dear HR Team,

A new leave request has been submitted via the self-service bot.

Employee Information:
Name:            {emp_name}
Employee ID:     {emp_id}
Position:        {emp_pos}
Nationality:     {emp.get('Nationality E', '')}
Company/Region:  {emp.get('Business Unit', '')} - {emp.get('Region E', '')}

Leave Details:
Leave Type:      {leave_type}
Start Date:      {leave_data.get('start_date', '')}
Return Date:     {leave_data.get('return_date', '')}
Duration:        {leave_data.get('duration', '')} days
Destination:     {dest}

Request ID:      #{request_id}
Submitted:       {datetime.now().strftime('%d/%m/%Y %H:%M')}

Attached: Signed leave form

Best regards,
IKK Group — HR Self-Service System"""

    message = Mail(
        from_email=SMTP_USER,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body + SIGNATURE_TEXT,
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
    emp_name = emp.get("Employee Name Eng", "")
    emp_id   = emp.get("Employee Code", "")

    region = str(emp.get("Region E", "")).strip().lower()
    to_email = HR_EMAIL_WESTERN if region == "western" else HR_EMAIL

    subject = f"[Sick Leave #{request_id}] {emp_name}"

    body = f"""Dear HR Team,

A new sick leave request has been submitted.

Employee Information:
Name:            {emp_name}
Employee ID:     {emp_id}
Nationality:     {emp.get('Nationality E', '')}
Company/Region:  {emp.get('Business Unit', '')} - {emp.get('Region E', '')}

Leave Details:
Start Date:      {leave_data.get('start_date', '')}
Return Date:     {leave_data.get('return_date', '')}
Duration:        {leave_data.get('duration', '')} days

Request ID:      #{request_id}

Attached: Medical report photo

Best regards,
IKK Group — HR Self-Service System"""

    with open(photo_path, "rb") as f:
        data = base64.b64encode(f.read()).decode()

    message = Mail(
        from_email=SMTP_USER,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body + SIGNATURE_TEXT,
    )
    for cc in CC_EMAILS:
        message.add_cc(Cc(cc))

    message.add_attachment(Attachment(
        FileContent(data),
        FileName("medical_report.jpg"),
        FileType("image/jpeg"),
        Disposition("attachment"),
    ))
    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    print(f"✅ Sick leave email sent! Status: {response.status_code}")


BTR_EMAIL         = "Maryam.Almuslim@ikkgroup.com"
BTR_EMAIL_WESTERN = "Muhammad.Younis@ikkgroup.com"
BTR_CC            = ["Khaled.salim@ikkgroup.com"]

SERVICE_MAP = {
    "hotel":        "Hotel Only",
    "flight":       "Flight Only",
    "hotel_flight": "Hotel & Flight",
}


def send_btr_request(emp: dict, btr_data: dict, mename_photo: str, iqama_photo: str, request_id: str):
    emp_name = emp.get("Employee Name Eng", "")
    emp_id   = emp.get("Employee Code", "")

    service = SERVICE_MAP.get(btr_data.get("service", ""), "")

    region = str(emp.get("Region E", "")).strip().lower()
    to_email = BTR_EMAIL_WESTERN if region == "western" else BTR_EMAIL
    print(f"📧 BTR Region: {region} → TO: {to_email}")

    subject = f"[BTR #{request_id}] {emp_name} — {service}"

    body = f"""Dear Travel Team,

A new Business Trip Request has been submitted via the self-service bot.

Employee Information:
Name:            {emp_name}
Employee ID:     {emp_id}
Nationality:     {emp.get('Nationality E', '')}
Company/Region:  {emp.get('Business Unit', '')} - {emp.get('Region E', '')}

Trip Details:
Booking Type:    {service}
Travel Date:     {btr_data.get('date_from', '')}
Return Date:     {btr_data.get('date_to', '')}
From:            {btr_data.get('city_from', '')}
To:              {btr_data.get('city_to', '')}

Contact Information:
Mobile:          {btr_data.get('phone', '')}
Email:           {btr_data.get('email', '')}

Request ID:      #{request_id}
Submitted:       {datetime.now().strftime('%d/%m/%Y %H:%M')}

Attached: MENAME screenshot + Iqama photo

Best regards,
IKK Group — HR Self-Service System"""

    message = Mail(
        from_email=SMTP_USER,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body + SIGNATURE_TEXT,
    )

    for cc in BTR_CC:
        message.add_cc(Cc(cc))

    with open(mename_photo, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    message.add_attachment(Attachment(FileContent(data), FileName("mename_status.jpg"), FileType("image/jpeg"), Disposition("attachment")))

    with open(iqama_photo, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    message.add_attachment(Attachment(FileContent(data), FileName("iqama.jpg"), FileType("image/jpeg"), Disposition("attachment")))

    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    print(f"✅ BTR email sent! Status: {response.status_code}")


def send_flight_request(emp: dict, flt_data: dict, mename_photo: str, passport_photo: str, companion_passports: list, request_id: str):
    from sendgrid.helpers.mail import Mail, Cc, Attachment, FileContent, FileName, FileType, Disposition

    emp_name = emp.get("Employee Name Eng", "")
    emp_id   = emp.get("Employee Code", "")
    region   = str(emp.get("Region E", "")).strip().lower()
    to_email = BTR_EMAIL_WESTERN if region == "western" else BTR_EMAIL
    companions = flt_data.get("companion_count", 0)
    comp_str = str(companions) + " companion(s)" if companions > 0 else "Traveling alone"
    subject = "[Vacation Flight #" + request_id + "] " + emp_name

    body = "Dear Travel Team,\n\nA new Vacation Flight Booking request has been submitted.\n\n"
    body += "Employee Information:\n"
    body += "Name:            " + emp_name + "\n"
    body += "Employee ID:     " + emp_id + "\n"
    body += "Nationality:     " + emp.get("Nationality E", "") + "\n"
    body += "Company/Region:  " + emp.get("Business Unit", "") + " - " + emp.get("Region E", "") + "\n\n"
    body += "Travel Details:\nCompanions:      " + comp_str + "\nFrom:            " + flt_data.get("city_from", "") + "\nTo:              " + flt_data.get("city_to", "") + "\n\n"
    body += "Contact Information:\nMobile:          " + flt_data.get("phone", "") + "\n"
    body += "Email:           " + flt_data.get("email", "") + "\n\n"
    body += "Request ID:      #" + request_id + "\n"
    body += "Submitted:       " + datetime.now().strftime("%d/%m/%Y %H:%M") + "\n\n"
    body += "Attached: MENAME screenshot + Passport photo(s)\n\nBest regards,\nIKK Group — HR Self-Service System"

    message = Mail(from_email=SMTP_USER, to_emails=to_email, subject=subject, plain_text_content=body + SIGNATURE_TEXT)
    for cc in BTR_CC:
        message.add_cc(Cc(cc))

    with open(mename_photo, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    message.add_attachment(Attachment(FileContent(data), FileName("mename_leave.jpg"), FileType("image/jpeg"), Disposition("attachment")))

    with open(passport_photo, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    message.add_attachment(Attachment(FileContent(data), FileName("passport_employee.jpg"), FileType("image/jpeg"), Disposition("attachment")))

    for i, cp in enumerate(companion_passports, 1):
        with open(cp, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        message.add_attachment(Attachment(FileContent(data), FileName("passport_companion_" + str(i) + ".jpg"), FileType("image/jpeg"), Disposition("attachment")))

    sg = SendGridAPIClient(SENDGRID_API_KEY)
    response = sg.send(message)
    print("✅ Flight request email sent! Status: " + str(response.status_code))
