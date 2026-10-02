import pytest
from sqlalchemy import select

from app.ai import assistant as assistant_module
from app.ai.context_builder import detect_intents, parse_levers
from app.ai.providers import Completion, ProviderError
from app.ai.validation import validate_numbers
from app.models import EmissionFactor, EmissionRecord, User
from tests.conftest import add_activity


def _conv(client, h):
    return client.post("/api/assistant/conversations", headers=h, json={}).json()["id"]


def _ask(client, h, conv, q):
    resp = client.post(f"/api/assistant/conversations/{conv}/messages", headers=h, json={"question": q})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_validation_flags_invented_numbers():
    facts = {"last_30_days": {"total_kg": 453.4, "share_pct": {"transport": 48.8}}}
    ok = validate_numbers("You emitted 453.4 kg, transport was 49% of it (0.45 t).", facts)
    assert ok["status"] == "verified" and ok["numbers_checked"] == 3
    bad = validate_numbers("You could save 812 kg per year.", facts)
    assert bad["status"] == "flagged" and bad["unverified"] == ["812 kg"]


def test_intent_and_lever_parsing():
    assert "what_if" in detect_intents("What would happen if I reduced flights by 30%?")
    levers = parse_levers("what if I cut flights by 30%")
    assert levers.flight_reduction_pct == 30 and levers.car_reduction_pct == 0
    assert parse_levers("what if I bought an electric car").ev_adoption_pct == 50
    assert parse_levers("what if the weather changes") is None


def test_demo_mode_answer_uses_real_data(client, user):
    h = user["headers"]
    add_activity(client, h, "car", 200, "km", fuel_type="petrol")
    status = client.get("/api/assistant/status", headers=h).json()
    assert status["mode"] == "demo"
    conv = _conv(client, h)
    msg = _ask(client, h, conv, "What is causing most of my emissions?")
    total = client.get("/api/dashboard/summary", headers=h).json()["totals"]["total_kg"]
    assert msg["mode"] == "demo"
    assert f"{round(total, 1)} kg" in msg["content"]
    assert "transport" in msg["content"]
    assert msg["validation"]["status"] == "verified"
    assert msg["context_used"]["facts"]["last_30_days"]["total_kg"] == pytest.approx(total, abs=0.05)
    detail = client.get(f"/api/assistant/conversations/{conv}", headers=h).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]


def test_what_if_answer_uses_scenario_engine(client, user):
    h = user["headers"]
    for d in range(15):
        add_activity(client, h, "car", 40, "km", days_ago=d, fuel_type="petrol")
    msg = _ask(client, h, _conv(client, h), "What would happen if I drove 50% less?")
    scenario = msg["context_used"]["facts"]["scenario"]
    assert scenario["reduction_pct"] == pytest.approx(50, abs=0.1)
    assert str(scenario["reduction_monthly_kg"]) in msg["content"]


class _FakeProvider:
    def __init__(self, reply: str | None = None, error: bool = False):
        self.reply, self.error, self.calls = reply, error, []

    def complete(self, system, messages, max_tokens=2000):
        self.calls.append((system, messages))
        if self.error:
            raise ProviderError("boom")
        return Completion(text=self.reply, model="fake-model")


def test_llm_receives_backend_facts_and_is_validated(client, user, monkeypatch):
    h = user["headers"]
    add_activity(client, h, "car", 100, "km", fuel_type="petrol")
    total = client.get("/api/dashboard/summary", headers=h).json()["totals"]["total_kg"]
    fake = _FakeProvider(reply=f"You tracked {round(total, 1)} kg. Cutting it could save 9999 kg.")
    monkeypatch.setattr(assistant_module, "get_provider", lambda settings: fake)
    msg = _ask(client, h, _conv(client, h), "Explain my carbon footprint")
    system, messages = fake.calls[0]
    assert "Never calculate" in system
    assert "FACTS" in messages[-1]["content"] and str(round(total, 1)) in messages[-1]["content"]
    assert msg["mode"] == "llm" and msg["model"] == "fake-model"
    assert msg["validation"]["unverified"] == ["9999 kg"]
    assert "could not be matched" in msg["content"]


def test_provider_failure_falls_back_to_demo(client, user, monkeypatch):
    h = user["headers"]
    add_activity(client, h, "car", 100, "km", fuel_type="petrol")
    monkeypatch.setattr(assistant_module, "get_provider", lambda settings: _FakeProvider(error=True))
    msg = _ask(client, h, _conv(client, h), "How can I reduce my transport footprint?")
    assert msg["mode"] == "demo"
    assert "unavailable" in msg["content"]


def test_factor_admin_requires_admin_role(client, user):
    payload = {
        "key": "transport.scooter.electric",
        "category": "transport",
        "name": "E-scooter",
        "unit": "km",
        "co2e_per_unit": 0.02,
        "source": "Test source",
        "change_reason": "testing",
    }
    assert client.post("/api/emission-factors", headers=user["headers"], json=payload).status_code == 403
    factors = client.get("/api/emission-factors?category=flights", headers=user["headers"]).json()
    assert factors and all(f["category"] == "flights" for f in factors)


def test_admin_factor_update_is_versioned_and_records_stay_traceable(client, user, db):
    h = user["headers"]
    act = add_activity(client, h, "car", 100, "km", fuel_type="petrol")
    u = db.get(User, __import__("uuid").UUID(user["user"]["id"]))
    u.role = "admin"
    db.commit()

    old = db.scalar(select(EmissionFactor).where(EmissionFactor.key == "transport.car.petrol", EmissionFactor.is_active.is_(True)))
    resp = client.put(f"/api/emission-factors/{old.id}", headers=h, json={"co2e_per_unit": 0.2, "change_reason": "Updated dataset"})
    assert resp.status_code == 200
    new = resp.json()
    assert new["version"] == old.version + 1 and new["co2e_per_unit"] == 0.2
    history = client.get(f"/api/emission-factors/{new['id']}/history", headers=h).json()
    assert [f["version"] for f in history] == [2, 1] and history[1]["is_active"] is False

    # The earlier record still points at version 1; new activities use version 2.
    db.expire_all()
    rec = db.scalar(select(EmissionRecord).where(EmissionRecord.activity_id == __import__("uuid").UUID(act["id"])))
    assert str(rec.emission_factor_id) == str(old.id)
    act2 = add_activity(client, h, "car", 100, "km", fuel_type="petrol")
    assert act2["emission"]["co2e_kg"] == pytest.approx(20.0)
    assert (
        client.put(f"/api/emission-factors/{old.id}", headers=h, json={"co2e_per_unit": 0.3, "change_reason": "x" * 3}).status_code == 409
    )


def test_lever_parsing_variants():
    assert parse_levers("what if I drove 30% less").car_reduction_pct == 30
    ev = parse_levers("what if I switched to an electric car")
    assert ev.ev_adoption_pct == 50 and ev.car_reduction_pct == 0 and ev.electricity_reduction_pct == 0
    assert parse_levers("what if I started recycling more").recycling_improvement_pct == 50


def test_why_change_intent_variants():
    for q in ("Why did my emissions change this month?", "Why did my footprint increase?", "why have emissions dropped"):
        assert "why_change" in detect_intents(q), q
