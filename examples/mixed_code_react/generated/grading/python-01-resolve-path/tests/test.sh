#!/usr/bin/env bash
set +e
mkdir -p /logs/verifier
PYTHONPATH=/workspace python3 /tests/test_task.py
status=$?
if [ "$status" -eq 0 ]; then
  printf '{"reward": 1.0}\n' > /logs/verifier/reward.json
else
  printf '{"reward": 0.0}\n' > /logs/verifier/reward.json
fi
exit 0
