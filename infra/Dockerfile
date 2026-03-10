FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8080

WORKDIR /app/backend/app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
