from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models import EmissionFactor, EmissionRecord
from tests.conftest import add_activity


def test_create_activity_persists_traceable_record(client, user, db):
    act = add_activity(client, user["headers"], "car", 50, "km", fuel_type="diesel")
    factor = db.scalar(select(EmissionFactor).where(EmissionFactor.key == "transport.car.diesel"))
    em = act["emission"]
    assert em["co2e_kg"] == pytest.approx(50 * factor.co2e_per_unit)
    assert em["emission_factor_id"] == str(factor.id)
    assert em["factor_source"] == factor.source
    assert em["calculation_method"]
    record = db.scalar(select(EmissionRecord).where(EmissionRecord.activity_id == act["id"]))
    assert record is not None and record.co2e_kg == pytest.approx(em["co2e_kg"])


def test_preview_does_not_persist(client, user, db):
    resp = client.post(
        "/api/activities/preview",
        headers=user["headers"],
        json={"activity_type": "meal", "quantity": 2, "unit": "serving", "details": {"meal_type": "beef"}},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["co2e_kg"] > 0
    assert client.get("/api/activities", headers=user["headers"]).json()["total"] == 0


def test_invalid_activity_returns_422(client, user):
    resp = client.post(
        "/api/activities",
        headers=user["headers"],
        json={"activity_type": "car", "quantity": 10, "unit": "kWh", "occurred_on": date.today().isoformat(), "details": {}},
    )
    assert resp.status_code == 422
    future = (date.today() + timedelta(days=5)).isoformat()
    resp = client.post(
        "/api/activities",
        headers=user["headers"],
        json={"activity_type": "car", "quantity": 10, "unit": "km", "occurred_on": future, "details": {"fuel_type": "petrol"}},
    )
    assert resp.status_code == 422


def test_update_recalculates_and_delete(client, user):
    act = add_activity(client, user["headers"], "car", 10, "km", fuel_type="petrol")
    resp = client.patch(f"/api/activities/{act['id']}", headers=user["headers"], json={"quantity": 20})
    assert resp.status_code == 200
    assert resp.json()["emission"]["co2e_kg"] == pytest.approx(2 * act["emission"]["co2e_kg"])
    resp = client.patch(f"/api/activities/{act['id']}", headers=user["headers"], json={"details": {"fuel_type": "electric"}})
    assert resp.json()["emission"]["factor_key"] == "transport.car.electric"
    assert client.delete(f"/api/activities/{act['id']}", headers=user["headers"]).status_code == 204
    assert client.get(f"/api/activities/{act['id']}", headers=user["headers"]).status_code == 404


def test_list_pagination_filter_sort(client, user):
    for i in range(5):
        add_activity(client, user["headers"], "car", 10 + i, "km", days_ago=i, fuel_type="petrol")
    add_activity(client, user["headers"], "meal", 1, "serving", meal_type="vegan")
    page = client.get("/api/activities?page=1&page_size=2", headers=user["headers"]).json()
    assert page["total"] == 6 and page["pages"] == 3 and len(page["items"]) == 2
    food = client.get("/api/activities?category=food", headers=user["headers"]).json()
    assert food["total"] == 1
    by_kg = client.get("/api/activities?sort=co2e_kg&order=desc&category=transport", headers=user["headers"]).json()["items"]
    kgs = [a["emission"]["co2e_kg"] for a in by_kg]
    assert kgs == sorted(kgs, reverse=True)


def test_user_data_isolation(client, user, other_user):
    act = add_activity(client, user["headers"], "car", 100, "km", fuel_type="petrol")
    h2 = other_user["headers"]
    # Other user cannot read, modify or delete it, and doesn't see it in lists or analytics.
    assert client.get(f"/api/activities/{act['id']}", headers=h2).status_code == 404
    assert client.patch(f"/api/activities/{act['id']}", headers=h2, json={"quantity": 1}).status_code == 404
    assert client.delete(f"/api/activities/{act['id']}", headers=h2).status_code == 404
    assert client.get("/api/activities", headers=h2).json()["total"] == 0
    assert client.get("/api/dashboard/summary", headers=h2).json()["totals"]["total_kg"] == 0
    # Owner still has it.
    assert client.get(f"/api/activities/{act['id']}", headers=user["headers"]).status_code == 200


def test_cross_user_goal_conversation_and_recommendation_access(client, user, other_user):
    add_activity(client, user["headers"], "car", 300, "km", fuel_type="petrol")
    goal = client.post(
        "/api/goals",
        headers=user["headers"],
        json={"title": "Drive less", "target_reduction_pct": 10, "deadline": (date.today() + timedelta(days=60)).isoformat()},
    ).json()
    conv = client.post("/api/assistant/conversations", headers=user["headers"], json={}).json()
    recs = client.post("/api/recommendations/refresh", headers=user["headers"]).json()
    assert recs, "car activity should produce recommendations"
    h2 = other_user["headers"]
    assert client.get(f"/api/goals/{goal['id']}", headers=h2).status_code == 404
    assert client.delete(f"/api/goals/{goal['id']}", headers=h2).status_code == 404
    assert client.get(f"/api/assistant/conversations/{conv['id']}", headers=h2).status_code == 404
    assert (
        client.post(f"/api/assistant/conversations/{conv['id']}/messages", headers=h2, json={"question": "hello there"}).status_code == 404
    )
    assert client.patch(f"/api/recommendations/{recs[0]['id']}", headers=h2, json={"status": "dismissed"}).status_code == 404


def test_activity_triggers_analytics_pipeline(client, user):
    """Creating an activity runs the background refresh: recommendations, insights and achievements."""
    add_activity(client, user["headers"], "car", 120, "km", fuel_type="petrol")
    insights = client.get("/api/insights", headers=user["headers"]).json()
    assert any(i["insight_type"] == "largest_source" for i in insights)
    achievements = {a["code"]: a["achieved"] for a in client.get("/api/achievements", headers=user["headers"]).json()}
    assert achievements["first_activity"] is True


def test_activity_types_catalogue(client):
    types = client.get("/api/activities/types").json()
    keys = {t["key"] for t in types}
    assert {"car", "flight", "electricity", "meal", "waste", "purchase"} <= keys
    car = next(t for t in types if t["key"] == "car")
    assert "km" in car["units"] and any(f["name"] == "fuel_type" for f in car["fields"])
