# Deployment

## Local — Docker Compose (recommended)

```bash
cp .env.example .env        # optional: change passwords/secret, add AI key
docker compose up --build
```

| Service | URL | Notes |
|---|---|---|
| frontend (nginx) | http://localhost:8080 | Serves the SPA and proxies `/api` to the backend |
| backend (FastAPI) | http://localhost:8000/docs | Runs `alembic upgrade head` and `python -m app.seed` on start |
| postgres | internal only | Data in the `pgdata` volume |

Demo login (when `SEED_DEMO_DATA=true`, the compose default): `demo@carbonnavigator.app` / `DemoPass123!`.
All three services have health checks; the frontend waits for a healthy backend, which waits for a healthy database.
`docker compose down -v` removes the database volume.

## Backend — Render

`render.yaml` is a Blueprint that provisions a PostgreSQL database and the Dockerised API:

1. Push the repository to GitHub, then in Render choose **New → Blueprint** and select the repo.
2. Render creates `carbon-footprint-navigator-db` and `carbon-footprint-navigator-api`. `DATABASE_URL` is wired from the database
   (`postgres://…` URLs are normalised to the psycopg driver automatically) and `JWT_SECRET` is generated.
3. Set `CORS_ORIGINS` to your Vercel URL (comma-separate multiple origins). Optionally set `AI_PROVIDER=anthropic` and `AI_API_KEY`.
4. The container listens on Render's `$PORT`; health checks hit `/api/health`. Migrations and seeding run on every start (idempotent).
   Set `SEED_DEMO_DATA=false` if you don't want the demo account in production.

## Frontend — Vercel

1. Import the repository in Vercel and set **Root Directory** to `frontend` (framework preset: Vite).
2. Environment variable: `VITE_API_URL=https://<your-render-service>.onrender.com` (build-time).
3. `frontend/vercel.json` rewrites client-side routes to `index.html` and sets long-lived caching for hashed assets.

## Environment variables

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | backend | local dev URL | PostgreSQL connection string |
| `JWT_SECRET` | backend | dev placeholder (rejected in production) | JWT signing key, ≥ 32 chars |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | backend | 720 | Token lifetime |
| `CORS_ORIGINS` | backend | localhost origins | Comma-separated allowed origins |
| `ENVIRONMENT` | backend | development | `production` enables secret checks |
| `AI_PROVIDER` | backend | demo | `anthropic` or `demo` |
| `AI_API_KEY` | backend | – | Anthropic API key (server only) |
| `AI_MODEL` | backend | claude-opus-5-5 | Model id |
| `SEED_EMISSION_FACTORS` / `SEED_DEMO_DATA` | backend | true / false | Seeding on start |
| `DEMO_USER_EMAIL` / `DEMO_USER_PASSWORD` | backend | demo values | Demo account |
| `RATE_LIMIT_AUTH_PER_MINUTE` / `RATE_LIMIT_ASSISTANT_PER_MINUTE` | backend | 10 / 12 | Rate limits |
| `PORT` | backend | 8000 | Listen port (Render sets it) |
| `VITE_API_URL` | frontend (build) | empty | Backend origin; empty = same-origin `/api` |

## Administrator

```bash
# inside the backend container or venv; password read from ADMIN_PASSWORD or prompted
docker compose exec backend python -m app.scripts.create_admin --email you@example.com
```
Admins see **Settings → Manage emission factors**.
