FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    chromium-browser \
    chromium-common \
    fonts-liberation \
    libnss3 \
    libxss1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kallang_cloud_bot.py .

CMD ["python", "kallang_cloud_bot.py"]
