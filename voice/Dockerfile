FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project
COPY pankh_voice pankh_voice
ENV PATH="/app/.venv/bin:$PATH"
# Fetch model files (voice activity detection) at build time, not on the first call.
RUN python -m pankh_voice.agent download-files
CMD ["python", "-m", "pankh_voice.agent", "start"]
