FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts ./scripts
COPY ground_truth ./ground_truth
COPY frontend/public/data ./frontend/public/data

RUN adduser --disabled-password --gecos "" susbiome \
    && mkdir -p /app/data /app/models \
    && chown -R susbiome:susbiome /app

USER susbiome

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" || exit 1

CMD ["python", "-m", "scripts.api.server"]
