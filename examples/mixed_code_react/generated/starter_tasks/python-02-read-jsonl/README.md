# Read indexed JSONL records

read_jsonl_line(path, index) must return the indexed non-empty JSON record. Blank lines do not count as records. Reject negative indexes and raise IndexError when the requested record is absent.
