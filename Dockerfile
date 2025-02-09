FROM python:3.9-slim
LABEL authors="sevak"

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY main.py .
COPY config.yaml .
COPY templates/ ./templates/

EXPOSE 8000

CMD ["gunicorn", "--chdir", "/app", "main:app", "-b", "0.0.0.0:8000", "--timeout", "60", "--capture-output", "--access-logfile", "-", "--error-logfile", "-"]