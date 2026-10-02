"""Response validation: every emission figure in an LLM answer must trace back to the FACTS.

We extract numbers attached to emission/percentage units and check each against the set of
numbers present in the context (allowing for rounding and kg<->tonne conversion). Unverifiable
figures are reported to the client and flagged in the UI.
"""

import re
from typing import Any

NUMBER_UNIT_RE = re.compile(
    r"(?<![\w.])(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)\s*"
    r"(kg|kilograms?|t\b|tonnes?|tons?|%|percent|per\s?cent)",
    re.IGNORECASE,
)


def _numbers_in(value: Any, out: list[float]) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, int | float):
        out.append(float(value))
    elif isinstance(value, dict):
        for v in value.values():
            _numbers_in(v, out)
    elif isinstance(value, list | tuple):
        for v in value:
            _numbers_in(v, out)
    elif isinstance(value, str):
        for m in re.finditer(r"-?\d[\d,]*\.?\d*", value):
            try:
                out.append(float(m.group().replace(",", "")))
            except ValueError:
                continue


def allowed_numbers(facts: dict[str, Any], question: str = "") -> list[float]:
    nums: list[float] = []
    _numbers_in(facts, nums)
    _numbers_in(question, nums)
    expanded = set()
    for n in nums:
        expanded.update({n, abs(n), n / 1000, abs(n) / 1000})
    return sorted(expanded)


def _matches(x: float, candidates: list[float], decimals: int) -> bool:
    # Tolerance: half a unit in the last displayed digit, or 1% relative — whichever is larger.
    tol_round = 0.5 * 10 ** (-decimals)
    return any(abs(x - c) <= max(tol_round, 0.01 * abs(c)) for c in candidates)


def validate_numbers(text: str, facts: dict[str, Any], question: str = "") -> dict[str, Any]:
    candidates = allowed_numbers(facts, question)
    checked, unverified = 0, []
    for m in NUMBER_UNIT_RE.finditer(text):
        raw, unit = m.group(1), m.group(2).lower()
        value = float(raw.replace(",", ""))
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        checked += 1
        if not _matches(value, candidates, decimals) and not _matches(abs(value), candidates, decimals):
            unverified.append(f"{raw} {unit}")
    return {
        "status": "verified" if not unverified else "flagged",
        "numbers_checked": checked,
        "unverified": unverified,
    }
