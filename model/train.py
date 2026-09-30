"""Обучение XGBoost с учётом дисбаланса + SHAP explainability."""
import os, json
import numpy as np
import pandas as pd
import xgboost as xgb
import mlflow, mlflow.xgboost
import shap
from sklearn.model_selection import train_test_split
from sklearn.metrics import (roc_auc_score, average_precision_score, precision_recall_curve)

def make_dataset(n=200_000):
    rng = np.random.default_rng(42)
    is_fraud = rng.random(n) < 0.01
    df = pd.DataFrame({
        "amount": np.where(is_fraud, rng.uniform(5000, 50000, n), rng.uniform(5, 500, n)),
        "ip_risk": np.where(is_fraud, rng.uniform(0.5, 1.0, n), rng.uniform(0, 0.3, n)),
        "merchant_cat": rng.integers(0, 5, n),
        "device": rng.integers(0, 4, n),
        "country": rng.integers(0, 7, n),
        "hour": rng.integers(0, 24, n),
        "is_fraud": is_fraud.astype(int),
    })
    return df

def main():
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
    mlflow.set_experiment("fraudhunter")

    df = make_dataset()
    X = df.drop(columns=["is_fraud"]); y = df["is_fraud"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, stratify=y, test_size=0.2, random_state=42)

    spw = (ytr == 0).sum() / max((ytr == 1).sum(), 1)

    with mlflow.start_run(run_name="xgb_baseline") as run:
        model = xgb.XGBClassifier(
            n_estimators=500, max_depth=6, learning_rate=0.05,
            scale_pos_weight=spw, eval_metric="aucpr",
            tree_method="hist", n_jobs=-1,
        )
        model.fit(Xtr, ytr)

        proba = model.predict_proba(Xte)[:, 1]
        auc = roc_auc_score(yte, proba)
        ap = average_precision_score(yte, proba)

        # подбираем порог по F1
        prec, rec, thr = precision_recall_curve(yte, proba)
        f1 = 2 * prec * rec / (prec + rec + 1e-9)
        best_thr = float(thr[f1.argmax()]) if len(thr) else 0.5

        mlflow.log_params({"n_estimators": 500, "max_depth": 6, "scale_pos_weight": float(spw)})
        mlflow.log_metrics({"roc_auc": auc, "avg_precision": ap, "best_threshold": best_thr})
        mlflow.xgboost.log_model(model, "model", registered_model_name="fraud-xgb")

        # SHAP explainer
        explainer = shap.TreeExplainer(model)
        sample = Xte.sample(200, random_state=0)
        sv = explainer.shap_values(sample)
        import matplotlib.pyplot as plt
        shap.summary_plot(sv, sample, show=False)
        plt.savefig("/tmp/shap_summary.png", bbox_inches="tight")
        mlflow.log_artifact("/tmp/shap_summary.png")

        print(f"✅ AUC={auc:.4f} AP={ap:.4f} thr={best_thr:.3f}")

if __name__ == "__main__":
    main()
