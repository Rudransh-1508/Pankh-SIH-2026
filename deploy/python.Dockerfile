# One image for the API, the Temporal worker and the simulators; each runs a different command.
FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/
# psutil (pinned by OpenFisca) has no prebuilt wheel for Linux on ARM, so it is compiled here.
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY rules rules
COPY backend backend
COPY simulators simulators
RUN uv sync --locked --all-packages --no-dev

FROM python:3.13-slim
WORKDIR /app
COPY --from=build /app /app
COPY deploy/start-api.sh deploy/start-simulators.sh /app/
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app/backend
