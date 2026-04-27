"""
employees.py — تحميل وبحث بيانات الموظفين من Excel
"""
import openpyxl
from pathlib import Path

EXCEL_PATH = Path(__file__).parent / "data" / "EMP_List.xlsx"

def load_employees() -> dict:
    """بيحمل الـ Excel ويرجع dict مفتاحه الرقم الوظيفي (lower case)"""
    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    ws = wb.active

    headers = []
    employees = {}

    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            headers = [str(h).strip() if h else "" for h in row]
            continue
        if not row[0]:
            continue
        emp = dict(zip(headers, row))
        key = str(emp.get("Employee Code", "")).strip().lower()
        if key:
            employees[key] = emp

    wb.close()
    return employees


def find_employee(identifier: str, employees: dict) -> dict | None:
    """
    بيدور على الموظف بالرقم الوظيفي أو الـ National Code (رقم الإقامة).
    بيرجع بيانات الموظف أو None لو مش موجود.
    """
    identifier = identifier.strip().lower()

    # بحث بالرقم الوظيفي
    if identifier in employees:
        return employees[identifier]

    # بحث بالـ National Code (رقم الإقامة)
    for emp in employees.values():
        national = str(emp.get("National Code", "") or "").strip()
        if national and national == identifier:
            return emp

    return None


def is_labor(emp: dict) -> bool:
    """بيتحقق إن الموظف Labor مش Staff"""
    classification = str(emp.get("Employee Classification", "")).strip().lower()
    return classification == "labor"


def get_display_name(emp: dict) -> str:
    return str(emp.get("Employee Name Eng", "")).strip()


def get_company_region(emp: dict) -> str:
    bu = str(emp.get("Business Unit", "") or "").strip()
    region = str(emp.get("Region E", "") or "").strip()
    return f"{bu} - {region}" if bu and region else bu or region


if __name__ == "__main__":
    emps = load_employees()
    print(f"✅ تم تحميل {len(emps)} موظف")
    # تجربة
    emp = find_employee("KCG00139", emps)
    if emp:
        print(f"الموظف: {get_display_name(emp)} | Labor: {is_labor(emp)}")
