# Madad (مدد) — Verified Medical Crowdfunding for Pakistan

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi) ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red) ![JWT](https://img.shields.io/badge/Auth-JWT%20%2B%20bcrypt-black) ![Tests](https://img.shields.io/badge/tests-45%20passed-brightgreen) ![License](https://img.shields.io/badge/license-MIT-blue)

**Madad** is a transparent, document-verified medical crowdfunding platform. Families raise PKR for cancer treatment, surgeries, thalassemia and dialysis care; donors give online with a public ledger so every rupee is traceable to a verified campaign.

> When a family in Pakistan gets a cancer or dialysis diagnosis, the first question after "how?" is "from where?" — treatment runs into lakhs, insurance covers almost nobody, and pleas for help travel by WhatsApp with zero verification. Madad sits in the middle: campaigns go live only after an admin verifies them, every donation lands on a public ledger, and a campaign closes the moment its goal is met.

## Features

- **Verified campaigns only** — every campaign is reviewed by an admin before going public; rejected campaigns tell the owner exactly why.
- **Transparent public ledger** — confirmed donations are public (donor can stay anonymous), each with a unique receipt reference.
- **Smart donation lifecycle** — donors pledge, owners confirm receipt, raised amount updates atomically, and hitting 100% auto-closes the campaign (no endless running totals).
- **No self-funding** — you cannot donate to your own campaign; over-goal donations are rejected.
- **Campaign updates** — owners post progress (receipts, doctor notes) that donors see on the campaign page.
- **Three roles** — donor/fundraiser, campaign owner dashboard (pledges to confirm, receipts), admin panel (verify/reject, suspend users, stats).
- **Real security** — JWT (24h) + bcrypt(12), SlowAPI rate limits on register/login, scoped queries (foreign data returns 404), Pydantic v2 validation everywhere.
- **Mobile-first dark SPA** — zero build step, works on a Rs. 30k Android phone.

## Tech stack

| Layer | Choice |
|---|---|
| API | FastAPI 0.115 · Python 3.11 · Pydantic v2 |
| ORM / DB | SQLAlchemy 2.0 · SQLite WAL (dev/test) · PostgreSQL 16 (Docker/prod) |
| Auth | JWT HS256 · bcrypt · SlowAPI rate limits |
| Frontend | Vanilla JS SPA · mobile-first dark UI · no build step |
| Infra | Docker · docker-compose · Vercel-ready |

## Screenshots

Home · Explore · Campaign detail · Donate modal · Dashboard · Admin panel — capture and add below.

## Quick start (local)

```bash
git clone https://github.com/mohdabrarbaloch-arch/day-27-madad.git
cd day-27-madad
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/seed.py          # admin + 3 demo campaigns
uvicorn app.main:app --reload   # http://localhost:8000
```

### Docker

```bash
docker compose up --build       # API on :8000 + PostgreSQL 16
```

## Demo logins (seeded)

| Role | Email | Password |
|---|---|---|
| Admin | `admin@madad.pk` | `admin12345` |
| Campaign owner | `fatima@example.com` | `demo12345` |
| Donor (register fresh) | — | — |

## Docs

- [Setup guide](docs/setup.md)
- [Usage guide](docs/usage.md)
- [API reference](docs/api.md)
- [Architecture](ARCHITECTURE.md)

## Tests

```bash
pytest -q        # 45 tests
ruff check .     # clean
black --check .  # clean
```

Coverage: auth (register/login/me, suspended accounts, rate limiting 429), campaign lifecycle (pending → verified → closed, reject-with-reason, scoped updates, slug uniqueness), donation lifecycle (pledge → confirm → raised credit → auto-close at 100%, self-donation 409, over-goal 400, donor cancel), admin (role guards, verify/reject queue, suspend/unsuspend), public stats.

## License

[MIT](LICENSE)
