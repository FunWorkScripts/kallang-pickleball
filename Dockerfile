FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kallang_cloud_bot.py .

CMD ["python", "kallang_cloud_bot.py"]
