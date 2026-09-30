FROM python:3.11-slim
RUN pip install --no-cache-dir \
    fastapi==0.111.0 uvicorn[standard]==0.30.1 \
    kafka-python==2.0.2 redis==5.0.4 psycopg[binary]==3.1.18 \
    prometheus-client==0.20.0
WORKDIR /app
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
