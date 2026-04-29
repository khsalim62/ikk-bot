"""
pdf_filler.py — ملء فورم الإجازة وفورم الإقرار تلقائياً + إضافة التوقيع
"""
from pathlib import Path
from datetime import date
import pikepdf
from pikepdf import Pdf, Name, String

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


def _set_radio_group(group_field, chosen_value: str):
    chosen = Name("/" + chosen_value)
    group_field[Name("/V")] = chosen
    if "/Kids" in group_field:
        for kid in group_field.Kids:
            ap_keys = []
            if "/AP" in kid:
                try:
                    ap_keys = [str(k) for k in kid["/AP"]["/N"].keys()]
                except:
                    pass
            if ("/" + chosen_value) in ap_keys:
                kid[Name("/AS")] = chosen
            else:
                kid[Name("/AS")] = Name("/Off")


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
        acroform[Name("/NeedAppearances")] = True
        for field_ref in acroform.Fields:
            field_name = str(field_ref.get("/T", "")).strip()
            if not field_name or field_name not in fields:
                continue
            value = fields[field_name]
            field_type = str(field_ref.get("/FT", "")).strip()
            if field_type == "/Tx":
                field_ref[Name("/V")] = String(str(value))
                if "/AP" in field_ref:
                    del field_ref[Name("/AP")]
            elif field_type == "/Btn" or "/Kids" in field_ref:
                _set_radio_group(field_ref, str(value))
        pdf.save(str(output_path))


def _add_image_to_pdf(pdf_path: Path, image_path: Path, output_path: Path,
                       x: float, y: float, width: float, height: float, page_num: int = 0):
    from PIL import Image
    import io

    img_orig = Image.open(str(image_path)).convert("RGBA")
    background = Image.new("RGBA", img_orig.size, (255, 255, 255, 255))
    background.paste(img_orig, mask=img_orig.split()[3])
    img = background.convert("RGB")

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=95)
    img_bytes.seek(0)
    img_data = img_bytes.read()

    with Pdf.open(str(pdf_path)) as pdf:
        page = pdf.pages[page_num]
        image_obj = pikepdf.Stream(pdf, img_data)
        image_obj.stream_dict = pikepdf.Dictionary(
            Type=Name("/XObject"),
            Subtype=Name("/Image"),
            Width=img.width,
            Height=img.height,
            ColorSpace=Name("/DeviceRGB"),
            BitsPerComponent=8,
            Filter=Name("/DCTDecode"),
        )
        if "/Resources" not in page:
            page[Name("/Resources")] = pikepdf.Dictionary()
        if "/XObject" not in page.Resources:
            page.Resources[Name("/XObject")] = pikepdf.Dictionary()
        page.Resources.XObject[Name("/Sig0")] = image_obj
        draw_cmd = f"q {width} 0 0 {height} {x} {y} cm /Sig0 Do Q\n"
        existing = b""
        if "/Contents" in page:
            contents = page.Contents
            if isinstance(contents, pikepdf.Stream):
                existing = contents.read_bytes()
            elif isinstance(contents, list):
                for c in contents:
                    existing += c.read_bytes()
        new_stream = pikepdf.Stream(pdf, existing + draw_cmd.encode())
        page[Name("/Contents")] = new_stream
        output_path.parent.mkdir(parents=True, exist_ok=True)
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
        "Contact Numbers":  str(leave_data.get("phone", emp.get("Mobile", ""))),
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
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Pdf.open(str(DECL_FORM)) as pdf:
        page = pdf.pages[0]

        # بيانات الموظف في مواضعها على الصفحة
        text_items = [
            (emp_name, 39.5,  623.4),
            (emp_id,   46.5,  609.5),
            (emp_name, 313.9, 622.9),
            (emp_id,   411.1, 609.5),
            (emp_name, 40.0,  334.1),
            (emp_name, 308.2, 334.1),
            (today,    308.2, 305.5),
        ]

        lines = []
        for text, x, y in text_items:
            t = text.replace("(", "\\(").replace(")", "\\)")
            lines.append("BT /TT1 8 Tf " + str(x) + " " + str(y) + " Td (" + t + ") Tj ET")

        text_bytes = ("\n".join(lines) + "\n").encode()
        text_stream = pikepdf.Stream(pdf, text_bytes)

        # نضيف كـ stream إضافي للـ contents array
        if "/Contents" in page:
            existing = page["/Contents"]
            if isinstance(existing, pikepdf.Array):
                existing.append(text_stream)
                page[Name("/Contents")] = existing
            else:
                page[Name("/Contents")] = pikepdf.Array([existing, text_stream])
        else:
            page[Name("/Contents")] = text_stream

        pdf.save(str(output_path),
                 compress_streams=False,
                 stream_decode_level=pikepdf.StreamDecodeLevel.all)

    return output_path


def add_signature_to_pdf(pdf_path: Path, signature_image_path: Path, output_path: Path,
                          field_id: str = "Signature4") -> Path:
    try:
        sig_x, sig_y, sig_w, sig_h = 120, 390, 120, 25
        page_num = 0

        with Pdf.open(str(pdf_path)) as pdf:
            for p_num, page in enumerate(pdf.pages):
                if "/Annots" not in page:
                    continue
                for annot in page.Annots:
                    obj = annot
                    t_val = str(obj.get("/T", "")).strip()
                    if t_val == field_id and "/Rect" in obj:
                        rect = obj["/Rect"]
                        sig_x = float(rect[0])
                        sig_y = float(rect[1])
                        sig_w = float(rect[2]) - float(rect[0])
                        sig_h = float(rect[3]) - float(rect[1])
                        page_num = p_num
                        break

        _add_image_to_pdf(
            pdf_path=pdf_path,
            image_path=signature_image_path,
            output_path=output_path,
            x=sig_x,
            y=sig_y,
            width=sig_w,
            height=sig_h,
            page_num=page_num
        )
    except Exception as e:
        print(f"Signature add error: {e}")
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
