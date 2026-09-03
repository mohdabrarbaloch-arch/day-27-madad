def test_admin_endpoints_require_admin(client, auth_headers):
    h, _ = auth_headers()
    for path in ["/api/admin/campaigns", "/api/admin/users", "/api/admin/stats"]:
        assert client.get(path, headers=h).status_code == 403
    assert client.get("/api/admin/campaigns").status_code == 401


def test_admin_pending_queue(client, auth_headers, admin_headers):
    headers, _ = auth_headers()
    client.post(
        "/api/campaigns",
        headers=headers,
        json={
            "title": "Campaign waiting in the admin queue now",
            "story": "x" * 80,
            "category": "other",
            "target_amount": 5000,
        },
    )
    q = client.get("/api/admin/campaigns?status_filter=pending", headers=admin_headers()).json()
    assert len(q) == 1
    assert q[0]["status"] == "pending"


def test_admin_suspend_user(client, auth_headers, admin_headers, make_user):
    u, _ = make_user("victim@test.pk")
    ah = admin_headers()
    r = client.post(f"/api/admin/users/{u.id}/suspend", headers=ah)
    assert r.status_code == 200
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        from app.models import User

        u2 = db.get(User, u.id)
        assert u2.is_suspended is True
    finally:
        db.close()
    # suspended user cannot log in
    lr = client.post("/api/auth/login", json={"email": "victim@test.pk", "password": "testpass123"})
    assert lr.status_code == 403
    r2 = client.post(f"/api/admin/users/{u.id}/unsuspend", headers=ah)
    assert r2.status_code == 200


def test_admin_cannot_suspend_admin(client, make_user, admin_headers):
    u, _ = make_user("secondroot@madad.pk", role="admin")
    r = client.post(f"/api/admin/users/{u.id}/suspend", headers=admin_headers())
    assert r.status_code == 400


def test_admin_stats(client, campaign, admin_headers):
    campaign()
    s = client.get("/api/admin/stats", headers=admin_headers()).json()
    assert s["campaigns"]["verified"] >= 1
    assert s["users"] >= 2


def test_public_stats_shape(client):
    s = client.get("/api/public/stats").json()
    assert set(s.keys()) == {
        "total_campaigns",
        "verified_campaigns",
        "total_raised",
        "total_donations",
        "cities",
    }


def test_invalid_token_401(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert r.status_code == 401


def test_campaign_detail_404_unknown_slug(client):
    assert client.get("/api/campaigns/does-not-exist").status_code == 404
