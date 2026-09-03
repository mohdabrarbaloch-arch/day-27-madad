# Madad — API Reference

Base path: `/api` · Auth: `Authorization: Bearer <jwt>` · All bodies/responses JSON.

Rate limits (SlowAPI, per IP): register **5/min**, login **10/min**.

## Health & stats

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Liveness probe |
| GET | `/public/stats` | — | Total campaigns, verified count, raised PKR, donations, cities |

## Auth

### POST `/auth/register`
Body: `{"name", "email", "password" (min 8), "phone"?}` → **201** `{access_token, user}`. Duplicate email → 409.

### POST `/auth/login`
Body: `{"email", "password"}` → **200** `{access_token, user}`. Wrong creds → 401; suspended → 403.

### GET `/auth/me`
→ **200** current user. Invalid/missing token → 401.

## Campaigns

### GET `/campaigns`
Query: `category`, `city`, `q` (title/story search), `sort` (`recent|urgent|raised`), `limit` (≤50), `offset`. Returns verified campaigns only.

### GET `/campaigns/{slug}`
Full detail incl. story, owner name, progress, donor count. Non-verified/unknown → 404.

### GET `/campaigns/{slug}/updates`
Public list of owner updates (newest first).

### POST `/campaigns`  🔒
Body: `{title (10–150), story (50–10k), category ∈ [cancer, surgery, child-health, thalassemia, dialysis, accident, maternity, cardiac, other], city?, hospital?, target_amount (1k–100M)}` → **201** with `status: pending`.

### GET `/my/campaigns` 🔒
Owner's campaigns.

### POST `/campaigns/{slug}/updates` 🔒 owner
Body: `{body (10–5k)}` → **201**. Live campaign only.

### POST `/campaigns/{slug}/close` 🔒 owner
Closes a live campaign. → 200 with `status: closed`.

## Donations

### POST `/campaigns/{slug}/donate` 🔒
Body: `{amount (100–2M, ≤ remaining), message?, is_anonymous?}` → **201** `status: pledged`. Self-donation → 409; over-goal → 400.

### POST `/campaigns/{slug}/donations/{id}/confirm` 🔒 owner
Confirms a received transfer: credits `amount_raised`; auto-closes campaign at 100%. Donor/stranger → 403.

### POST `/donations/{id}/cancel` 🔒 donor
Cancels own unconfirmed pledge. Confirmed → 400; foreign id → 404.

### GET `/my/donations` 🔒
Donor's receipt history.

### GET `/campaigns/{slug}/donations?status_filter=confirmed|pledged|all`
Public ledger (default confirmed, newest 50).

### GET `/my/campaigns/{slug}/pledges` 🔒 owner
All pledges (incl. pending/cancelled) for the owner's confirmation workflow.

## Admin 🔒 role=admin

| Method | Path | Description |
|---|---|---|
| GET | `/admin/campaigns?status_filter=pending|verified|closed|rejected|all` | Review queue |
| POST | `/admin/campaigns/{id}/verify` | Pending → verified (live) |
| POST | `/admin/campaigns/{id}/reject` | Body `{reason ≥10 chars}` → rejected |
| POST | `/admin/campaigns/{id}/close` | Live → closed |
| POST | `/admin/users/{id}/suspend` \| `/unsuspend` | Ban / unban (admins can't be suspended) |
| GET | `/admin/users` | User list (role, suspension, campaign count) |
| GET | `/admin/stats` | Status breakdown + donation totals |

## Error format

```json
{ "detail": "human readable message" }
```

Status codes: `400` bad request · `401` unauthenticated · `403` forbidden · `404` not found (scoped) · `409` conflict · `422` validation · `429` rate limited.
