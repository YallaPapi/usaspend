# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default envs inside container
ENV DB_PATH=/data/app.db \
    USASPENDING_PAGE_SIZE=100 \
    USASPENDING_MAX_PAGES=10 \
    USASPENDING_PAGE_SLEEP=0.3

EXPOSE 8000

CMD ["uvicorn", "src.web:app", "--host", "0.0.0.0", "--port", "8000"]

