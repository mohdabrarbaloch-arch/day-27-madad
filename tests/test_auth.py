def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_success(client):
    r = client.post(
        "/api/auth/register",
        json={
            "name": "Ayesha Khan",
            "email": "ayesha@test.pk",
            "password": "secure12345",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "ayesha@test.pk"
    assert data["user"]["role"] == "user"
    assert "password" not in str(data["user"])


def test_register_duplicate_email_conflict(client, register):
    assert register("dup@test.pk").status_code == 201
    r = register("dup@test.pk")
    assert r.status_code == 409


def test_register_invalid_email(client):
    r = client.post(
        "/api/auth/register",
        json={
            "name": "Bad",
            "email": "not-an-email",
            "password": "secure12345",
        },
    )
    assert r.status_code == 422


def test_register_weak_password_rejected(client):
    r = client.post(
        "/api/auth/register",
        json={
            "name": "Weak",
            "email": "weak@test.pk",
            "password": "12345678",
        },
    )
    assert r.status_code == 422


def test_login_success(client, register):
    register("login@test.pk")
    r = client.post("/api/auth/login", json={"email": "login@test.pk", "password": "testpass123"})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_wrong_password(client, register):
    register("wrong@test.pk")
    r = client.post("/api/auth/login", json={"email": "wrong@test.pk", "password": "wrongpass123"})
    assert r.status_code == 401


def test_login_case_insensitive_email(client, register):
    register("case@test.pk")
    r = client.post("/api/auth/login", json={"email": "CASE@test.pk", "password": "testpass123"})
    assert r.status_code == 200


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_user(client, register):
    register("me@test.pk")
    r = client.post("/api/auth/login", json={"email": "me@test.pk", "password": "testpass123"})
    tok = r.json()["access_token"]
    r2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r2.status_code == 200
    assert r2.json()["email"] == "me@test.pk"


def test_suspended_user_cannot_login(client, make_user):
    u, pw = make_user("banned@test.pk")
    from app.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        u = db.get(User, u.id)
        u.is_suspended = True
        db.commit()
    finally:
        db.close()
    r = client.post("/api/auth/login", json={"email": "banned@test.pk", "password": pw})
    assert r.status_code == 403


def test_register_rate_limit(client):
    # 5/min allowed; 6th should 429 (TestClient shares the same IP)
    codes = []
    for i in range(6):
        r = client.post(
            "/api/auth/register",
            json={
                "name": f"Spam {i}",
                "email": f"spam{i}@test.pk",
                "password": "secure12345",
            },
        )
        codes.append(r.status_code)
    assert 429 in codes
