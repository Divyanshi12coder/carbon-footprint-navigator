# API

Interactive documentation: **`/docs`** (Swagger UI) and **`/redoc`**; schema at `/openapi.json`.
Authenticate in Swagger with *Authorize → Bearer `<access_token>`* from `/api/auth/login`.

Conventions: JSON bodies validated by Pydantic (422 with field-level messages), `401` for missing/invalid/expired/revoked tokens,
`403` for role violations, `404` for resources that don't exist **or belong to someone else**, `409` for conflicts, `429` with
`Retry-After` when rate-limited.

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/health` | – | Liveness + DB check (503 if DB down) |
| POST | `/api/auth/register` | – | Create account → JWT (rate limited) |
| POST | `/api/auth/login` | – | Login → JWT (rate limited) |
| GET | `/api/auth/me` | ✓ | Current user |
| POST | `/api/auth/logout` | ✓ | Revoke all tokens (token-version bump) |
| POST | `/api/auth/change-password` | ✓ | Change password, revoke other sessions |
| GET/PUT | `/api/profile` | ✓ | Onboarding profile |
| POST | `/api/profile/onboarding` | ✓ | Save profile, mark onboarded, optionally create organization |
| GET | `/api/profile/baseline` | ✓ | Footprint estimate from onboarding answers |
| GET/PUT | `/api/profile/preferences` | ✓ | Distance unit, default range |
| GET | `/api/activities/types` | – | Activity catalogue (drives forms) |
| GET | `/api/activities/airports` | – | Airports available for distance calculation |
| POST | `/api/activities/preview` | ✓ | Calculate without saving |
| GET | `/api/activities` | ✓ | List — `page`, `page_size`, `category`, `activity_type`, `date_from`, `date_to`, `search`, `scope`, `sort`, `order` |
| POST | `/api/activities` | ✓ | Create (calculates + stores record, triggers analytics refresh) |
| GET/PATCH/DELETE | `/api/activities/{id}` | ✓ | Read / recalculate / delete own activity |
| GET | `/api/dashboard/summary` | ✓ | KPIs, comparison, categories, timeline, top activities — `range=7d|30d|90d|180d|365d|custom&start&end` |
| GET | `/api/emissions/timeseries` | ✓ | Daily/weekly/monthly series with 7-day rolling mean, optional `category` |
| GET | `/api/emissions/breakdown` | ✓ | Per activity type/factor: count, quantity, kg, share |
| GET | `/api/emissions/monthly` | ✓ | Calendar-month totals by category |
| GET | `/api/emission-factors` | – | Active factors (`category`, `region`, `search`; admins may add `include_inactive`) |
| GET | `/api/emission-factors/categories` | – | Category list |
| GET | `/api/emission-factors/{id}` / `{id}/history` | – | Factor / version history |
| POST | `/api/emission-factors` | admin | Create factor |
| PUT | `/api/emission-factors/{id}` | admin | New version (old retired; requires `change_reason`) |
| DELETE | `/api/emission-factors/{id}` | admin | Deactivate (soft) |
| GET | `/api/forecast?horizon=7..90` | ✓ | Model-selected forecast with intervals and metrics |
| GET | `/api/anomalies` | ✓ | Weekly robust-z and Isolation Forest anomalies |
| GET / POST | `/api/insights`, `/api/insights/refresh` | ✓ | Generated insights |
| GET / POST | `/api/recommendations`, `/refresh` | ✓ | Explainable recommendations |
| PATCH | `/api/recommendations/{id}` | ✓ | Set status open/accepted/dismissed/completed |
| GET | `/api/scenarios/baseline` | ✓ | Monthly behaviour profile used by scenarios |
| POST | `/api/scenarios/simulate` | ✓ | Apply levers → current vs scenario (409 if no data) |
| GET/POST | `/api/goals` | ✓ | List (with progress) / create (baseline defaults to last 30 days) |
| GET/PATCH/DELETE | `/api/goals/{id}` | ✓ | Goal CRUD |
| GET | `/api/achievements` | ✓ | Achievement catalogue with earned state |
| GET | `/api/assistant/status` | ✓ | `llm` or `demo` mode + suggested questions |
| GET/POST | `/api/assistant/conversations` | ✓ | List / create |
| GET/DELETE | `/api/assistant/conversations/{id}` | ✓ | Conversation with messages / delete |
| POST | `/api/assistant/conversations/{id}/messages` | ✓ | Ask (rate limited); returns answer, mode, facts used, validation |
| POST | `/api/organizations`, `/join`, `/leave` | ✓ | Organization membership |
| GET | `/api/organizations/me`, `/me/members`, `/me/dashboard` | ✓ | Organization details, members, company dashboard |

## Example

```bash
TOKEN=$(curl -s localhost:8000/api/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"demo@carbonnavigator.app","password":"DemoPass123!"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s localhost:8000/api/activities -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"activity_type":"flight","occurred_on":"2026-09-30","details":{"origin":"LHR","destination":"BCN","cabin_class":"economy","round_trip":true}}'
# → emission.calculation_method:
#   "great-circle LHR->BCN 1,148 km x 1.08 routing uplift = 1,239.4 km x 1 passenger(s) x 2 leg(s)
#    = 2,478.8 passenger-km x 0.151 kg CO2e/passenger-km (short-haul) = 374.295 kg CO2e"
```
