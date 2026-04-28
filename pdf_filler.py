"""
pdf_filler.py — ملء فورم الإجازة وفورم الإقرار تلقائياً + إضافة التوقيع
"""
from pathlib import Path
from datetime import date

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, ArrayObject, DictionaryObject, NumberObject

FORMS_DIR  = Path(__file__).parent / "Forms"
LEAVE_FORM = FORMS_DIR / "Leave_form_fillable.pdf"
DECL_FORM  = FORMS_DIR / "Declaration_Form_.pdf"

LEAVE_TYPE_MAP = {
    "annual": "/Choice1",
    "unpaid": "/Choice2",
    "sick":   "/Choice3",
}

DESTINATION_MAP = {
    "inside":  "/Choice1",
    "outside": "/Choice2",
}


def _set_text_field(writer: PdfWriter, field_id: str, value: str):
    for page in writer.pages:
        if "/Annots" not in page:
            continue
        for annot in page["/Annots"]:
            obj = annot.get_object()
            if obj.get("/T") == field_id:
                obj.update({NameObject("/V"): str(value)})


def _set_radio(writer: PdfWriter, field_id: str, value: str):
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


def _save(writer: PdfWriter, output_path: Path):
    """حفظ الـ PDF بالطريقة الصحيحة"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer.write(str(output_path))


def fill_leave_form(emp: dict, leave_data: dict, output_path: Path) -> Path:
    from employees import get_company_region

    reader = PdfReader(str(LEAVE_FORM))
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)

    _set_text_field(writer, "Emp name",         str(emp.get("Employee Name Eng", "")))
    _set_text_field(writer, "emp position",     str(emp.get("Postition E", "")))
    _set_text_field(writer, "ID Number",        str(emp.get("Employee Code", "")))
    _set_text_field(writer, "emp nationality",  str(emp.get("Nationality E", "")))
    _set_text_field(writer, "company & Region", get_company_region(emp))
    _set_text_field(writer, "Contact Numbers",  str(emp.get("Mobile", "")))

    leave_type_val = LEAVE_TYPE_MAP.get(leave_data.get("leave_type", "annual"), "/Choice1")
    _set_radio(writer, "Group1", leave_type_val)

    _set_text_field(writer, "leave start date",  leave_data.get("start_date", ""))
    _set_text_field(writer, "leave return date", leave_data.get("return_date", ""))
    _set_text_field(writer, "Duration",          str(leave_data.get("duration", "")))

    dest = leave_data.get("destination", "inside")
    _set_radio(writer, "Group2", DESTINATION_MAP.get(dest, "/Choice1"))

    if dest == "outside":
        city_from = leave_data.get("city_from", "")
        country_to = leave_data.get("country_to", "")
        _set_text_field(writer, "Specify", f"{city_from} → {country_to}" if city_from else country_to)

    _set_radio(writer, "Group3", "/1")
    _set_radio(writer, "Group4", "/Choice2")

    _save(writer, output_path)
    return output_path


def fill_declaration_form(emp: dict, leave_data: dict, output_path: Path) -> Path:
    emp_name = str(emp.get("Employee Name Eng", "")).strip()
    emp_id   = str(emp.get("Employee Code", "")).strip()
    today    = date.today().strftime("%d/%m/%Y")

    reader = PdfReader(str(DECL_FORM))
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)

    _set_text_field(writer, "No",          emp_name)
    _set_text_field(writer, "Text2",       emp_name)
    _set_text_field(writer, "Text1",       emp_id)
    _set_text_field(writer, "Text3",       emp_id)
    _set_text_field(writer, "undefined",   emp_name)
    _set_text_field(writer, "undefined_3", emp_name)
    _set_text_field(writer, "undefined_4", today)

    _save(writer, output_path)
    return output_path


def add_signature_to_pdf(pdf_path: Path, signature_image_path: Path, output_path: Path,
                          field_id: str = "Signature4") -> Path:
    import io
    from PIL import Image as PILImage

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    writer.append(reader)

    sig_rect     = None
    sig_page_num = 0
    for p_num, page in enumerate(reader.pages):
        if "/Annots" not in page:
            continue
        for annot in page["/Annots"]:
            obj = annot.get_object()
            if obj.get("/T") == field_id:
                sig_rect     = obj.get("/Rect")
                sig_page_num = p_num
                break

    if sig_rect is None:
        sig_rect = [40, 300, 193, 324]

    img = PILImage.open(str(signature_image_path)).convert("RGBA")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    writer.add_annotation(
        page_number=sig_page_num,
        annotation=DictionaryObject({
            NameObject("/Type"):     NameObject("/Annot"),
            NameObject("/Subtype"):  NameObject("/Stamp"),
            NameObject("/Rect"):     ArrayObject([
                NumberObject(sig_rect[0]), NumberObject(sig_rect[1]),
                NumberObject(sig_rect[2]), NumberObject(sig_rect[3])
            ]),
            NameObject("/Contents"): "Signature",
        })
    )

    _save(writer, output_path)
    return output_path


def merge_pdfs(pdf_paths: list[Path], output_path: Path) -> Path:
    writer = PdfWriter()
    for p in pdf_paths:
        writer.append(PdfReader(str(p)))
    _save(writer, output_path)
    return output_path
