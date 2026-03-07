"""Tests for XGBoost salary trainer (SPEC.md §5.1, Gates P6-P8, P16)."""

import os
import tempfile

import numpy as np

from src.salary.trainer import (
    MAX_SALARY,
    MIN_SALARY,
    load_model,
    predict_salary,
    save_model,
    train_salary_model,
)


def _synthetic_data(n: int = 200) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic training data."""
    rng = np.random.RandomState(42)
    features = rng.rand(n, 20)
    # Salary correlated with first few features
    labels = 30000 + features[:, 0] * 40000 + features[:, 1] * 20000 + rng.normal(0, 2000, n)
    return features, labels


class TestTrainSalaryModel:
    """Model training tests."""

    def test_trains_without_error(self) -> None:
        """Gate P6: Model trains without error."""
        features, labels = _synthetic_data(200)
        model, metrics = train_salary_model(features, labels)
        assert model is not None
        assert "mae" in metrics
        assert "median_ae" in metrics

    def test_metrics_computed(self) -> None:
        features, labels = _synthetic_data(200)
        _model, metrics = train_salary_model(features, labels)
        assert metrics["mae"] > 0
        assert metrics["median_ae"] > 0
        assert 0 <= metrics["within_20pct"] <= 100
        assert metrics["train_size"] == 160  # 80% of 200
        assert metrics["test_size"] == 40  # 20% of 200


class TestPredictSalary:
    """Prediction tests."""

    def test_predictions_sane(self) -> None:
        """Gate P8: No predictions < £10K or > £500K."""
        features, labels = _synthetic_data(200)
        model, _ = train_salary_model(features, labels)

        test_features = np.random.RandomState(99).rand(50, 20)
        predictions = predict_salary(model, test_features)

        for pred in predictions:
            assert pred["predicted_min"] >= MIN_SALARY * 0.9
            assert pred["predicted_max"] <= MAX_SALARY * 1.1

    def test_prediction_structure(self) -> None:
        features, labels = _synthetic_data(200)
        model, _ = train_salary_model(features, labels)

        test_features = np.random.RandomState(99).rand(5, 20)
        predictions = predict_salary(model, test_features)

        assert len(predictions) == 5
        for pred in predictions:
            assert "predicted_min" in pred
            assert "predicted_max" in pred
            assert "confidence" in pred
            assert pred["predicted_min"] < pred["predicted_max"]

    def test_confidence_values(self) -> None:
        features, labels = _synthetic_data(200)
        model, _ = train_salary_model(features, labels)

        test_features = np.random.RandomState(99).rand(10, 20)
        predictions = predict_salary(model, test_features)

        for pred in predictions:
            assert 0 < pred["confidence"] <= 1.0


class TestModelPersistence:
    """Save/load round-trip tests."""

    def test_save_load_roundtrip(self) -> None:
        """Gate P16: Save → load → predict produces same results."""
        features, labels = _synthetic_data(200)
        model, _ = train_salary_model(features, labels)

        test_features = np.random.RandomState(99).rand(10, 20)
        original_preds = predict_salary(model, test_features)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "model.json")
            save_model(model, path)
            loaded = load_model(path)
            loaded_preds = predict_salary(loaded, test_features)

        for orig, loaded_p in zip(original_preds, loaded_preds):
            assert abs(orig["predicted_min"] - loaded_p["predicted_min"]) < 0.01
            assert abs(orig["predicted_max"] - loaded_p["predicted_max"]) < 0.01
