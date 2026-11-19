FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 PATH=/app/.venv/bin:$PATH

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

COPY . .
RUN uv sync --locked

CMD ["trips", "run", "data/trips.csv"]
