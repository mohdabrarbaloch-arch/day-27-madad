# Madad — Setup Guide

This guide covers local development, Docker, and production deployment notes.

## Prerequisites

- Python 3.11+
- (Docker path) Docker + Docker Compose

## 1. Local development (SQLite)

```bash
cd day-27-madad
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: set JWT_SECRET to a random string
python scripts/seed.py
uvicorn app.main:app --reload
```

Open http://localhost:8000 — the SPA is served from the same origin.

Seeded demo data:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@madad.pk` | `admin12345` |
| Owner | `fatima@example.com` | `demo12345` |
| Owner | `bilal@example.com` | `demo12345` |
| Owner | `sana@example.com` | `demo12345` |

## 2. Docker (PostgreSQL 16)

```bash
docker compose up --build
```

- API on http://localhost:8000
- Postgres on `db:5432` (volume `madad_pgdata` persists data)
- Set `JWT_SECRET` before first run or via `.env` (docker-compose reads it)
- Seed inside the container:

```bash
docker compose exec api python scripts/seed.py
```

## 3. Running tests

```bash
pytest -q
ruff check app tests api scripts
black --check app tests api scripts
```

Tests use an isolated temp SQLite DB — no `.env` changes needed.

## 4. Production notes

- Use PostgreSQL (managed RDS/Neon/Supabase) and set `DATABASE_URL` accordingly — the app uses `pool_pre_ping` and works with both sync drivers.
- `JWT_SECRET` must be a long random value: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `CORS_ORIGINS` should list your exact frontend origin(s), comma separated, not `*`.
- Change `ADMIN_SEED_*` before seeding in production.

## 5. Vercel (serverless)

The repo ships `vercel.json` + `api/index.py`. For a real deploy:

1. `vercel login` and link the project.
2. Add env vars in the Vercel dashboard (or `vercel env add`): `JWT_SECRET`, `CORS_ORIGINS`, `DATABASE_URL` (managed Postgres), `ADMIN_SEED_EMAIL`, `ADMIN_SEED_PASSWORD`.
3. `vercel --prod`. On serverless, SQLite is impractical (ephemeral `/tmp`), so point `DATABASE_URL` at a managed PostgreSQL instance; the schema auto-creates on cold start.
