FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kallang_cloud_bot.py .

CMD ["python", "kallang_cloud_bot.py"]

FROM ghcr.io/browserless/chrome:latest

RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kallang_cloud_bot.py .

CMD ["python3.11", "kallang_cloud_bot.py"]
