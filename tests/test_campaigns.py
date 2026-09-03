def test_create_campaign_pending(client, auth_headers):
    headers, user = auth_headers()
    r = client.post(
        "/api/campaigns",
        headers=headers,
        json={
            "title": "Help fund a heart surgery in Lahore",
            "story": "My father needs an urgent bypass surgery and the hospital has asked for "
            "a very large amount which we cannot arrange alone.",
            "category": "cardiac",
            "city": "Lahore",
            "hospital": "Punjab Institute of Cardiology",
            "target_amount": 1_000_000,
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert data["slug"].startswith("help-fund-a-heart")
    assert data["progress_percent"] == 0


def test_create_campaign_requires_auth(client):
    r = client.post(
        "/api/campaigns",
        json={
            "title": "No auth campaign title here",
            "story": "x" * 80,
            "category": "other",
            "target_amount": 5000,
        },
    )
    assert r.status_code == 401


def test_create_campaign_invalid_category(client, auth_headers):
    headers, _ = auth_headers()
    r = client.post(
        "/api/campaigns",
        headers=headers,
        json={
            "title": "This campaign uses a bad category name",
            "story": "x" * 80,
            "category": "vacation",
            "target_amount": 5000,
        },
    )
    assert r.status_code == 422


def test_create_campaign_validation_errors(client, auth_headers):
    headers, _ = auth_headers()
    # too-short title
    r = client.post(
        "/api/campaigns",
        headers=headers,
        json={
            "title": "short",
            "story": "x" * 80,
            "category": "other",
            "target_amount": 5000,
        },
    )
    assert r.status_code == 422
    # too-small target
    r = client.post(
        "/api/campaigns",
        headers=headers,
        json={
            "title": "A perfectly fine campaign title here",
            "story": "x" * 80,
            "category": "other",
            "target_amount": 50,
        },
    )
    assert r.status_code == 422


def test_pending_campaign_not_public(client, auth_headers):
    headers, _ = auth_headers()
    r = client.post(
        "/api/campaigns",
        headers=headers,
        json={
            "title": "Pending should not be visible to public yet",
            "story": "x" * 80,
            "category": "other",
            "target_amount": 5000,
        },
    )
    slug = r.json()["slug"]
    assert client.get("/api/campaigns").json() == []
    assert client.get(f"/api/campaigns/{slug}").status_code == 404


def test_verify_makes_campaign_public(client, auth_headers, admin_headers):
    headers, _ = auth_headers()
    r = client.post(
        "/api/campaigns",
        headers=headers,
        json={
            "title": "A verified campaign becomes public quickly",
            "story": "x" * 80,
            "category": "other",
            "city": "Karachi",
            "target_amount": 5000,
        },
    )
    cid = r.json()["id"]
    # non-admin cannot verify
    assert client.post(f"/api/admin/campaigns/{cid}/verify", headers=headers).status_code == 403
    client.post(f"/api/admin/campaigns/{cid}/verify", headers=admin_headers())
    listing = client.get("/api/campaigns").json()
    assert len(listing) == 1
    assert listing[0]["status"] == "verified"


def test_reject_requires_reason(client, auth_headers, admin_headers):
    headers, _ = auth_headers()
    r = client.post(
        "/api/campaigns",
        headers=headers,
        json={
            "title": "A campaign that will be rejected for docs",
            "story": "x" * 80,
            "category": "other",
            "target_amount": 5000,
        },
    )
    cid = r.json()["id"]
    ah = admin_headers()
    assert (
        client.post(
            f"/api/admin/campaigns/{cid}/reject", headers=ah, json={"reason": "short"}
        ).status_code
        == 422
    )
    r2 = client.post(
        f"/api/admin/campaigns/{cid}/reject",
        headers=ah,
        json={"reason": "Documents incomplete — no hospital estimate attached."},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "rejected"
    assert client.get("/api/campaigns").json() == []


def test_owner_cannot_verify_own(client, auth_headers, admin_headers):
    pass  # covered by test_verify_makes_campaign_public non-admin 403


def test_my_campaigns_only_owner(client, auth_headers):
    h1, _ = auth_headers("owner1@test.pk")
    client.post(
        "/api/campaigns",
        headers=h1,
        json={
            "title": "Campaign belonging to owner number one",
            "story": "x" * 80,
            "category": "other",
            "target_amount": 5000,
        },
    )
    h2, _ = auth_headers("owner2@test.pk")
    mine = client.get("/api/my/campaigns", headers=h2).json()
    assert mine == []
    mine1 = client.get("/api/my/campaigns", headers=h1).json()
    assert len(mine1) == 1


def test_list_campaigns_filters(client, campaign):
    slug, headers = campaign(target=700_000)
    # category filter
    r = client.get("/api/campaigns?category=surgery")
    assert len(r.json()) == 1
    r = client.get("/api/campaigns?category=cancer")
    assert r.json() == []
    # search
    assert len(client.get("/api/campaigns?q=little+boy").json()) == 1
    assert len(client.get("/api/campaigns?q=zzzznothing").json()) == 0
    # city
    assert len(client.get("/api/campaigns?city=Karachi").json()) == 1


def test_campaign_slug_unique(client, auth_headers):
    headers, _ = auth_headers()
    payload = {
        "title": "Two campaigns with the exact same title here",
        "story": "x" * 80,
        "category": "other",
        "target_amount": 5000,
    }
    s1 = client.post("/api/campaigns", headers=headers, json=payload).json()["slug"]
    s2 = client.post("/api/campaigns", headers=headers, json=payload).json()["slug"]
    assert s1 != s2


def test_post_update_owner_only(client, campaign):
    slug, owner_h = campaign()
    # fresh other user
    r = client.post(
        "/api/auth/register",
        json={"email": "other@test.pk", "name": "Other", "password": "testpass123"},
    )
    other_h = {"Authorization": "Bearer " + r.json()["access_token"]}
    # stranger cannot post
    assert (
        client.post(
            f"/api/campaigns/{slug}/updates",
            headers=other_h,
            json={"body": "A stranger update should not be allowed at all"},
        ).status_code
        == 404
    )
    # owner can
    r = client.post(
        f"/api/campaigns/{slug}/updates",
        headers=owner_h,
        json={"body": "Surgery went well, alhamdulillah. Receipts attached soon."},
    )
    assert r.status_code == 201
    updates = client.get(f"/api/campaigns/{slug}/updates").json()
    assert len(updates) == 1


def test_close_campaign_owner(client, campaign):
    slug, owner_h = campaign()
    other_h, _ = client_register(client, "random@test.pk")
    assert client.post(f"/api/campaigns/{slug}/close", headers=other_h).status_code == 404
    r = client.post(f"/api/campaigns/{slug}/close", headers=owner_h)
    assert r.status_code == 200
    assert r.json()["status"] == "closed"
    # closed campaigns leave the public list
    assert client.get("/api/campaigns").json() == []


def client_register(client, email, password="testpass123", name="Tester"):
    r = client.post("/api/auth/register", json={"email": email, "password": password, "name": name})
    tok = r.json()["access_token"]
    return {"Authorization": "Bearer " + tok}, r.json()["user"]
