# Carbon methodology

> Results are **estimates** derived from published average emission factors. They are suitable for
> understanding and reducing a footprint, not for audited or regulatory reporting.

## CO₂ vs CO₂e

CO₂e (carbon-dioxide equivalent) expresses several greenhouse gases (CO₂, CH₄, N₂O…) as the amount of CO₂ with the
same 100-year warming effect (GWP100). All values in the platform are **kg CO₂e**.

## The calculation

```
co2e_kg = normalized_quantity × factor_value
```

1. **Classification** — `app/carbon/catalog.py` declares each activity type (car, flight, electricity, meal, waste,
   purchase…), its category, accepted units, extra inputs and how those inputs resolve to a factor key
   (e.g. `car` + `fuel_type=diesel` → `transport.car.diesel`). This is deterministic rule-based classification; the frontend
   renders its forms from the same catalogue (`GET /api/activities/types`).
2. **Factor lookup** — `app/carbon/factors.py` loads the active factor for the key. Grid electricity is looked up for the
   user's country first and falls back to `GLOBAL` (confidence is downgraded and an assumption recorded).
3. **Normalisation** — `app/carbon/units.py` converts the input to the factor's unit (mi→km, therm/MJ/m³→kWh, lb→kg,
   gal→L, min→hour). Allocation is applied: car emissions divided by occupants; flights multiplied by passengers and legs.
4. **Result** — stored with the factor id, value, unit, source, region, a human-readable method string (e.g.
   `42 mi x 1.6093 = 67.5924 km x 0.17 kg CO2e/km = 11.491 kg CO2e`), assumptions and a confidence level.

### Flights

* Distance = great-circle distance between airport coordinates (bundled table of 71 major airports) × **1.08**
  routing uplift (DESNZ guidance). Unknown airports → enter the distance manually.
* Bands: < 500 km → domestic factor, < 3,700 km → short-haul, otherwise long-haul; cabin class selects the factor
  (substitutions, e.g. short-haul premium economy → economy factor, are recorded as assumptions).
* Factors include the radiative-forcing uplift for non-CO₂ effects.

### Food

* Per-serving factors = 120 g of the main food × mean kg CO₂e/kg from Poore & Nemecek (2018, via Our World in Data)
  + 0.35 kg CO₂e for sides. The derivation is stored in each factor's notes.
* Whole-day diet factors (meat-heavy … vegan) from Scarborough et al. (2014).

### Other categories

* Electricity: location-based grid intensity (Ember 2023 lifecycle values; US from EPA eGRID; GB from DESNZ).
  Renewable electricity uses a lifecycle estimate for a wind/solar mix (0.030 kg/kWh); market-based reporting would use 0.
* Heating: DESNZ natural gas (kWh), LPG and heating oil (litres).
* Waste: DESNZ factors for landfill, incineration with energy recovery, recycling and composting.
* Consumption: spend-based (USEEIO sector averages, low confidence) and product-based (manufacturer footprints, low confidence).
* Custom: users may supply their own factor; such records are always marked low confidence.

## The dataset

`backend/app/carbon/data/emission_factors.json` contains 75 factors (key, category, region, unit, value, source,
source URL, year, quality, notes). It is seeded idempotently into the `emission_factors` table and never overwrites edits.
Every factor is browsable on the public Methodology page and via `GET /api/emission-factors`.

**Values are approximations of the cited datasets**, rounded and in some cases simplified (e.g. a single average car
size). Before using the platform for formal reporting, replace them with the current edition of your chosen dataset —
administrators can update factors through the admin UI/API (versioned).

## Confidence (data quality)

| Level | Typical sources |
|---|---|
| high | Country grid factors, fuels, zero-emission active travel |
| medium | Vehicle and flight averages, food means, waste |
| low | Spend-based purchases, product footprints, user-supplied factors, region fallbacks (downgraded one level) |

## Onboarding estimate (cold start)

Before a user has ≥14 days and ≥5 tracked activities, behaviour-based features use an estimate from onboarding answers
(`app/carbon/behavior.py:onboarding_profile`). Assumptions are explicit and returned to the UI, e.g. one short-haul flight
= economy return of 2 × 1,100 km; household energy and waste divided by household size; recycling level mapped to a share.

## Behaviour profile

Scenarios and recommendations work on a *monthly behaviour profile*: per factor key, the monthly quantity and its factor.
Routine activities use the last 90 days; flights, purchases and hotel stays use up to 365 days so a single trip is not
extrapolated ×4.

## Limitations

* Only tracked or estimated activities are counted; public services, infrastructure and many supply chains are not.
* Averages hide variation (vehicle efficiency, load factors, farming practices, grid hour-by-hour intensity).
* Many factors come from UK datasets and are applied globally where no better open value is bundled.
* Recommendation savings are estimated individually and are not strictly additive.
