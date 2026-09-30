FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir \
    kafka-python==2.0.2 xgboost==2.0.3 pandas==2.2.2 numpy==1.26.4 \
    mlflow==2.13.0 boto3==1.34.0 redis==5.0.4 psycopg[binary]==3.1.18 \
    prometheus-client==0.20.0
WORKDIR /app
COPY . .
CMD ["python", "consumer.py"]
