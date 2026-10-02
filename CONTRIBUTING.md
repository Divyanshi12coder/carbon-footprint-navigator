# Contributing

1. Create a branch from `main`.
2. Backend: `cd backend && pip install -r requirements-dev.txt`, start PostgreSQL (`docker compose up postgres` or your own), then
   `ruff check app tests && ruff format --check app tests && pytest`. Tests need `TEST_DATABASE_URL` pointing at a disposable database
   (the test session drops and recreates its schema).
3. Model changes need a migration: `alembic revision --autogenerate -m "…"`, review it, and make sure `alembic check` passes.
4. Frontend: `cd frontend && npm ci && npm run typecheck && npm run lint && npm test && npm run build`.
5. New emission factors go in `backend/app/carbon/data/emission_factors.json` with a source, year, unit and quality — never hard-code
   factor values in code.
6. Open a pull request; CI runs lint, migrations, backend tests on PostgreSQL, frontend checks and a Docker Compose smoke test.
