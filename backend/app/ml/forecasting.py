"""Daily emission forecasting with model selection by backtest.

Candidates
----------
* ``moving_average_28``   — flat mean of the last 28 days (naive baseline).
* ``seasonal_weekday_28`` — per-weekday mean over the last 4 weeks (captures weekly routines).
* ``ridge_trend_weekday`` — scikit-learn Ridge regression on [linear trend, day-of-week one-hot],
  sample-weighted towards recent days (half-life 60 days).

Procedure
---------
1. Build a zero-filled daily series from the user's first record to today (max 365 days).
2. Cap extreme one-off days at Q3 + 3*IQR so a single flight does not dominate the fit.
3. Hold out the last min(28, n/4) days, fit every candidate on the rest, score MAE on the holdout.
4. Refit the best candidate on all data and forecast the horizon.
5. Prediction intervals: empirical 10th/90th percentiles of holdout residuals (80% interval)
   per day; the horizon total interval comes from a 2,000-path residual bootstrap.

Cold start: fewer than 28 days of history or fewer than 10 active days returns
``insufficient_data`` instead of a forecast — we do not extrapolate from noise.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import numpy as np
from sklearn.linear_model import Ridge

from app.ml.evaluation import mae, rmse, skill_score, smape
from app.ml.feature_engineering import DailyFrame, calendar_features, clip_outliers, rolling_mean

MIN_HISTORY_DAYS = 28
MIN_ACTIVE_DAYS = 10
INTERVAL_LOW, INTERVAL_HIGH = 10, 90
BOOTSTRAP_PATHS = 2000
RECENCY_HALF_LIFE_DAYS = 60

Model = Callable[[list[date], np.ndarray, list[date]], np.ndarray]


def _moving_average(train_dates: list[date], y: np.ndarray, future: list[date]) -> np.ndarray:
    return np.full(len(future), float(np.mean(y[-28:])))


def _seasonal_weekday(train_dates: list[date], y: np.ndarray, future: list[date]) -> np.ndarray:
    recent_dates, recent = train_dates[-28:], y[-28:]
    overall = float(np.mean(recent))
    means = {}
    for dow in range(7):
        vals = [v for d, v in zip(recent_dates, recent, strict=True) if d.weekday() == dow]
        means[dow] = float(np.mean(vals)) if vals else overall
    return np.array([means[d.weekday()] for d in future])


def _ridge(train_dates: list[date], y: np.ndarray, future: list[date]) -> np.ndarray:
    t0 = train_dates[0]
    x = calendar_features(train_dates, t0)
    age = np.array([(train_dates[-1] - d).days for d in train_dates], dtype=float)
    weights = 0.5 ** (age / RECENCY_HALF_LIFE_DAYS)
    model = Ridge(alpha=1.0)
    model.fit(x, y, sample_weight=weights)
    pred = model.predict(calendar_features(future, t0))
    # Guard against a steep fitted trend running away over long horizons: never exceed 2x the
    # recent 28-day mean, never go below zero.
    ceiling = 2 * max(float(np.mean(y[-28:])), 1e-6)
    return np.clip(pred, 0, ceiling)


CANDIDATES: dict[str, Model] = {
    "moving_average_28": _moving_average,
    "seasonal_weekday_28": _seasonal_weekday,
    "ridge_trend_weekday": _ridge,
}


@dataclass
class ForecastResult:
    status: str  # "ok" | "insufficient_data"
    horizon_days: int
    model_name: str | None = None
    points: list[dict[str, Any]] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    predicted_total_kg: float | None = None
    lower_total_kg: float | None = None
    upper_total_kg: float | None = None
    recent_total_kg: float | None = None  # actual emissions over the previous `horizon` days
    metrics: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _history_points(frame: DailyFrame, days: int = 90) -> list[dict[str, Any]]:
    roll = rolling_mean(frame.total, 7)
    start = max(0, frame.n - days)
    return [
        {
            "date": frame.dates[i].isoformat(),
            "actual_kg": round(float(frame.total[i]), 3),
            "rolling_7d_kg": round(float(roll[i]), 3),
        }
        for i in range(start, frame.n)
    ]


def forecast(frame: DailyFrame, horizon_days: int, seed: int = 7) -> ForecastResult:
    result = ForecastResult(status="insufficient_data", horizon_days=horizon_days)
    result.history = _history_points(frame)
    if frame.n < MIN_HISTORY_DAYS or frame.active_days < MIN_ACTIVE_DAYS:
        result.notes.append(
            f"Forecasts need at least {MIN_HISTORY_DAYS} days of history with {MIN_ACTIVE_DAYS}+ days of logged "
            f"activity (you have {frame.n} days, {frame.active_days} active)."
        )
        return result

    y, n_clipped = clip_outliers(frame.total)
    if n_clipped:
        result.notes.append(f"{n_clipped} unusually high day(s) were capped for model fitting (e.g. one-off flights).")

    n = frame.n
    holdout = max(7, min(28, n // 4))
    train_dates, test_dates = frame.dates[: n - holdout], frame.dates[n - holdout :]
    y_train, y_test = y[: n - holdout], y[n - holdout :]

    scores: dict[str, dict[str, float]] = {}
    residuals: dict[str, np.ndarray] = {}
    for name, model in CANDIDATES.items():
        pred = model(train_dates, y_train, test_dates)
        scores[name] = {"mae": mae(y_test, pred), "rmse": rmse(y_test, pred), "smape": smape(y_test, pred)}
        residuals[name] = y_test - pred
    best = min(scores, key=lambda k: scores[k]["mae"])

    future = [frame.dates[-1] + timedelta(days=i + 1) for i in range(horizon_days)]
    yhat = np.clip(CANDIDATES[best](frame.dates, y, future), 0, None)
    # Centre the residuals: the interval describes error *dispersion* around the model's prediction.
    # (Holdout bias is reported in metrics rather than silently shifting the forecast.)
    bias = float(np.mean(residuals[best]))
    res = residuals[best] - bias
    lo_q, hi_q = np.percentile(res, [INTERVAL_LOW, INTERVAL_HIGH])
    result.points = [
        {
            "date": d.isoformat(),
            "predicted_kg": round(float(v), 3),
            "lower_kg": round(float(max(0.0, v + lo_q)), 3),
            "upper_kg": round(float(max(0.0, v + hi_q)), 3),
        }
        for d, v in zip(future, yhat, strict=True)
    ]

    rng = np.random.default_rng(seed)
    sims = yhat.sum() + rng.choice(res, size=(BOOTSTRAP_PATHS, horizon_days), replace=True).sum(axis=1)
    sims = np.clip(sims, 0, None)
    result.status = "ok"
    result.model_name = best
    result.predicted_total_kg = round(float(yhat.sum()), 2)
    result.lower_total_kg = round(float(np.percentile(sims, INTERVAL_LOW)), 2)
    result.upper_total_kg = round(float(np.percentile(sims, INTERVAL_HIGH)), 2)
    result.recent_total_kg = round(float(frame.total[-horizon_days:].sum()), 2) if n >= horizon_days else None
    baseline = scores["moving_average_28"]["mae"]
    result.metrics = {
        "selected_model": best,
        "holdout_days": holdout,
        "training_days": n - holdout,
        "candidates": {k: {m: round(v, 4) for m, v in s.items()} for k, s in scores.items()},
        "mae_kg_per_day": round(scores[best]["mae"], 4),
        "rmse_kg_per_day": round(scores[best]["rmse"], 4),
        "holdout_bias_kg_per_day": round(bias, 4),
        "skill_vs_moving_average": None if (s := skill_score(scores[best]["mae"], baseline)) is None else round(s, 4),
        "interval": f"{INTERVAL_HIGH - INTERVAL_LOW}% empirical (holdout residual percentiles)",
    }
    result.notes.append("Forecast assumes your recent routine continues; it cannot anticipate one-off trips.")
    return result
