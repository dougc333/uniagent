# Calculate bounded retry delays

retry_delays(max_retries, base_seconds=5, cap_seconds=60) returns the delays used between attempts. There is no delay after the final attempt, so return max_retries-1 values. Use exponential backoff base_seconds * 2**attempt_index capped at cap_seconds. Reject max_retries < 1 and non-positive base/cap.
