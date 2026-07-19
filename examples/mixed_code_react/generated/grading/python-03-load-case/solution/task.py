def load_case(cases: list[dict], case_id: str) -> dict:
    for case in cases:
        if case.get("id") == case_id:
            return case
    raise KeyError(f"Case {case_id!r} is missing from the manifest")
