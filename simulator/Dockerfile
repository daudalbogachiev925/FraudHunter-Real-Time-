FROM python:3.11-slim
RUN pip install --no-cache-dir kafka-python==2.0.2 faker==25.2.0 numpy==1.26.4
WORKDIR /app
COPY . .
CMD ["python", "gen.py"]
