FROM python:3.11-slim
RUN pip install --no-cache-dir \
    xgboost==2.0.3 scikit-learn==1.5.0 pandas==2.2.2 numpy==1.26.4 \
    shap==0.45.1 matplotlib==3.8.4 mlflow==2.13.0 boto3==1.34.0
WORKDIR /app
COPY . .
CMD ["python", "train.py"]
