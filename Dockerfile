# Dockerfile
FROM python:3.10

WORKDIR /app

COPY .env .env

COPY app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]