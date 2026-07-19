def load_case(cases: list[dict], case_id: str) -> dict | None:
    for case in cases:
        if case.get("id") == case_id:
            return case
    return None
