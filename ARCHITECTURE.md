# Madad (مدد) — Transparent Medical Crowdfunding for Pakistan

> **Madad** is a verified medical crowdfunding platform. Families raise PKR for surgeries, cancer treatment, thalassemia and dialysis care; donors give online with a public ledger so every rupee is traceable to a verified campaign.

---

## Why it exists

In Pakistan, when a family gets a cancer or dialysis diagnosis, the first question after "how?" is "from where?" — treatment costs run into lakhs, insurance covers almost nobody, and hospital social workers hand out bank account numbers that people share on WhatsApp with zero verification. Donors want to help but are scared of fraud; families need help but have no trusted channel. Madad sits in the middle: campaigns only go live after an admin verifies the supporting documents, every donation appears on a public ledger, and a campaign closes the moment its goal is met — no endless running totals.

## System diagram

```text
┌────────────────────────────── Client ─────────────────────────────┐
│  SPA (vanilla JS, mobile-first dark UI, zero build step)           │
│  home · explore · campaign detail · donate · dashboard · admin     │
└───────────────▲───────────────────────────────▲───────────────────┘
                │ REST (JSON, Bearer JWT)        │
┌───────────────┴───────────────────────────────┴───────────────────┐
│  FastAPI app (app/main.py)                                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────┐  │
│  │ auth       │ │ campaigns  │ │ donations  │ │ admin          │  │
│  │ register/  │ │ feed/detail│ │ pledge →   │ │ verify/reject, │  │
│  │ login/me   │ │ create/    │ │ confirm by │ │ suspend, stats │  │
│  │ (rate-lim) │ │ updates    │ │ owner      │ │                │  │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └───────┬────────┘  │
│        └──────────────┴───────┬──────┴────────────────┘            │
│                    Security layer:                                │
│   JWT (HS256, 24h) · bcrypt(12) · SlowAPI rate limits ·           │
│   CORS allow-list · Pydantic v2 validation · scoped queries       │
├─────────────────────────────────┬──────────────────────────────────┤
│  SQLAlchemy 2.0 ORM (typed Mapped models)                          │
│  SQLite WAL (dev/test) · PostgreSQL 16 (docker-compose / prod)    │
└─────────────────────────────────┬──────────────────────────────────┘
            Users · Campaigns · CampaignUpdates · Donations
```

## Domain model

| Entity | Purpose |
|---|---|
| `User` | email/password (bcrypt), role `user` \| `admin`, suspend flag |
| `Campaign` | owner, title, story, category, target (PKR), `amount_raised`, status machine |
| `CampaignUpdate` | owner's progress posts on a live campaign |
| `Donation` | pledge → confirm lifecycle, public ledger, receipt reference |

### Campaign status machine

```text
create ──▶ pending ──verify(admin)──▶ verified (live, public)
              │                          │
              │ reject(admin)            │  close (goal reached / owner / admin)
              ▼                          ▼
          rejected                    closed
```

- Only `verified` campaigns are listed publicly or accept donations.
- Owners see their `pending`/`rejected` campaigns in their dashboard with reasons.
- Confirmations update `amount_raised` inside one DB transaction; when raised reaches target the campaign auto-closes as **goal reached**.

### Donation lifecycle

```text
donor pledges ──▶ pledged ──owner confirms receipt──▶ confirmed ──(+raised)
donor cancels before confirmation ──▶ cancelled
```

- Donors must be signed in (receipts and a real ledger) and may choose anonymous display.
- A donor **cannot** donate to their own campaign (409) — self-funding is blocked at the API.
- Confirmation happens **only** through the campaign owner (they hold the bank account), never by the donor — and only an owner/admin can confirm.
- Donations are capped at the remaining goal; over-target pledges are rejected.

## API surface (summary)

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/register` · `POST /api/auth/login` (rate-limited) · `GET /api/auth/me` |
| Public | `GET /api/public/stats` · `GET /api/campaigns` (filters, search, pagination) · `GET /api/campaigns/{slug}` |
| Campaigns | `POST /api/campaigns` · `GET /api/my/campaigns` · `POST /api/campaigns/{slug}/updates` · `POST /api/campaigns/{slug}/close` |
| Donations | `POST /api/campaigns/{slug}/donate` · `GET /api/my/donations` · `POST /api/donations/{id}/cancel` · `POST /api/campaigns/{slug}/donations/{id}/confirm` · `GET /api/campaigns/{slug}/donations` |
| Admin | `GET /api/admin/campaigns` · `POST /api/admin/campaigns/{id}/verify|reject|close` · `POST /api/admin/users/{id}/suspend|unsuspend` · `GET /api/admin/stats` |

Full reference with request/response examples: `docs/api.md`.

## Security

- **Passwords** — bcrypt, 12 rounds. Never stored or logged in plain text.
- **Auth** — JWT HS256, 24-hour expiry, role claim; `get_current_user` / `require_admin` dependencies on every protected route.
- **Rate limiting** — SlowAPI: register 5/min per IP, login 10/min, donate 20/min. 429s are tested.
- **Scoped queries** — campaign updates, donation confirmations and admin queues always filter by current user; foreign resources return 404 (no existence leak).
- **Validation** — Pydantic v2 models constrain every payload: title 10–100 chars, story 50–10,000, target PKR 1,000–100M, donations PKR 100–2M.
- **Self-donation** — API-level 409 for owner donating to own campaign.
- **Secrets** — everything in `.env` (`JWT_SECRET`, `DATABASE_URL`, admin seed creds); `.env.example` documents every variable; no key in the client.
- **CORS** — allow-list from env (`CORS_ORIGINS`), defaults to localhost in dev.

## Concurrency

Confirming a donation and crediting `amount_raised` happens in **one transaction** (`db.commit()` after guarded update) so two simultaneous confirmations cannot both pass the remaining-goal check. SQLite uses WAL; production should run PostgreSQL where the same guarded update is row-locked by the DB. Slug uniqueness is enforced with a unique index + random-suffix retry on collision.

## Scaling notes

- Stateless API → horizontally scalable behind a load balancer; JWT means no session store.
- Move `DATABASE_URL` to PostgreSQL 16 (provided in `docker-compose.yml`); add `pgbouncer` when connections grow.
- Static SPA can be served by any CDN / Vercel; API as serverless via `api/index.py` (uses `/tmp` SQLite in serverless mode, or managed Postgres in production).
- Background jobs later: receipt emails, expiry sweeps for stale `pledged` donations.
- Search today is SQL `LIKE` on title/story; swap to Postgres FTS or Meilisearch at scale.

## Tech stack

| Layer | Choice |
|---|---|
| API | FastAPI 0.115 · Python 3.11 · Pydantic v2 |
| ORM/DB | SQLAlchemy 2.0 (typed) · SQLite WAL (dev/test) · PostgreSQL 16 (prod/docker) |
| Auth | JWT HS256 · bcrypt · SlowAPI |
| Frontend | Vanilla JS SPA · mobile-first dark · zero build step |
| Infra | Docker · docker-compose · Vercel-ready (`vercel.json` + `api/index.py`) |
| QA | pytest (TestClient) · ruff · black |

## Run locally

```bash
cp .env.example .env
pip install -r requirements.txt
python scripts/seed.py          # admin + demo campaigns
uvicorn app.main:app --reload   # http://localhost:8000
```

Or with Docker:

```bash
docker compose up --build       # API on :8000, Postgres on :5432
```
