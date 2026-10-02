from datetime import date, timedelta

import pytest

from tests.conftest import add_activity, register


def test_dashboard_totals_categories_and_comparison(client, user):
    h = user["headers"]
    car = add_activity(client, h, "car", 100, "km", days_ago=1, fuel_type="petrol")
    meal = add_activity(client, h, "meal", 2, "serving", days_ago=2, meal_type="chicken")
    old = add_activity(client, h, "car", 50, "km", days_ago=40, fuel_type="petrol")  # previous period
    d = client.get("/api/dashboard/summary?range=30d", headers=h).json()
    expected = car["emission"]["co2e_kg"] + meal["emission"]["co2e_kg"]
    assert d["totals"]["total_kg"] == pytest.approx(expected, abs=1e-3)
    assert d["totals"]["previous_total_kg"] == pytest.approx(old["emission"]["co2e_kg"], abs=1e-3)
    assert d["totals"]["change_pct"] == pytest.approx(100 * (expected - old["emission"]["co2e_kg"]) / old["emission"]["co2e_kg"], abs=0.1)
    cats = {c["category"]: c for c in d["categories"]}
    assert cats["transport"]["share_pct"] == pytest.approx(100 * car["emission"]["co2e_kg"] / expected, abs=0.1)
    assert d["totals"]["activity_count"] == 2
    assert len(d["timeline"]) == 30
    assert sum(p["total_kg"] for p in d["timeline"]) == pytest.approx(expected, abs=1e-2)


def test_custom_range_and_validation(client, user):
    h = user["headers"]
    add_activity(client, h, "car", 10, "km", days_ago=5, fuel_type="petrol")
    start = (date.today() - timedelta(days=6)).isoformat()
    end = (date.today() - timedelta(days=4)).isoformat()
    d = client.get(f"/api/dashboard/summary?range=custom&start={start}&end={end}", headers=h).json()
    assert d["range"]["days"] == 3 and d["totals"]["total_kg"] > 0
    assert client.get("/api/dashboard/summary?range=custom", headers=h).status_code == 422


def test_timeseries_breakdown_monthly(client, user):
    h = user["headers"]
    add_activity(client, h, "car", 10, "km", days_ago=3, fuel_type="petrol")
    add_activity(client, h, "electricity", 100, "kWh", days_ago=3, source="grid")
    ts = client.get("/api/emissions/timeseries?range=7d&category=energy", headers=h).json()
    assert ts["category"] == "energy" and len(ts["points"]) == 7
    bd = client.get("/api/emissions/breakdown?range=30d", headers=h).json()
    assert {b["activity_type"] for b in bd} == {"car", "electricity"}
    assert sum(b["share_pct"] for b in bd) == pytest.approx(100, abs=0.2)
    monthly = client.get("/api/emissions/monthly?months=3", headers=h).json()
    assert len(monthly) == 3


def test_goal_progress(client, user):
    h = user["headers"]
    for d in range(10):
        add_activity(client, h, "car", 20, "km", days_ago=d, fuel_type="petrol")
    resp = client.post(
        "/api/goals",
        headers=h,
        json={
            "title": "Cut 20%",
            "target_reduction_pct": 20,
            "baseline_monthly_kg": 200,
            "deadline": (date.today() + timedelta(days=90)).isoformat(),
        },
    )
    assert resp.status_code == 201
    g = resp.json()
    assert g["progress"]["target_monthly_kg"] == pytest.approx(160)
    assert g["status"] == "active"
    # Default baseline from tracked data when not provided.
    resp = client.post(
        "/api/goals",
        headers=h,
        json={
            "title": "Transport",
            "category": "transport",
            "target_reduction_pct": 10,
            "deadline": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    assert resp.json()["baseline_monthly_kg"] > 0
    goals = client.get("/api/goals", headers=h).json()
    assert len(goals) == 2
    bad = client.post(
        "/api/goals",
        headers=h,
        json={"title": "Bad", "target_reduction_pct": 10, "deadline": (date.today() - timedelta(days=1)).isoformat()},
    )
    assert bad.status_code == 422


def test_goal_without_data_requires_baseline(client, user):
    resp = client.post(
        "/api/goals",
        headers=user["headers"],
        json={"title": "Empty", "target_reduction_pct": 10, "deadline": (date.today() + timedelta(days=30)).isoformat()},
    )
    assert resp.status_code == 422


def test_onboarding_and_baseline(client, user):
    h = user["headers"]
    resp = client.post(
        "/api/profile/onboarding",
        headers=h,
        json={
            "country": "gb",
            "household_size": 2,
            "vehicle_type": "hybrid",
            "weekly_car_km": 120,
            "monthly_electricity_kwh": 300,
            "diet_type": "mixed",
            "organization_name": "Acme Ltd",
            "organization_industry": "Software",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["onboarding_completed"] is True
    assert resp.json()["organization"]["name"] == "Acme Ltd"
    assert client.get("/api/profile", headers=h).json()["country"] == "GB"
    base = client.get("/api/profile/baseline", headers=h).json()
    assert base["basis"] == "onboarding_profile" and base["monthly_total_kg"] > 0
    # Scenario simulator works from onboarding answers before any activity exists.
    assert client.post("/api/scenarios/simulate", headers=h, json={"car_reduction_pct": 50}).status_code == 200


def test_preferences(client, user):
    h = user["headers"]
    assert client.get("/api/profile/preferences", headers=h).json()["distance_unit"] == "km"
    resp = client.put("/api/profile/preferences", headers=h, json={"distance_unit": "mi", "default_range": "90d"})
    assert resp.json() == {"distance_unit": "mi", "default_range": "90d", "monthly_budget_kg": None}


def test_organization_mode(client, user):
    owner = user["headers"]
    org = client.post("/api/organizations", headers=owner, json={"name": "GreenCo", "country": "GB"}).json()
    assert org["join_code"]
    member = register(client)
    joined = client.post("/api/organizations/join", headers=member["headers"], json={"join_code": org["join_code"]})
    assert joined.status_code == 200 and joined.json()["join_code"] is None  # members don't see the code

    org_act = client.post(
        "/api/activities",
        headers=member["headers"],
        json={
            "activity_type": "hotel_stay",
            "quantity": 2,
            "unit": "room_night",
            "occurred_on": date.today().isoformat(),
            "details": {},
            "for_organization": True,
        },
    ).json()
    add_activity(client, member["headers"], "car", 10, "km", fuel_type="petrol")  # personal, must not count for org
    dash = client.get("/api/organizations/me/dashboard?range=30d", headers=owner).json()
    assert dash["totals"]["total_kg"] == pytest.approx(org_act["emission"]["co2e_kg"], abs=1e-3)
    members = client.get("/api/organizations/me/members", headers=owner).json()
    assert len(members) == 2
    # Personal dashboard of the member excludes the org activity.
    personal = client.get("/api/dashboard/summary", headers=member["headers"]).json()
    assert personal["totals"]["activity_count"] == 1

    outsider = register(client)
    assert client.get("/api/organizations/me/dashboard", headers=outsider["headers"]).status_code == 404
    assert (
        client.post(
            "/api/activities",
            headers=outsider["headers"],
            json={
                "activity_type": "hotel_stay",
                "quantity": 1,
                "unit": "room_night",
                "occurred_on": date.today().isoformat(),
                "details": {},
                "for_organization": True,
            },
        ).status_code
        == 403
    )
    assert client.post("/api/organizations/leave", headers=owner).status_code == 400  # owner with members


def test_insights_reflect_data(client, user):
    h = user["headers"]
    for d in range(3):
        add_activity(client, h, "car", 80, "km", days_ago=d, fuel_type="petrol")
    add_activity(client, h, "meal", 1, "serving", meal_type="vegan")
    insights = client.post("/api/insights/refresh", headers=h).json()
    largest = next(i for i in insights if i["insight_type"] == "largest_source")
    assert largest["category"] == "transport"
    dash = client.get("/api/dashboard/summary", headers=h).json()
    transport_share = next(c["share_pct"] for c in dash["categories"] if c["category"] == "transport")
    assert largest["metric_value"] == pytest.approx(transport_share, abs=0.1)
