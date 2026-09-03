FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/loris/.local/bin:$PATH"

RUN groupadd --gid 10001 loris \
    && useradd --uid 10001 --gid loris --create-home --shell /usr/sbin/nologin loris

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir . \
    && mkdir -p /app/data/documents \
    && chown -R loris:loris /app /home/loris
COPY --chown=loris:loris alembic.ini ./
COPY --chown=loris:loris alembic ./alembic

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; from app.core.config import get_settings; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/health', headers={'Host': get_settings().allowed_hosts[0]}), timeout=4)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
