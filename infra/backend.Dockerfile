FROM python:3.11.11-slim AS runtime

ARG UV_VERSION=0.5.11

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/workspace/backend/.venv/bin:${PATH}"

RUN pip install --no-cache-dir "uv==${UV_VERSION}"

WORKDIR /workspace/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/ ./
COPY contracts/ /workspace/contracts/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
