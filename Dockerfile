FROM python:3.11-slim

WORKDIR /app

COPY weather_agent/ /app/weather_agent/
COPY main.py .
COPY requirements.txt .
RUN pip install -r requirements.txt

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]