"""Builds the factual context for the sustainability assistant from the user's own data.

The LLM never calculates emissions. Everything numeric it may cite is computed here by the
carbon engine, analytics queries and ML layer, and passed in as a FACTS JSON object.
"""

import re
from dataclasses import asdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.carbon.scenarios import LEVER_LABELS, ScenarioLevers, simulate
from app.models import Goal, Recommendation, User
from app.services import goals as goal_service
from app.services import ml_service
from app.services.analytics import BENCHMARK, Scope, by_activity, daily_category_rows

INTENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("what_if", re.compile(r"\bwhat if\b|\bwhat would happen\b|\bif i\b|\bsimulat|\bscenario", re.I)),
    (
        "why_change",
        re.compile(r"\bwhy\b.*\b(chang\w*|increas\w*|rise|rose|risen|went up|higher|spike\w*|jump\w*|decreas\w*|drop\w*|fell|lower)", re.I),
    ),  # noqa: E501
    ("plan", re.compile(r"\bplan\b|\broadmap\b|\bstep[- ]by[- ]step\b", re.I)),
    ("reduce", re.compile(r"\breduce\b|\blower\b|\bcut\b|\bimprove\b|\bsave\b|\bhow can i\b", re.I)),
    ("biggest_source", re.compile(r"\bbiggest\b|\blargest\b|\bmost of my\b|\bmain (source|cause)\b|\bcausing\b", re.I)),
    ("forecast", re.compile(r"\bforecast\b|\bpredict|\bnext month\b|\bfuture\b", re.I)),
    ("explain", re.compile(r"\bexplain\b|\bwhat is\b|\bunderstand\b|\bfootprint\b|\bsummar", re.I)),
]

TOPIC_PATTERNS: dict[str, re.Pattern[str]] = {
    "transport": re.compile(r"\b(car|drive|driving|commut|transport|bus|train|travel)", re.I),
    "flights": re.compile(r"\b(fly|flight|flights|plane|air)", re.I),
    "energy": re.compile(r"\b(electric|energy|heating|gas|power|solar|renewable)", re.I),
    "food": re.compile(r"\b(food|meat|beef|diet|vegetarian|vegan|eat)", re.I),
    "waste": re.compile(r"\b(waste|recycl|compost|bin)", re.I),
    "consumption": re.compile(r"\b(shopping|clothes|clothing|buy|purchas|electronics)", re.I),
}

# (lever, topic regex) — used to map "what if I reduced flights by 50%" onto scenario levers.
LEVER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ev_adoption_pct", re.compile(r"\b(ev|electric car|electric vehicle)\b", re.I)),
    ("flight_reduction_pct", TOPIC_PATTERNS["flights"]),
    ("car_reduction_pct", re.compile(r"\b(cars?|drive|drives|drove|driving|driven)\b", re.I)),
    ("renewable_share_pct", re.compile(r"\b(renewable|green tariff|solar)\b", re.I)),
    ("electricity_reduction_pct", re.compile(r"\belectric(ity)?\b", re.I)),
    ("heating_reduction_pct", re.compile(r"\b(heating|thermostat|gas)\b", re.I)),
    ("meat_reduction_pct", re.compile(r"\b(meat|beef|vegetarian|vegan)\b", re.I)),
    ("recycling_improvement_pct", re.compile(r"\b(recycl\w*|waste)\b", re.I)),
]
PCT_RE = re.compile(r"(\d{1,3})\s*(%|percent)")
DEFAULT_LEVER_PCT = 50.0


def detect_intents(question: str) -> list[str]:
    intents = [name for name, rx in INTENT_PATTERNS if rx.search(question)]
    return intents or ["explain"]


def detect_topics(question: str) -> list[str]:
    return [t for t, rx in TOPIC_PATTERNS.items() if rx.search(question)]


def parse_levers(question: str) -> ScenarioLevers | None:
    pct_match = PCT_RE.search(question)
    pct = min(100.0, float(pct_match.group(1))) if pct_match else DEFAULT_LEVER_PCT
    levers = ScenarioLevers()
    matched = False
    for lever, rx in LEVER_PATTERNS:
        if rx.search(question):
            # "electric car" should not also trigger the electricity or drive-less levers.
            if lever in ("electricity_reduction_pct", "car_reduction_pct") and levers.ev_adoption_pct:
                continue
            setattr(levers, lever, pct)
            matched = True
    return levers if matched else None


def _r(x: float | None, nd: int = 1) -> float | None:
    return None if x is None else round(x, nd)


def build_context(db: Session, user: User, question: str, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    scope = Scope(user_id=user.id)
    intents = detect_intents(question)
    topics = detect_topics(question)

    def window(days: int, offset: int = 0) -> dict[str, float]:
        end = today - timedelta(days=offset)
        start = end - timedelta(days=days - 1)
        totals: dict[str, float] = {}
        for _, c, kg in daily_category_rows(db, scope, start, end):
            totals[c] = totals.get(c, 0.0) + kg
        return totals

    last30, prev30 = window(30), window(30, 30)
    total30, totalp = sum(last30.values()), sum(prev30.values())
    facts: dict[str, Any] = {
        "as_of": today.isoformat(),
        "user_first_name": user.full_name.split()[0] if user.full_name else None,
        "units": "kg CO2e unless stated",
        "last_30_days": {
            "total_kg": _r(total30),
            "by_category_kg": {c: _r(v) for c, v in sorted(last30.items(), key=lambda kv: -kv[1])},
            "share_pct": {c: _r(100 * v / total30) for c, v in last30.items()} if total30 else {},
        },
        "previous_30_days": {
            "total_kg": _r(totalp),
            "by_category_kg": {c: _r(v) for c, v in sorted(prev30.items(), key=lambda kv: -kv[1])},
        },
        "change_vs_previous_30_days_pct": _r(100 * (total30 - totalp) / totalp) if totalp else None,
        "category_change_kg": {c: _r(last30.get(c, 0) - prev30.get(c, 0)) for c in set(last30) | set(prev30)},
        "annualized_pace_kg": _r(total30 / 30 * 365.25, 0) if total30 else None,
        "benchmark": {"label": BENCHMARK["label"], "annual_kg": BENCHMARK["annual_kg"], "source": BENCHMARK["source"]},
    }

    activities = by_activity(db, scope, today - timedelta(days=29), today)[:8]
    facts["top_activities_last_30_days"] = [
        {
            "activity_type": a["activity_type"],
            "factor": a["factor_key"],
            "count": a["count"],
            "quantity": _r(a["quantity"]),
            "unit": a["unit"],
            "kg": _r(a["kg"]),
            "share_pct": a["share_pct"],
        }
        for a in activities
    ]

    if user.profile:
        p = user.profile
        facts["profile"] = {
            k: v
            for k, v in {
                "country": p.country,
                "household_size": p.household_size,
                "vehicle_type": p.vehicle_type,
                "diet_type": p.diet_type,
                "heating_fuel": p.heating_fuel,
                "renewable_share_pct": p.renewable_share_pct,
            }.items()
            if v is not None
        }

    anomalies = ml_service.run_anomaly_detection(db, user, today)
    facts["anomalies"] = [
        {
            "message": a.message,
            "category": a.category,
            "observed_kg": a.observed_kg,
            "expected_kg": a.expected_kg,
            "pct_above": a.pct_above,
            "method": a.method,
            "date": a.date or a.period_end,
        }
        for a in anomalies[:5]
    ]

    recs = db.scalars(
        select(Recommendation)
        .where(Recommendation.user_id == user.id, Recommendation.is_current.is_(True), Recommendation.status != "dismissed")
        .order_by(Recommendation.priority_score.desc())
        .limit(6)
    ).all()
    if topics:
        recs = sorted(recs, key=lambda r: (r.category not in topics, -r.priority_score))
    facts["recommendations"] = [
        {
            "title": r.title,
            "category": r.category,
            "current": r.current_behavior,
            "action": r.suggested_action,
            "monthly_reduction_kg": r.estimated_monthly_reduction_kg,
            "annual_reduction_kg": _r(r.estimated_monthly_reduction_kg * 12),
            "difficulty": r.difficulty,
            "calculation": r.calculation_basis,
        }
        for r in recs
    ]

    fc = ml_service.run_forecast(db, user, 30, persist=False, today=today)
    facts["forecast_next_30_days"] = (
        {
            "model": fc.model_name,
            "predicted_kg": fc.predicted_total_kg,
            "lower_kg": fc.lower_total_kg,
            "upper_kg": fc.upper_total_kg,
            "interval": "80%",
        }
        if fc.status == "ok"
        else {"status": "insufficient_data", "note": fc.notes[-1] if fc.notes else None}
    )

    goals = db.scalars(select(Goal).where(Goal.user_id == user.id, Goal.status == "active")).all()
    facts["goals"] = []
    for g in goals:
        ev = goal_service.evaluate(db, g, today)
        facts["goals"].append(
            {
                "title": g.title,
                "category": g.category,
                "baseline_monthly_kg": _r(g.baseline_monthly_kg),
                "target_reduction_pct": g.target_reduction_pct,
                "deadline": g.deadline.isoformat(),
                **ev,
            }
        )

    if "what_if" in intents or "plan" in intents:
        levers = parse_levers(question)
        if levers is None and "plan" in intents:
            levers = ScenarioLevers(
                car_reduction_pct=20,
                flight_reduction_pct=50,
                renewable_share_pct=100,
                meat_reduction_pct=50,
                recycling_improvement_pct=50,
            )
        if levers is not None:
            profile = ml_service.behaviour_profile(db, user, today)
            if profile.items:
                res = simulate(db, profile, levers, user.profile.country if user.profile else None)
                facts["scenario"] = {
                    "levers": {LEVER_LABELS[k]: v for k, v in asdict(levers).items() if v},
                    "basis": res.basis,
                    "current_monthly_kg": _r(res.current_monthly_kg),
                    "scenario_monthly_kg": _r(res.scenario_monthly_kg),
                    "reduction_monthly_kg": _r(res.reduction_monthly_kg),
                    "reduction_annual_kg": _r(res.reduction_monthly_kg * 12),
                    "reduction_pct": _r(res.reduction_pct),
                    "lever_effects": [{**e, "monthly_reduction_kg": _r(e["monthly_reduction_kg"])} for e in res.lever_effects],
                    "assumptions": res.assumptions[:4],
                }
    db.commit()
    return {"intents": intents, "topics": topics, "facts": facts}
