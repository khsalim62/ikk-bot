"""
pdf_filler.py — ملء فورم الإجازة وفورم الإقرار تلقائياً + إضافة التوقيع
"""
import json
import shutil
from pathlib import Path
from datetime import date, datetime

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject, ArrayObject, DictionaryObject

FORMS_DIR = Path(__file__).parent / "forms"
LEAVE_FORM = FORMS_DIR / "Leave_form_fillable.pdf"
DECL_FORM  = FORMS_DIR / "Declaration_Form_.pdf"

# ===== خريطة الحقول =====
# Group1 = نوع الإجازة:
#   /Choice1 = Paid Leave (سنوية)
#   /Choice2 = Unpaid Leave (بدون راتب)
#   /Choice3 = Sick Leave (مرضية)
#   /Choice4 = Marriage Leave
#   /Choice5 = Birth Leave
#   /Choice6 = Other
#
# Group2 = الوجهة:
#   /Choice1 = Inside KSA
#   /Choice2 = Outside KSA
#
# Group3 = Ticket:
#   /0 = Cash
#   /1 = Ticket
#
# Group4 = Passport Required:
#   /Choice1 = Yes
#   /Choice2 = No

LEAVE_TYPE_MAP = {
    "annual":    "/Choice1",   # إجازة سنوية (Paid Leave)
    "unpaid":    "/Choice2",   # بدون راتب
    "sick":      "/Choice3",   # مرضية
}

DESTINATION_MAP = {
    "inside":  "/Choice1",
    "outside": "/Choice2",
}


def _set_field(writer: PdfWriter, field_id: str, value):
    """تعديل قيمة حقل في الـ PDF"""
    for page in writer.pages:
        if "/Annots" not in page:
            continue
        for annot in page["/Annots"]:
            obj = annot.get_object()
            if obj.get("/T") == field_id:
                obj.update({
                    NameObject("/V"): NameObject(value) if value.startswith("/") else value,
                    NameObject("/AS"): NameObject(value) if value.startswith("/") else NameObject("/Off"),
                })
                if not value.startswith("/"):
                    obj.update({NameObject("/AS"): NameObject("/Off")})


def _set_text_field(writer: PdfWriter, field_id: str, value: str):
    """تعيين قيمة حقل نصي"""
    for page in writer.pages:
        if "/Annots" not in page:
            continue
        for annot in page["/Annots"]:
            obj = annot.get_object()
            if obj.get("/T") == field_id:
                obj.update({NameObject("/V"): str(value)})


def _set_radio(writer: PdfWriter, field_id: str, value: str):
    """تعيين قيمة radio button"""
    for page in writer.pages:
        if "/Annots" not in page:
            continue
        for annot in page["/Annots"]:
            obj = annot.get_object()
            if obj.get("/T") == field_id:
                obj.update({
                    NameObject("/V"):  NameObject(value),
                    NameObject("/AS"): NameObject(value),
                })


def fill_leave_form(emp: dict, leave_data: dict, output_path: Path) -> Path:
    """
    يملأ فورم الإجازة ويحفظه في output_path.
    
    leave_data keys:
        leave_type:   "annual" | "sick" | "unpaid"
        start_date:   "YYYY-MM-DD"
        return_date:  "YYYY-MM-DD"
        destination:  "inside" | "outside"
        city_from:    مدينة المغادرة (لو outside)
        country_to:   البلد المقصود (لو outside)
        duration:     عدد الأيام (int)
    """
    from employees import get_company_region

    reader = PdfReader(str(LEAVE_FORM))
    writer = PdfWriter()
    writer.append(reader)

    # بيانات الموظف التلقائية
    _set_text_field(writer, "Emp name",        str(emp.get("Employee Name Eng", "")))
    _set_text_field(writer, "emp position",    str(emp.get("Postition E", "")))
    _set_text_field(writer, "ID Number",       str(emp.get("Employee Code", "")))
    _set_text_field(writer, "emp nationality", str(emp.get("Nationality E", "")))
    _set_text_field(writer, "company & Region", get_company_region(emp))
    _set_text_field(writer, "Contact Numbers", str(emp.get("Mobile", "")))

    # بيانات الإجازة
    leave_type_val = LEAVE_TYPE_MAP.get(leave_data.get("leave_type", "annual"), "/Choice1")
    _set_radio(writer, "Group1", leave_type_val)

    _set_text_field(writer, "leave start date", leave_data.get("start_date", ""))
    _set_text_field(writer, "leave return date", leave_data.get("return_date", ""))
    _set_text_field(writer, "Duration", str(leave_data.get("duration", "")))

    dest = leave_data.get("destination", "inside")
    _set_radio(writer, "Group2", DESTINATION_MAP.get(dest, "/Choice1"))

    if dest == "outside":
        city_from   = leave_data.get("city_from", "")
        country_to  = leave_data.get("country_to", "")
        specify_val = f"{city_from} → {country_to}" if city_from else country_to
        _set_text_field(writer, "Specify", specify_val)

    # Ticket = Ticket (تذكرة من الشركة افتراضياً)
    _set_radio(writer, "Group3", "/1")
    # Passport = No (مش محتاج جواز دلوقتي)
    _set_radio(writer, "Group4", "/Choice2")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


def fill_declaration_form(emp: dict, leave_data: dict, output_path: Path) -> Path:
    """
    يملأ فورم الإقرار (للسفر خارج المملكة فقط).
    
    حقول الإقرار:
        No       = اسم الموظف (الجانب العربي: أنا الموقع أدناه)
        Text2    = اسم الموظف (الجانب الإنجليزي: I, ...)
        Text1    = الرقم الوظيفي (عربي)
        Text3    = الرقم الوظيفي (إنجليزي)
        undefined        = Employee Name (جدول التوقيعات)
        undefined_3      = Requested by
        undefined_4      = Date
        undefined_2      = Approved by
        undefined_5      = Reviewed & Noted by
    """
    emp_name = str(emp.get("Employee Name Eng", "")).strip()
    emp_id   = str(emp.get("Employee Code", "")).strip()
    today    = date.today().strftime("%d/%m/%Y")

    reader = PdfReader(str(DECL_FORM))
    writer = PdfWriter()
    writer.append(reader)

    _set_text_field(writer, "No",    emp_name)
    _set_text_field(writer, "Text2", emp_name)
    _set_text_field(writer, "Text1", emp_id)
    _set_text_field(writer, "Text3", emp_id)

    # جدول التوقيعات
    _set_text_field(writer, "undefined",   emp_name)  # Employee Name
    _set_text_field(writer, "undefined_3", emp_name)  # Requested by
    _set_text_field(writer, "undefined_4", today)     # Date

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


def add_signature_to_pdf(pdf_path: Path, signature_image_path: Path, output_path: Path,
                          field_id: str = "Signature4") -> Path:
    """
    يضيف صورة التوقيع على الحقل المحدد في الـ PDF.
    يستخدم pypdf لإضافة التوقيع كـ image annotation.
    """
    import io
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (
        RectangleObject, NameObject, DictionaryObject,
        ArrayObject, NumberObject, ByteStringObject
    )
    from PIL import Image as PILImage

    # نقرأ الـ PDF
    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    writer.append(reader)

    # نلاقي الـ rect للحقل
    sig_rect = None
    sig_page_num = 0
    for p_num, page in enumerate(reader.pages):
        if "/Annots" not in page:
            continue
        for annot in page["/Annots"]:
            obj = annot.get_object()
            if obj.get("/T") == field_id:
                sig_rect = obj.get("/Rect")
                sig_page_num = p_num
                break

    # لو مفيش حقل توقيع، نحط التوقيع في مكان ثابت (أسفل اليسار)
    if sig_rect is None:
        sig_rect = [40, 300, 193, 324]

    # نحول صورة التوقيع لـ PNG bytes
    img = PILImage.open(str(signature_image_path)).convert("RGBA")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    # نضيف الصورة على الصفحة
    page = writer.pages[sig_page_num]
    writer.add_annotation(
        page_number=sig_page_num,
        annotation=DictionaryObject({
            NameObject("/Type"):    NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Stamp"),
            NameObject("/Rect"):    ArrayObject([
                NumberObject(sig_rect[0]), NumberObject(sig_rect[1]),
                NumberObject(sig_rect[2]), NumberObject(sig_rect[3])
            ]),
            NameObject("/Contents"): "Signature",
        })
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


def merge_pdfs(pdf_paths: list[Path], output_path: Path) -> Path:
    """يدمج قائمة PDF في ملف واحد"""
    writer = PdfWriter()
    for p in pdf_paths:
        reader = PdfReader(str(p))
        writer.append(reader)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path
