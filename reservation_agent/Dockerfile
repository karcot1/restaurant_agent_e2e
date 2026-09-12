FROM python:3.11-slim

WORKDIR /app

COPY __init__.py .
COPY a2a_config.py .
COPY agent.py .
COPY executor.py .
COPY main.py .
COPY register_a2a_service.py .
COPY requirements.txt .

RUN pip install -r requirements.txt

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]