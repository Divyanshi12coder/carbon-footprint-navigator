"""Forecasting and anomaly detection on synthetic series with known structure."""

from datetime import date, timedelta

import numpy as np
import pytest

from app.ml import anomaly_detection, forecasting
from app.ml.evaluation import mae, skill_score, smape
from app.ml.feature_engineering import build_daily_frame, rolling_mean, weekly_blocks


def _frame(days: int, fn, category: str = "transport"):
    start = date(2026, 1, 5)  # a Monday
    rows = [(start + timedelta(days=i), category, fn(i, start + timedelta(days=i))) for i in range(days)]
    return build_daily_frame(rows, start, start + timedelta(days=days - 1))


def test_feature_engineering_helpers():
    frame = _frame(14, lambda i, d: float(i))
    assert frame.n == 14 and frame.total[3] == 3
    assert rolling_mean(np.array([2.0, 4.0, 6.0]), 2).tolist() == [2.0, 3.0, 5.0]
    blocks = weekly_blocks(frame.total, 3)
    assert blocks.tolist() == [sum(range(7, 14)), sum(range(0, 7))]


def test_metrics():
    a, p = np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 5.0])
    assert mae(a, p) == pytest.approx(2 / 3)
    assert smape(np.zeros(3), np.zeros(3)) == 0
    assert skill_score(5, 10) == pytest.approx(0.5)


def test_forecast_cold_start():
    result = forecasting.forecast(_frame(10, lambda i, d: 5.0), 30)
    assert result.status == "insufficient_data"
    assert result.points == []
    assert "at least" in result.notes[0]


def test_forecast_learns_weekly_pattern():
    rng = np.random.default_rng(0)
    # Weekdays ~20 kg (commuting), weekends ~5 kg.
    frame = _frame(120, lambda i, d: (20.0 if d.weekday() < 5 else 5.0) + rng.normal(0, 1))
    result = forecasting.forecast(frame, 14)
    assert result.status == "ok"
    assert result.model_name in ("seasonal_weekday_28", "ridge_trend_weekday")
    assert result.metrics["skill_vs_moving_average"] > 0.3
    weekday = [p for p in result.points if date.fromisoformat(p["date"]).weekday() < 5]
    weekend = [p for p in result.points if date.fromisoformat(p["date"]).weekday() >= 5]
    assert np.mean([p["predicted_kg"] for p in weekday]) > 3 * np.mean([p["predicted_kg"] for p in weekend])
    for p in result.points:
        assert p["lower_kg"] <= p["predicted_kg"] <= p["upper_kg"]
    assert result.lower_total_kg <= result.predicted_total_kg <= result.upper_total_kg


def test_forecast_never_negative_and_caps_outliers():
    frame = _frame(60, lambda i, d: 400.0 if i == 30 else 3.0)
    result = forecasting.forecast(frame, 30)
    assert result.status == "ok"
    assert all(p["lower_kg"] >= 0 for p in result.points)
    assert any("capped" in n for n in result.notes)
    assert result.predicted_total_kg < 30 * 10  # the one-off 400 kg day doesn't inflate the forecast


def test_weekly_anomaly_detected_with_percentage():
    # Stable ~30 kg/week of transport, last week ~3x.
    frame = _frame(84, lambda i, d: (13.0 if i >= 77 else 4.3) + (0.2 if i % 3 == 0 else 0.0))
    anomalies = anomaly_detection.weekly_category_anomalies(frame)
    assert len(anomalies) == 1
    a = anomalies[0]
    assert a.category == "transport"
    expected_pct = 100 * (a.observed_kg - a.expected_kg) / a.expected_kg
    assert a.pct_above == pytest.approx(expected_pct, abs=0.2)
    assert "above your normal weekly pattern" in a.message


def test_no_anomaly_for_stable_history():
    rng = np.random.default_rng(1)
    frame = _frame(84, lambda i, d: 5 + rng.normal(0, 0.3))
    assert anomaly_detection.weekly_category_anomalies(frame) == []


def test_isolation_forest_flags_spike_day():
    rng = np.random.default_rng(2)
    frame = _frame(90, lambda i, d: 70.0 if i == 85 else 8 + rng.normal(0, 1))
    flagged = anomaly_detection.daily_isolation_forest(frame)
    assert any(a.date == frame.dates[85].isoformat() for a in flagged)
    assert all(a.method == "isolation_forest" for a in flagged)


def test_isolation_forest_needs_history():
    assert anomaly_detection.daily_isolation_forest(_frame(20, lambda i, d: 5.0)) == []
