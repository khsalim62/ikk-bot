"""
pdf_filler.py — ملء فورم الإجازة وفورم الإقرار تلقائياً
"""
from pathlib import Path
from datetime import date
import pikepdf
from pikepdf import Pdf, Dictionary, Name, String, Array

FORMS_DIR  = Path(__file__).parent / "Forms"
LEAVE_FORM = FORMS_DIR / "Leave_form_fillable.pdf"
DECL_FORM  = FORMS_DIR / "Declaration_Form_.pdf"

LEAVE_TYPE_MAP = {
    "annual": "Choice1",
    "unpaid": "Choice2",
    "sick":   "Choice3",
}

DESTINATION_MAP = {
    "inside":  "Choice1",
    "outside": "Choice2",
}


def _fill_pdf(template_path: Path, fields: dict, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Pdf.open(str(template_path)) as pdf:
        if "/AcroForm" not in pdf.Root:
            pdf.save(str(output_path))
            return

        acroform = pdf.Root.AcroForm
        if "/Fields" not in acroform:
            pdf.save(str(output_path))
            return

        # ✅ NeedAppearances الصح في pikepdf
        acroform[Name("/NeedAppearances")] = pikepdf.objects.PdfObject.parse("true") if hasattr(pikepdf.objects.PdfObject, 'parse') else Name("/true")

        def process_field(field):
            if "/Kids" in field:
                for kid in field.Kids:
                    process_field(kid)
                return

            field_name = str(field.get("/T", "")).strip()
            if not field_name or field_name not in fields:
                return

            value = fields[field_name]
            field_type = str(field.get("/FT", "")).strip()

            if field_type == "/Tx":
                field[Name("/V")] = String(str(value))
                if "/AP" in field:
                    del field[Name("/AP")]

            elif field_type == "/Btn":
                choice = Name("/" + str(value))
                field[Name("/V")] = choice
                field[Name("/AS")] = choice

        for field_ref in acroform.Fields:
            process_field(field_ref)

        pdf.save(str(output_path))


def fill_leave_form(emp: dict, leave_data: dict, output_path: Path) -> Path:
    from employees import get_company_region

    dest = leave_data.get("destination", "inside")
    city_from  = leave_data.get("city_from", "")
    country_to = leave_data.get("country_to", "")

    fields = {
        "Emp name":         str(emp.get("Employee Name Eng", "")),
        "emp position":     str(emp.get("Postition E", "")),
        "ID Number":        str(emp.get("Employee Code", "")),
        "emp nationality":  str(emp.get("Nationality E", "")),
        "company & Region": get_company_region(emp),
        "Contact Numbers":  str(emp.get("Mobile", "")),
        "leave start date": leave_data.get("start_date", ""),
        "leave return date":leave_data.get("return_date", ""),
        "Duration":         str(leave_data.get("duration", "")),
        "Group1":           LEAVE_TYPE_MAP.get(leave_data.get("leave_type", "annual"), "Choice1"),
        "Group2":           DESTINATION_MAP.get(dest, "Choice1"),
        "Group3":           "1",
        "Group4":           "Choice2",
    }

    if dest == "outside":
        fields["Specify"] = f"{city_from} -> {country_to}" if city_from else country_to

    _fill_pdf(LEAVE_FORM, fields, output_path)
    return output_path


def fill_declaration_form(emp: dict, leave_data: dict, output_path: Path) -> Path:
    emp_name = str(emp.get("Employee Name Eng", "")).strip()
    emp_id   = str(emp.get("Employee Code", "")).strip()
    today    = date.today().strftime("%d/%m/%Y")

    fields = {
        "No":          emp_name,
        "Text2":       emp_name,
        "Text1":       emp_id,
        "Text3":       emp_id,
        "undefined":   emp_name,
        "undefined_3": emp_name,
        "undefined_4": today,
    }

    _fill_pdf(DECL_FORM, fields, output_path)
    return output_path


def add_signature_to_pdf(pdf_path: Path, signature_image_path: Path, output_path: Path,
                          field_id: str = "Signature4") -> Path:
    import shutil
    shutil.copy(str(pdf_path), str(output_path))
    return output_path


def merge_pdfs(pdf_paths: list[Path], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = Pdf.new()
    for p in pdf_paths:
        src = Pdf.open(str(p))
        pdf.pages.extend(src.pages)
    pdf.save(str(output_path))
    return output_path
