.PHONY: up down train promote stream api ui simulate test

up:
	docker compose up -d kafka zookeeper postgres minio mlflow redis

down:
	docker compose down -v

train:
	docker compose run --rm model python train.py

promote:
	docker compose run --rm model python -c "from mlflow.tracking import MlflowClient; \
c=MlflowClient('http://mlflow:5000'); vs=c.search_model_versions(\"name='fraud-xgb'\"); \
latest=max(vs, key=lambda v:int(v.version)); \
c.transition_model_version_stage('fraud-xgb', latest.version, 'Production', True); \
print(f'✅ v{latest.version} → Production')"

stream:
	docker compose up -d --build stream simulator

api:
	docker compose up -d --build api

ui:
	docker compose up -d --build ui

test:
	pytest -q tests/
