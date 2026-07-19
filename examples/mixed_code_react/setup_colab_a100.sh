#!/usr/bin/env bash
# Install Uni-Agent/veRL and task dependencies directly in a Colab GPU runtime.
set -xeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
react_runtime=${REACT_RUNTIME:-/content/uniagent-react-runtime}

cd "${repo_root}"

nvidia-smi

python3 -m pip install --upgrade pip setuptools wheel
python3 -m pip install --no-cache-dir "vllm==0.11.0"
python3 -m pip install --no-cache-dir -r verl/requirements.txt
python3 -m pip install --no-deps -e ./verl
python3 -m pip install --no-cache-dir \
  swe-rex \
  loguru \
  pydantic \
  pydantic_settings \
  aiohttp \
  pexpect \
  pyyaml \
  "playwright==1.48.0" \
  "Pillow>=10.4,<12" \
  "numpy<2.0" \
  datasets

python3 -m playwright install --with-deps chromium

if ! command -v npm >/dev/null 2>&1; then
  apt-get update
  apt-get install -y nodejs npm
fi

npm install \
  --prefix "${react_runtime}" \
  --no-audit \
  --no-fund \
  react@19.1.0 \
  react-dom@19.1.0 \
  vite@7.0.6 \
  @vitejs/plugin-react@4.6.0

echo "Colab dependencies installed. Restart the Colab runtime before training."
