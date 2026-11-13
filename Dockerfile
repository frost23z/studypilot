FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH=/app/src PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .

CMD ["sh", "-c", "if [ \"$APP\" = web ]; then exec streamlit run src/frontend/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false; else exec uvicorn api.main:app --host 0.0.0.0 --port $PORT; fi"]
