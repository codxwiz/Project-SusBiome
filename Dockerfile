FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libexpat1 \
    libexpat1-dev \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    proj-bin \
    proj-data \
    libgeos-dev \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "scripts.api.server"]