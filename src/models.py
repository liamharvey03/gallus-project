"""
FlexPoint Loan Funding Forecasting — ML Model Training & Selection

Trains multiple models on snapshot-based training data, evaluates on a
temporal hold-out (2024 train → 2025 test), and selects the best-calibrated
model for dollar-volume projection.

Primary metric: Brier score (calibration matters most when summing P × Amount).
"""
import sys
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import brier_score_loss, roc_auc_score, log_loss
from sklearn.calibration import calibration_curve

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

# Try LightGBM — fall back gracefully if not installed
try:
    import lightgbm as lgb
    HAS_LGBM = True
except ImportError:
    HAS_LGBM = False


# ─── Temporal train / test split ─────────────────────────────────────────────

def temporal_train_test_split(training_df, feature_columns):
    """
    Split by year: 2024 for training, 2025 for testing.

    Returns X_train, y_train, X_test, y_test (all numpy arrays).
    """
    train_mask = training_df["snapshot_year"] == 2024
    test_mask = training_df["snapshot_year"] == 2025

    X_train = training_df.loc[train_mask, feature_columns].values.astype(np.float32)
    y_train = training_df.loc[train_mask, "fund_by_end"].values.astype(int)
    X_test = training_df.loc[test_mask, feature_columns].values.astype(np.float32)
    y_test = training_df.loc[test_mask, "fund_by_end"].values.astype(int)

    return X_train, y_train, X_test, y_test


# ─── Model training ─────────────────────────────────────────────────────────

def train_models(X_train, y_train, feature_columns):
    """
    Train candidate models and return a dict of {name: fitted_model}.

    Logistic regression gets a StandardScaler wrapper (stored as attribute).
    """
    models = {}

    # 1. Logistic Regression (needs scaling)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)
    lr = LogisticRegression(C=1.0, max_iter=1000, solver="lbfgs")
    lr.fit(X_scaled, y_train)
    lr._scaler = scaler  # attach for scoring
    models["LogisticRegression"] = lr

    # 2. Gradient Boosting
    gb = GradientBoostingClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        min_samples_leaf=20,
        subsample=0.8,
        random_state=42,
    )
    gb.fit(X_train, y_train)
    models["GradientBoosting"] = gb

    # 3. LightGBM
    if HAS_LGBM:
        lgbm = lgb.LGBMClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            min_child_samples=20,
            subsample=0.8,
            random_state=42,
            verbose=-1,
        )
        lgbm.fit(X_train, y_train)
        models["LightGBM"] = lgbm

    # 4. Random Forest
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        min_samples_leaf=20,
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    models["RandomForest"] = rf

    return models


def _predict_proba(model, X):
    """Get P(fund) from a model, handling LR's scaler."""
    if hasattr(model, "_scaler"):
        X = model._scaler.transform(X)
    return model.predict_proba(X)[:, 1]


# ─── Model evaluation ───────────────────────────────────────────────────────

def evaluate_models(models, X_test, y_test):
    """
    Evaluate all models on the test set.

    Returns a DataFrame with Brier, AUC, and LogLoss for each model,
    sorted by Brier score (lower is better).
    """
    rows = []
    for name, model in models.items():
        probs = _predict_proba(model, X_test)
        rows.append({
            "model": name,
            "brier_score": brier_score_loss(y_test, probs),
            "auc": roc_auc_score(y_test, probs),
            "log_loss": log_loss(y_test, probs),
        })

    results = pd.DataFrame(rows).sort_values("brier_score")
    return results


def feature_importance(model, feature_columns):
    """
    Extract feature importance from a tree-based model.

    Returns a DataFrame sorted by importance (descending).
    """
    if hasattr(model, "feature_importances_"):
        imp = model.feature_importances_
    else:
        return pd.DataFrame(columns=["feature", "importance"])

    fi = pd.DataFrame({
        "feature": feature_columns,
        "importance": imp,
    }).sort_values("importance", ascending=False)

    return fi


def calibration_plot(models, X_test, y_test, save_path=None):
    """
    Plot calibration curves for all models and save to disk.
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot([0, 1], [0, 1], "k--", label="Perfect calibration")

    for name, model in models.items():
        probs = _predict_proba(model, X_test)
        fraction_pos, mean_predicted = calibration_curve(
            y_test, probs, n_bins=10, strategy="uniform"
        )
        brier = brier_score_loss(y_test, probs)
        ax.plot(mean_predicted, fraction_pos,
                "s-", label=f"{name} (Brier={brier:.4f})")

    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives")
    ax.set_title("Calibration Curves — P(fund by month end)")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150)
        print(f"  Saved calibration plot → {save_path}")
    plt.close(fig)


# ─── Orchestrator ────────────────────────────────────────────────────────────

def train_and_select(training_df, feature_columns):
    """
    End-to-end: split → train → evaluate → select best model.

    Returns dict with keys:
        best_model_name, best_model, models, results,
        feature_columns, X_train, y_train, X_test, y_test
    """
    print("\n  Splitting: 2024 train / 2025 test...")
    X_train, y_train, X_test, y_test = temporal_train_test_split(
        training_df, feature_columns
    )
    print(f"    Train: {len(X_train):,} rows  pos rate {y_train.mean():.1%}")
    print(f"    Test:  {len(X_test):,} rows  pos rate {y_test.mean():.1%}")

    print("\n  Training models...")
    models = train_models(X_train, y_train, feature_columns)
    print(f"    Trained: {', '.join(models.keys())}")

    print("\n  Evaluating...")
    results = evaluate_models(models, X_test, y_test)

    best_name = results.iloc[0]["model"]
    best_model = models[best_name]

    return {
        "best_model_name": best_name,
        "best_model": best_model,
        "models": models,
        "results": results,
        "feature_columns": feature_columns,
        "X_train": X_train,
        "y_train": y_train,
        "X_test": X_test,
        "y_test": y_test,
    }


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from data_prep import load_and_clean
    from transition_tables import build_transition_tables
    from feature_engineering import (
        build_training_set, encode_categoricals, fill_missing_numeric,
        get_feature_columns, NUMERIC_FEATURES, CATEGORICAL_FEATURES,
        META_COLUMNS,
    )

    df = load_and_clean()

    print("\nBuilding transition tables...")
    tables = build_transition_tables(df)

    print("Building training set...")
    training = build_training_set(df, tables)
    print(f"  Raw training shape: {training.shape}")

    # Encode and impute
    encoded, encoders = encode_categoricals(training, fit=True)
    encoded, medians = fill_missing_numeric(encoded, fit=True)
    feature_cols = get_feature_columns(encoders)
    print(f"  Feature columns: {len(feature_cols)}")

    # Train and select
    print(f"\n{'═' * 65}")
    print("MODEL TRAINING & COMPARISON")
    print(f"{'═' * 65}")

    bundle = train_and_select(encoded, feature_cols)
    results = bundle["results"]

    print(f"\n  {'Model':<25s} {'Brier':>8s} {'AUC':>8s} {'LogLoss':>8s}")
    print(f"  {'─' * 52}")
    for _, row in results.iterrows():
        marker = " ★" if row["model"] == bundle["best_model_name"] else ""
        print(f"  {row['model']:<25s} {row['brier_score']:>8.4f} "
              f"{row['auc']:>8.4f} {row['log_loss']:>8.4f}{marker}")
    print(f"\n  Selected: {bundle['best_model_name']} (lowest Brier score)")

    # Feature importance (best model)
    print(f"\n{'═' * 65}")
    print(f"FEATURE IMPORTANCE — {bundle['best_model_name']}")
    print(f"{'═' * 65}")
    fi = feature_importance(bundle["best_model"], feature_cols)
    for i, (_, row) in enumerate(fi.head(15).iterrows()):
        print(f"  {i+1:>2d}. {row['feature']:<30s} {row['importance']:.4f}")

    # Calibration plot
    save_path = config.OUTPUTS_PATH / "figures" / "calibration_curves.png"
    calibration_plot(bundle["models"], bundle["X_test"], bundle["y_test"],
                     save_path=save_path)

    # ── Quick projection sanity check on Sep 15 2025 test rows ─────────
    print(f"\n{'═' * 65}")
    print("SANITY CHECK — Sep 2025 test rows")
    print(f"{'═' * 65}")
    sep_mask = (encoded["snapshot_year"] == 2025) & (encoded["snapshot_month"] == 9)
    if sep_mask.any():
        sep_rows = encoded[sep_mask]
        X_sep = sep_rows[feature_cols].values.astype(np.float32)
        ml_probs = _predict_proba(bundle["best_model"], X_sep)
        base_probs = sep_rows["stage_only_probability"].values

        print(f"  Sep 2025 test rows: {len(sep_rows):,}")
        print(f"  Actual positive rate: {sep_rows['fund_by_end'].mean():.1%}")
        print(f"  ML mean P(fund):     {ml_probs.mean():.1%}")
        print(f"  Base prob mean:      {base_probs.mean():.1%}")
    else:
        print("  No Sep 2025 rows in test set.")
