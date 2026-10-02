"""Turn emission records into dense daily/weekly arrays for the ML models (numpy only)."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np


@dataclass
class DailyFrame:
    dates: list[date]
    total: np.ndarray  # shape (n,)
    by_category: dict[str, np.ndarray]  # each shape (n,)

    @property
    def n(self) -> int:
        return len(self.dates)

    @property
    def active_days(self) -> int:
        return int(np.count_nonzero(self.total))


def build_daily_frame(rows: Iterable[tuple[date, str, float]], start: date, end: date) -> DailyFrame:
    """rows: (occurred_on, category, kg). Missing days are zero-filled (no activity logged)."""
    n = (end - start).days + 1
    dates = [start + timedelta(days=i) for i in range(n)]
    total = np.zeros(n)
    by_cat: dict[str, np.ndarray] = {}
    for day, category, kg in rows:
        idx = (day - start).days
        if 0 <= idx < n:
            total[idx] += kg
            by_cat.setdefault(category, np.zeros(n))[idx] += kg
    return DailyFrame(dates, total, by_cat)


def rolling_mean(values: np.ndarray, window: int) -> np.ndarray:
    """Trailing mean including the current day; the first window-1 points use what is available."""
    if len(values) == 0:
        return values.copy()
    csum = np.cumsum(np.insert(values, 0, 0.0))
    out = np.empty(len(values))
    for i in range(len(values)):
        lo = max(0, i + 1 - window)
        out[i] = (csum[i + 1] - csum[lo]) / (i + 1 - lo)
    return out


def trailing_baseline(values: np.ndarray, window: int) -> np.ndarray:
    """Median of the previous `window` days (excluding the current day). NaN where unavailable."""
    out = np.full(len(values), np.nan)
    for i in range(1, len(values)):
        lo = max(0, i - window)
        out[i] = float(np.median(values[lo:i]))
    return out


def weekly_blocks(values: np.ndarray, n_blocks: int) -> np.ndarray:
    """Sum values in consecutive 7-day blocks aligned to the END of the series.

    Returns most-recent-first: block 0 = last 7 days, block 1 = the 7 days before, ...
    Incomplete leading blocks are dropped.
    """
    blocks = []
    end = len(values)
    for _ in range(n_blocks):
        start = end - 7
        if start < 0:
            break
        blocks.append(float(values[start:end].sum()))
        end = start
    return np.array(blocks)


def calendar_features(dates: list[date], t0: date, trend_scale: float = 365.0) -> np.ndarray:
    """[trend, dow_0..dow_6] design matrix for the regression forecaster."""
    x = np.zeros((len(dates), 8))
    for i, d in enumerate(dates):
        x[i, 0] = (d - t0).days / trend_scale
        x[i, 1 + d.weekday()] = 1.0
    return x


def clip_outliers(values: np.ndarray, iqr_multiplier: float = 3.0) -> tuple[np.ndarray, int]:
    """Cap extreme one-off days (e.g. a long-haul flight) so they don't dominate trend fitting."""
    if len(values) < 8:
        return values.copy(), 0
    q1, q3 = np.percentile(values, [25, 75])
    cap = q3 + iqr_multiplier * max(q3 - q1, 1e-9)
    clipped = np.minimum(values, cap)
    return clipped, int(np.count_nonzero(values > cap))
