"""
Entry point — Train churn prediction model end-to-end.

Usage
-----
    python train.py

What it does
------------
1. Load raw training data from data/train.csv
2. Apply feature engineering (leakage-free: scaler fitted on train only)
3. Cross-validate 4 candidate algorithms on the training set (StratifiedKFold k=5)
4. Train final Gradient Boosting model on full training set
5. Evaluate on hold-out test set (20%)
6. Save model + scaler artifact to models/
7. Persist CV and test metrics to notebooks/results/
"""

import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier

from src.config import RAW_TRAIN_PATH, SEED
from src.data.load import load_raw_data
from src.models.evaluate import compute_test_metrics, save_cv_results, save_test_results
from src.models.train import (
    cross_val_evaluate,
    load_artifacts,
    prepare_splits,
    save_artifacts,
    train_model,
)

# ---------------------------------------------------------------------------
# Experiment configuration
# ---------------------------------------------------------------------------
CICLO      = "ciclo0"
MODEL_NAME = "Gradient Boosting"

ALGORITHMS = {
    "Logistic Regression": LogisticRegression(random_state=SEED, max_iter=100),
    "Decision Tree":       DecisionTreeClassifier(random_state=SEED),
    "Random Forest":       RandomForestClassifier(random_state=SEED, n_jobs=-1),
    "Gradient Boosting":   GradientBoostingClassifier(random_state=SEED),
}


def main() -> None:
    # ------------------------------------------------------------------
    # 1. Load raw data
    # ------------------------------------------------------------------
    print("=" * 60)
    print("Churn Prediction — Training Pipeline")
    print("=" * 60)
    print(f"\n[1/5] Loading data from {RAW_TRAIN_PATH} ...")
    df_raw = load_raw_data(RAW_TRAIN_PATH)
    print(f"      Shape: {df_raw.shape}")

    # ------------------------------------------------------------------
    # 2. Feature engineering + train/test split (no leakage)
    # ------------------------------------------------------------------
    print("\n[2/5] Preparing splits (FE + stratified 80/20) ...")
    X_train, X_test, y_train, y_test, scaler = prepare_splits(df_raw)
    print(f"      X_train: {X_train.shape} | X_test: {X_test.shape}")
    print(f"      Train churn rate : {y_train.mean():.2%}")
    print(f"      Test  churn rate : {y_test.mean():.2%}")

    # ------------------------------------------------------------------
    # 3. Cross-validation baseline (all algorithms)
    # ------------------------------------------------------------------
    print(f"\n[3/5] Cross-validation (StratifiedKFold k=5) ...")
    rows = []
    for name, model in ALGORITHMS.items():
        print(f"      Evaluating {name} ...")
        metrics = cross_val_evaluate(model, X_train, y_train, cv=5)
        rows.append({"Model": name, **metrics})

    results_df = (
        pd.DataFrame(rows)
        .sort_values("F1", ascending=False)
        .reset_index(drop=True)
    )

    print("\n      === Cross-Validation Results (sorted by F1) ===")
    display_cols = ["Model", "Precision", "Recall", "F1", "ROC_AUC"]
    print(results_df[display_cols].to_string(index=False, float_format="{:.4f}".format))

    cv_path = save_cv_results(results_df, ciclo=CICLO)
    print(f"\n      CV results saved → {cv_path}")

    # ------------------------------------------------------------------
    # 4. Train final model + save artifact
    # ------------------------------------------------------------------
    print(f"\n[4/5] Training final model ({MODEL_NAME}) on full training set ...")
    model        = train_model(X_train, y_train)
    artifact_path = save_artifacts(model, scaler)
    print(f"      Artifact saved → {artifact_path}")

    # ------------------------------------------------------------------
    # 5. Evaluate on hold-out test set
    # ------------------------------------------------------------------
    print("\n[5/5] Evaluating on hold-out test set ...")
    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    metrics = compute_test_metrics(y_test, y_pred, y_proba)

    print("\n      === Test Set Results ===")
    for name, value in metrics.items():
        print(f"      {name:<20}: {value:.4f}")

    test_path = save_test_results(metrics, model_name=MODEL_NAME, ciclo=CICLO)
    print(f"\n      Test results saved → {test_path}")

    print("\n" + "=" * 60)
    print("Training complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
