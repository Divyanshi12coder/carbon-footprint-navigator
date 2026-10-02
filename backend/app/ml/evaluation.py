"""Forecast evaluation metrics."""

import numpy as np


def mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - predicted)))


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def smape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Symmetric MAPE in percent; robust to zero days (0/0 counts as a perfect prediction)."""
    denom = np.abs(actual) + np.abs(predicted)
    ratio = np.where(denom == 0, 0.0, 2 * np.abs(actual - predicted) / np.where(denom == 0, 1, denom))
    return float(100 * np.mean(ratio))


def skill_score(model_mae: float, baseline_mae: float) -> float | None:
    """1 - MAE_model / MAE_baseline. >0 means the model beats the naive baseline."""
    if baseline_mae <= 0:
        return None
    return float(1 - model_mae / baseline_mae)
