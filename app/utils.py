import re

EMP_RE = re.compile(r"^(?P<company_id>\d+)s(?P<user_id>\d+)$")

def parse_employee_no(employee_no: str) -> tuple[int, int] | None:
    m = EMP_RE.match(employee_no or "")
    if not m:
        return None
    return int(m.group("company_id")), int(m.group("user_id"))
