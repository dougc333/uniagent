def retry_delays(
    max_retries: int,
    base_seconds: int = 5,
    cap_seconds: int = 60,
) -> list[int]:
    if max_retries < 1:
        raise ValueError("max_retries must be at least 1")
    if base_seconds <= 0 or cap_seconds <= 0:
        raise ValueError("base_seconds and cap_seconds must be positive")
    return [
        min(cap_seconds, base_seconds * (2**attempt_index))
        for attempt_index in range(max_retries - 1)
    ]
