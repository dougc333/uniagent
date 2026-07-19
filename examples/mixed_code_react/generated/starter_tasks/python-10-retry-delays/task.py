def retry_delays(max_retries: int, base_seconds: int = 5, cap_seconds: int = 60) -> list[int]:
    return [base_seconds] * max_retries
