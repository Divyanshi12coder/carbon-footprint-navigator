"""Insight engine: turns stored data, ML outputs and goals into short, factual statements.

Every number in an insight is computed here from the database; the text is a template around it.
"""

from datetime import date, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import EmissionRecord, Goal, Insight, Recommendation, User
from app.services import goals as goal_service
from app.services import ml_service
from app.services.analytics import BENCHMARK, Scope, daily_category_rows

WINDOW = 30
MIN_CATEGORY_DELTA_KG = 5.0
MIN_CATEGORY_DELTA_PCT = 10.0


def _cat_totals(rows: list[tuple[date, str, float]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for _, c, kg in rows:
        out[c] = out.get(c, 0.0) + kg
    return out


def _label(category: str) -> str:
    return category.replace("_", " ").capitalize()


def compute_insights(db: Session, user: User, today: date | None = None) -> list[dict[str, Any]]:
    today = today or date.today()
    scope = Scope(user_id=user.id)
    cur_start = today - timedelta(days=WINDOW - 1)
    prev_end = cur_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=WINDOW - 1)
    cur = _cat_totals(daily_category_rows(db, scope, cur_start, today))
    prev = _cat_totals(daily_category_rows(db, scope, prev_start, prev_end))
    total, prev_total = sum(cur.values()), sum(prev.values())
    out: list[dict[str, Any]] = []

    if total > 0:
        top, top_kg = max(cur.items(), key=lambda kv: kv[1])
        share = 100 * top_kg / total
        out.append(
            dict(
                insight_type="largest_source",
                severity="info",
                category=top,
                metric_value=round(share, 1),
                title=f"{_label(top)} is your largest emission source",
                body=f"{_label(top)} accounts for {share:.0f}% of your tracked emissions in the last 30 days "
                f"({top_kg:.1f} of {total:.1f} kg CO2e).",
                data={"category_kg": round(top_kg, 2), "total_kg": round(total, 2)},
            )
        )

    if total > 0 and prev_total > 0:
        change = 100 * (total - prev_total) / prev_total
        direction = "decreased" if change < 0 else "increased"
        severity = "positive" if change <= -5 else ("warning" if change >= 5 else "info")
        out.append(
            dict(
                insight_type="period_change",
                severity=severity,
                category=None,
                metric_value=round(change, 1),
                title=f"Emissions {direction} {abs(change):.0f}% vs the previous 30 days",
                body=f"Your emissions {direction} {abs(change):.0f}% compared with the previous 30 days "
                f"({total:.1f} kg vs {prev_total:.1f} kg CO2e).",
                data={"current_kg": round(total, 2), "previous_kg": round(prev_total, 2)},
            )
        )
        deltas = {c: cur.get(c, 0.0) - prev.get(c, 0.0) for c in set(cur) | set(prev)}
        inc_cat, inc = max(deltas.items(), key=lambda kv: kv[1])
        if inc >= MIN_CATEGORY_DELTA_KG and (prev.get(inc_cat, 0) == 0 or 100 * inc / prev[inc_cat] >= MIN_CATEGORY_DELTA_PCT):
            pct = 100 * inc / prev[inc_cat] if prev.get(inc_cat) else None
            out.append(
                dict(
                    insight_type="biggest_increase",
                    severity="warning",
                    category=inc_cat,
                    metric_value=round(inc, 2),
                    title=f"Biggest increase: {_label(inc_cat)}",
                    body=f"{_label(inc_cat)} emissions rose by {inc:.1f} kg CO2e"
                    + (f" ({pct:.0f}%)" if pct is not None else "")
                    + " compared with the previous 30 days.",
                    data={"current_kg": round(cur.get(inc_cat, 0), 2), "previous_kg": round(prev.get(inc_cat, 0), 2)},
                )
            )
        dec_cat, dec = min(deltas.items(), key=lambda kv: kv[1])
        if -dec >= MIN_CATEGORY_DELTA_KG and prev.get(dec_cat, 0) > 0 and 100 * -dec / prev[dec_cat] >= MIN_CATEGORY_DELTA_PCT:
            out.append(
                dict(
                    insight_type="biggest_improvement",
                    severity="positive",
                    category=dec_cat,
                    metric_value=round(-dec, 2),
                    title=f"Biggest improvement: {_label(dec_cat)}",
                    body=f"{_label(dec_cat)} emissions fell by {-dec:.1f} kg CO2e ({100 * -dec / prev[dec_cat]:.0f}%) "
                    f"compared with the previous 30 days.",
                    data={"current_kg": round(cur.get(dec_cat, 0), 2), "previous_kg": round(prev[dec_cat], 2)},
                )
            )

    anomalies = ml_service.run_anomaly_detection(db, user, today)
    weekly = [a for a in anomalies if a.method == "weekly_robust_z"][:2]
    daily = [a for a in anomalies if a.method == "isolation_forest"][-1:]
    for a in weekly + daily:
        out.append(
            dict(
                insight_type="anomaly",
                severity="warning",
                category=a.category,
                metric_value=a.pct_above,
                title="Unusual week" if a.method == "weekly_robust_z" else "Unusual day",
                body=a.message,
                data=a.to_dict(),
            )
        )

    top_rec = db.scalars(
        select(Recommendation)
        .where(Recommendation.user_id == user.id, Recommendation.is_current.is_(True), Recommendation.status == "open")
        .order_by(Recommendation.priority_score.desc())
        .limit(1)
    ).first()
    if top_rec:
        out.append(
            dict(
                insight_type="opportunity",
                severity="info",
                category=top_rec.category,
                metric_value=top_rec.estimated_monthly_reduction_kg,
                title=f"Top opportunity: {top_rec.title}",
                body=f"{top_rec.suggested_action}. Estimated saving: {top_rec.estimated_monthly_reduction_kg:.1f} kg CO2e per month "
                f"({top_rec.share_of_footprint_pct:.0f}% of your footprint).",
                data={"recommendation_id": str(top_rec.id)},
            )
        )

    fc = ml_service.run_forecast(db, user, 30, persist=False, today=today)
    if fc.status == "ok" and fc.recent_total_kg:
        change = 100 * (fc.predicted_total_kg - fc.recent_total_kg) / fc.recent_total_kg
        if abs(change) >= 10:
            out.append(
                dict(
                    insight_type="forecast",
                    severity="warning" if change > 0 else "positive",
                    category=None,
                    metric_value=round(change, 1),
                    title=f"Forecast: next 30 days {'up' if change > 0 else 'down'} {abs(change):.0f}%",
                    body=f"The {fc.model_name} model projects {fc.predicted_total_kg:.0f} kg CO2e over the next 30 days "
                    f"(80% range {fc.lower_total_kg:.0f}–{fc.upper_total_kg:.0f} kg), versus {fc.recent_total_kg:.0f} kg in the last 30.",
                    data={"predicted_kg": fc.predicted_total_kg, "recent_kg": fc.recent_total_kg},
                )
            )

    for goal in db.scalars(select(Goal).where(Goal.user_id == user.id, Goal.status == "active")):
        ev = goal_service.evaluate(db, goal, today)
        if ev["current_monthly_kg"] is None:
            continue
        out.append(
            dict(
                insight_type="goal_progress",
                severity="positive" if ev["on_track"] else "info",
                category=goal.category,
                metric_value=ev["progress_pct"],
                title=f"Goal: {goal.title}",
                body=f"{ev['progress_pct']:.0f}% of the way to your target of {ev['target_monthly_kg']:.0f} kg/month "
                f"(currently {ev['current_monthly_kg']:.0f} kg/month, {ev['days_remaining']} days left).",
                data={"goal_id": str(goal.id), **ev},
            )
        )

    low_q, all_q = db.execute(
        select(
            func.count(EmissionRecord.id).filter(EmissionRecord.data_quality == "low"),
            func.count(EmissionRecord.id),
        ).where(EmissionRecord.user_id == user.id, EmissionRecord.occurred_on >= cur_start)
    ).one()
    if all_q and low_q / all_q >= 0.3:
        out.append(
            dict(
                insight_type="data_quality",
                severity="info",
                category=None,
                metric_value=round(100 * low_q / all_q, 1),
                title="Some estimates are low-confidence",
                body=f"{100 * low_q / all_q:.0f}% of recent records use low-confidence factors (e.g. spend-based purchases). "
                "Logging specific products or quantities improves accuracy.",
                data={"low_quality_records": low_q, "records": all_q},
            )
        )

    if total > 0:
        annual = total / WINDOW * 365.25
        ratio = annual / BENCHMARK["annual_kg"]
        out.append(
            dict(
                insight_type="benchmark",
                severity="positive" if ratio <= 1 else "info",
                category=None,
                metric_value=round(annual, 0),
                title="Annualised pace vs 1.5°C lifestyle target",
                body=f"At your last-30-day pace your tracked footprint is ~{annual / 1000:.2f} t CO2e/year, "
                f"{ratio:.1f}x the {BENCHMARK['annual_kg'] / 1000:.1f} t 2030 target ({BENCHMARK['source']}). "
                "Untracked activities are not included.",
                data={"annualized_kg": round(annual, 1)},
            )
        )
    db.commit()  # goal status transitions from evaluate()
    return out


def refresh_insights(db: Session, user: User, today: date | None = None) -> list[Insight]:
    computed = compute_insights(db, user, today)
    db.execute(delete(Insight).where(Insight.user_id == user.id))
    rows = [Insight(user_id=user.id, **item) for item in computed]
    db.add_all(rows)
    db.commit()
    return rows
