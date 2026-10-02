"""Deterministic 'demo mode' assistant.

Used when no LLM API key is configured (or the provider fails). It is NOT a language model:
it selects templates by detected intent and fills them only with values from the computed FACTS,
so every answer still reflects the user's real data. Responses are labelled as demo mode in the UI.
"""

from typing import Any

CATEGORY_LABELS = {
    "transport": "transport",
    "flights": "flights",
    "energy": "home energy",
    "food": "food",
    "waste": "waste",
    "consumption": "shopping",
    "digital": "digital",
    "business": "business travel",
    "other": "other sources",
}


def _cat(c: str | None) -> str:
    return CATEGORY_LABELS.get(c or "", c or "unknown")


def _no_data(facts: dict[str, Any]) -> bool:
    return not facts["last_30_days"]["total_kg"]


def _breakdown(facts: dict[str, Any], limit: int = 3) -> str:
    cats = facts["last_30_days"]["by_category_kg"]
    shares = facts["last_30_days"]["share_pct"]
    return "\n".join(f"- **{_cat(c)}**: {kg} kg ({shares.get(c)}%)" for c, kg in list(cats.items())[:limit])


def _recs(facts: dict[str, Any], limit: int = 3, topics: list[str] | None = None) -> str:
    recs = facts["recommendations"]
    if topics:
        topical = [r for r in recs if r["category"] in topics]
        recs = topical or recs
    return "\n".join(
        f"- **{r['title']}** — {r['action']}. Saves ~{r['monthly_reduction_kg']} kg/month ({r['difficulty']})." for r in recs[:limit]
    )


def respond(question: str, context: dict[str, Any]) -> str:
    facts, intents, topics = context["facts"], context["intents"], context["topics"]
    if _no_data(facts) and "scenario" not in facts:
        return (
            "I don't have any tracked activities from the last 30 days yet, so I can't analyse your footprint. "
            "Log a few journeys, energy readings or meals in **Activities** and I'll be able to explain where "
            "your emissions come from and what would reduce them most."
        )

    parts: list[str] = []
    if "what_if" in intents and "scenario" in facts:
        s = facts["scenario"]
        levers = ", ".join(f"{k} {v:.0f}%" for k, v in s["levers"].items())
        parts.append(
            f"Simulating **{levers}** on your {'tracked' if s['basis'] == 'tracked_activities' else 'estimated'} "
            f"monthly footprint: {s['current_monthly_kg']} kg → {s['scenario_monthly_kg']} kg CO2e, a reduction of "
            f"{s['reduction_monthly_kg']} kg/month ({s['reduction_pct']}%), or {s['reduction_annual_kg']} kg a year."
        )
        if s["lever_effects"]:
            parts.append("\n".join(f"- {e['label']}: {e['monthly_reduction_kg']} kg/month" for e in s["lever_effects"]))
    elif "what_if" in intents:
        parts.append(
            'I couldn\'t map that to a scenario lever. Try the **Scenario Simulator**, or ask e.g. "What if I reduced flights by 50%?"'
        )

    if "why_change" in intents:
        change = facts["change_vs_previous_30_days_pct"]
        if change is None:
            parts.append("There isn't a previous 30-day period with data to compare against yet.")
        else:
            direction = "up" if change > 0 else "down"
            parts.append(
                f"Your emissions are {direction} {abs(change)}% versus the previous 30 days "
                f"({facts['last_30_days']['total_kg']} kg vs {facts['previous_30_days']['total_kg']} kg)."
            )
            deltas = sorted(facts["category_change_kg"].items(), key=lambda kv: -abs(kv[1] or 0))[:3]
            parts.append("Biggest movers:\n" + "\n".join(f"- {_cat(c)}: {'+' if d > 0 else ''}{d} kg" for c, d in deltas if d))
        for a in facts["anomalies"][:2]:
            parts.append(f"⚠ {a['message']}")

    if "biggest_source" in intents or "explain" in intents:
        cats = facts["last_30_days"]["by_category_kg"]
        if cats:
            top = next(iter(cats))
            parts.append(
                f"In the last 30 days you tracked **{facts['last_30_days']['total_kg']} kg CO2e**. "
                f"Your largest source is **{_cat(top)}** at {facts['last_30_days']['share_pct'].get(top)}%:\n" + _breakdown(facts)
            )
            acts = facts["top_activities_last_30_days"][:3]
            if acts:
                parts.append("Top activities: " + "; ".join(f"{a['activity_type']} ({a['kg']} kg)" for a in acts) + ".")
        if facts.get("annualized_pace_kg"):
            parts.append(
                f"At this pace that's about {facts['annualized_pace_kg']} kg a year, against a 1.5°C-aligned lifestyle "
                f"target of {facts['benchmark']['annual_kg']} kg."
            )

    if "forecast" in intents:
        fc = facts["forecast_next_30_days"]
        if fc.get("predicted_kg") is not None:
            parts.append(
                f"The forecast ({fc['model']}) for the next 30 days is {fc['predicted_kg']} kg "
                f"(80% range {fc['lower_kg']}–{fc['upper_kg']} kg), assuming your routine continues."
            )
        else:
            parts.append(fc.get("note") or "Not enough history for a forecast yet.")

    if "reduce" in intents or "plan" in intents or not parts:
        recs = _recs(facts, 4 if "plan" in intents else 3, topics)
        if recs:
            heading = "A realistic plan, highest-impact first:" if "plan" in intents else "Your highest-impact options:"
            parts.append(f"{heading}\n{recs}")
        if "plan" in intents and "scenario" in facts:
            sc = facts["scenario"]
            levers = ", ".join(f"{k.lower()} {v:.0f}%" for k, v in sc["levers"].items())
            parts.append(
                f"A combined scenario ({levers}) is modelled at {sc['reduction_monthly_kg']} kg/month lower "
                f"({sc['reduction_pct']}%). Try your own mix in the Scenario Simulator."
            )
        for g in facts["goals"][:1]:
            parts.append(f"Goal **{g['title']}**: {g['progress_pct']}% of the way to {g['target_monthly_kg']} kg/month.")

    parts.append("_Demo mode: deterministic answer generated from your data without a language model._")
    return "\n\n".join(parts)
