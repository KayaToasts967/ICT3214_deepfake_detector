FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    MODEL_DIR=/app/models

WORKDIR /app
COPY requirements.lock.txt requirements-model.txt ./
RUN python -m pip install --no-cache-dir -r requirements.lock.txt \
    && python -m pip install --no-cache-dir -r requirements-model.txt \
    && useradd --uid 10001 --create-home appuser \
    && mkdir -p /app/.runtime /app/models \
    && chown -R appuser:appuser /app

COPY --chown=appuser:appuser backend ./backend
COPY --chown=appuser:appuser dist ./dist
COPY --chown=appuser:appuser plugins ./plugins
COPY --chown=appuser:appuser tests ./tests
COPY --chown=appuser:appuser scripts ./scripts
COPY --chown=appuser:appuser docs ./docs
COPY --chown=appuser:appuser models/README.md ./models/README.md
COPY --chown=appuser:appuser README.md TEAM_SETUP.md Dockerfile compose.yaml .dockerignore .gitignore .env.example requirements.txt setup.ps1 start.ps1 ./

USER appuser
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

# 0.0.0.0 is container-internal; Compose publishes it only on host loopback.
CMD ["python", "-m", "backend.run", "--container", "--port", "8000"]
