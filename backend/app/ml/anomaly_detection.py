"""Emission anomaly detection.

Two complementary detectors run on the user's own history:

1. **Weekly category deviation (robust z-score)** — for each category, the last 7 days are compared
   with the median of up to 12 previous 7-day blocks. Robust z = 0.6745 * (x - median) / MAD.
   Flags increases that are both statistically unusual and practically meaningful
   (>= 25% above normal and >= 1 kg). Produces messages such as
   "Your transport emissions were 42% above your normal weekly pattern."

2. **Daily Isolation Forest** — scikit-learn IsolationForest over daily feature vectors
   [total, total - trailing 28-day median, per-category kg]. Only upward spikes that are also
   >= 1.5x the trailing median are reported, and each is attributed to the category that deviated most.
   Requires >= 30 days of history with >= 10 active days.
"""

from dataclasses import asdict, dataclass

import numpy as np
from sklearn.ensemble import IsolationForest

from app.ml.feature_engineering import DailyFrame, trailing_baseline, weekly_blocks

MIN_BASELINE_WEEKS = 4
MAX_BASELINE_WEEKS = 12
Z_THRESHOLD = 2.0
MIN_PCT_ABOVE = 25.0
MIN_ABS_KG = 1.0
IFOREST_MIN_DAYS = 30
IFOREST_MIN_ACTIVE = 10
SPIKE_RATIO = 1.5


@dataclass
class Anomaly:
    method: str  # "weekly_robust_z" | "isolation_forest"
    category: str | None
    date: str | None
    period_start: str | None
    period_end: str | None
    observed_kg: float
    expected_kg: float
    pct_above: float
    score: float
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


def weekly_category_anomalies(frame: DailyFrame) -> list[Anomaly]:
    out: list[Anomaly] = []
    if frame.n < 7 * (MIN_BASELINE_WEEKS + 1):
        return out
    period_start, period_end = frame.dates[-7].isoformat(), frame.dates[-1].isoformat()
    for category, series in frame.by_category.items():
        blocks = weekly_blocks(series, MAX_BASELINE_WEEKS + 1)
        if len(blocks) < MIN_BASELINE_WEEKS + 1:
            continue
        current, history = blocks[0], blocks[1:]
        if np.count_nonzero(history) < MIN_BASELINE_WEEKS:
            continue  # category not part of the user's normal routine
        median = float(np.median(history))
        mad = float(np.median(np.abs(history - median)))
        if median <= 0 or current <= median:
            continue
        pct = 100 * (current - median) / median
        z = 0.6745 * (current - median) / mad if mad > 0 else float("inf")
        if z >= Z_THRESHOLD and pct >= MIN_PCT_ABOVE and current - median >= MIN_ABS_KG:
            out.append(
                Anomaly(
                    method="weekly_robust_z",
                    category=category,
                    date=None,
                    period_start=period_start,
                    period_end=period_end,
                    observed_kg=round(current, 2),
                    expected_kg=round(median, 2),
                    pct_above=round(pct, 1),
                    score=round(min(z, 99.0), 2),
                    message=f"Your {category} emissions were {pct:.0f}% above your normal weekly pattern "
                    f"({current:.1f} kg vs a typical {median:.1f} kg).",
                )
            )
    return sorted(out, key=lambda a: a.pct_above, reverse=True)


def daily_isolation_forest(frame: DailyFrame, lookback_days: int = 60, seed: int = 42) -> list[Anomaly]:
    if frame.n < IFOREST_MIN_DAYS or frame.active_days < IFOREST_MIN_ACTIVE:
        return []
    categories = sorted(frame.by_category)
    baseline = trailing_baseline(frame.total, 28)
    baseline = np.where(np.isnan(baseline), np.nanmedian(frame.total), baseline)
    cat_matrix = np.column_stack([frame.by_category[c] for c in categories]) if categories else np.zeros((frame.n, 0))
    x = np.column_stack([frame.total, frame.total - baseline, cat_matrix])
    std = x.std(axis=0)
    x = (x - x.mean(axis=0)) / np.where(std == 0, 1, std)

    model = IsolationForest(n_estimators=200, contamination=0.04, random_state=seed)
    labels = model.fit_predict(x)
    scores = -model.score_samples(x)  # higher = more anomalous

    cat_means = {c: float(np.mean(frame.by_category[c])) for c in categories}
    out: list[Anomaly] = []
    for i in range(max(0, frame.n - lookback_days), frame.n):
        expected = float(baseline[i])
        observed = float(frame.total[i])
        if labels[i] != -1 or observed < max(SPIKE_RATIO * expected, expected + MIN_ABS_KG):
            continue
        driver = max(categories, key=lambda c: frame.by_category[c][i] - cat_means[c]) if categories else None
        pct = 100 * (observed - expected) / expected if expected > 0 else 100.0
        day = frame.dates[i]
        out.append(
            Anomaly(
                method="isolation_forest",
                category=driver,
                date=day.isoformat(),
                period_start=None,
                period_end=None,
                observed_kg=round(observed, 2),
                expected_kg=round(expected, 2),
                pct_above=round(pct, 1),
                score=round(float(scores[i]), 3),
                message=f"{day.strftime('%d %b')}: {observed:.1f} kg CO2e, well above your typical "
                f"{expected:.1f} kg day" + (f" — mostly {driver}." if driver else "."),
            )
        )
    return out


def detect(frame: DailyFrame) -> list[Anomaly]:
    return weekly_category_anomalies(frame) + daily_isolation_forest(frame)
