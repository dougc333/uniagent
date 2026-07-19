# Load non-empty benchmark entries

load_entries(path) must parse each non-empty UTF-8 JSONL line in order and return a list of dictionaries. Ignore whitespace-only lines, return [] for an empty file, and do not suppress JSON decoding errors.
