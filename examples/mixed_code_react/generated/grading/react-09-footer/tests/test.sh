#!/usr/bin/env bash
set +e
mkdir -p /logs/verifier
python3 /tests/grade_react.py   --workspace /workspace   --reference /tests/reference.png   --screenshot /logs/verifier/candidate.png
exit 0
