FROM mcr.microsoft.com/playwright/python:v1.48.0-noble

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install \
        "numpy>=2.0,<3" \
        "Pillow>=10.4,<12" \
        "playwright==1.48.0" \
        "swe-rex"

WORKDIR /opt/react-runtime
COPY react_runtime_package.json ./package.json
RUN npm install --no-audit --no-fund

COPY generated/starter_tasks /opt/tasks

WORKDIR /workspace
