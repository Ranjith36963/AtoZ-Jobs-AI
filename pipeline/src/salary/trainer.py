"""XGBoost salary prediction model (SPEC.md §5.1).

Trains, predicts, saves, and loads salary prediction models.
"""

import numpy as np
import structlog
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, median_absolute_error
from sklearn.model_selection import train_test_split

logger = structlog.get_logger()

# Sanity bounds for salary predictions
MIN_SALARY = 10_000
MAX_SALARY = 500_000


def train_salary_model(
    features: np.ndarray,
    labels: np.ndarray,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[xgb.Booster, dict[str, float]]:
    """Train XGBoost salary predictor.

    Args:
        features: Feature matrix from build_features().
        labels: Salary labels (salary_annual_max).
        test_size: Fraction for test split.
        random_state: Random seed for reproducibility.

    Returns:
        Tuple of (trained model, metrics dict with mae, median_ae, within_20pct).
    """
    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=test_size, random_state=random_state
    )

    dtrain = xgb.DMatrix(x_train, label=y_train)
    dtest = xgb.DMatrix(x_test, label=y_test)

    params = {
        "objective": "reg:squarederror",
        "max_depth": 6,
        "learning_rate": 0.1,
        "eval_metric": "mae",
    }

    model = xgb.train(
        params,
        dtrain,
        num_boost_round=200,
        evals=[(dtest, "test")],
        early_stopping_rounds=20,
        verbose_eval=0,
    )

    # Validate
    preds = model.predict(dtest)
    mae = float(mean_absolute_error(y_test, preds))
    median_ae = float(median_absolute_error(y_test, preds))

    # Percentage within 20% of actual
    within_20pct = float(np.mean(np.abs(preds - y_test) / y_test < 0.2) * 100)

    metrics = {
        "mae": mae,
        "median_ae": median_ae,
        "within_20pct": within_20pct,
        "train_size": len(y_train),
        "test_size": len(y_test),
    }

    logger.info("salary_model.trained", **metrics)
    return model, metrics


def predict_salary(
    model: xgb.Booster,
    features: np.ndarray,
) -> list[dict[str, float | str]]:
    """Predict salaries for jobs.

    Args:
        model: Trained XGBoost model.
        features: Feature matrix.

    Returns:
        List of dicts with predicted_min, predicted_max, confidence.
    """
    dmatrix = xgb.DMatrix(features)
    predictions = model.predict(dmatrix)

    results = []
    for pred in predictions:
        pred_val = float(pred)

        # Clamp to sanity bounds
        pred_val = max(MIN_SALARY, min(MAX_SALARY, pred_val))

        # predicted_min/max: ±10% band
        predicted_min = round(pred_val * 0.9, 2)
        predicted_max = round(pred_val * 1.1, 2)

        # Confidence based on prediction value relative to bounds
        # Higher predictions in the middle range → higher confidence
        if MIN_SALARY * 1.5 <= pred_val <= MAX_SALARY * 0.7:
            confidence = 0.85  # HIGH
        elif MIN_SALARY * 1.2 <= pred_val <= MAX_SALARY * 0.9:
            confidence = 0.65  # MEDIUM
        else:
            confidence = 0.4  # LOW

        results.append(
            {
                "predicted_min": predicted_min,
                "predicted_max": predicted_max,
                "confidence": confidence,
            }
        )

    return results  # type: ignore[return-value]


def save_model(model: xgb.Booster, path: str) -> None:
    """Save trained model to file."""
    model.save_model(path)
    logger.info("salary_model.saved", path=path)


def load_model(path: str) -> xgb.Booster:
    """Load trained model from file."""
    model = xgb.Booster()
    model.load_model(path)
    logger.info("salary_model.loaded", path=path)
    return model
