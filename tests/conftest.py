import os
import tempfile

# env must be set BEFORE importing app modules
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["JWT_SECRET"] = "test-secret-key-not-for-prod"
os.environ["ADMIN_SEED_EMAIL"] = "admin@madad.pk"
os.environ["ADMIN_SEED_PASSWORD"] = "admin12345"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Role, User  # noqa: E402
from app.security import hash_password  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from app.ratelimit import limiter

    limiter.reset()  # fresh rate-limit window per test
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def make_user():
    """Create a user directly in the DB; returns (user, password)."""

    def _make(
        email: str,
        name: str = "Test User",
        role: str = Role.USER.value,
        password: str = "testpass123",
    ):
        db = SessionLocal()
        try:
            u = User(email=email, name=name, role=role, password_hash=hash_password(password))
            db.add(u)
            db.commit()
            db.refresh(u)
            return u, password
        finally:
            db.close()

    return _make


@pytest.fixture()
def register(client):
    """Register through the API; returns token dict via closure."""

    def _register(email: str, password: str = "testpass123", name: str = "Test User"):
        r = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
                "name": name,
            },
        )
        return r

    return _register


@pytest.fixture()
def auth_headers(client, register):
    """Register + login a fresh user; returns (headers, user)."""

    def _auth(email: str = "user@test.pk"):
        register(email)
        r = client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
        data = r.json()
        return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]

    return _auth


@pytest.fixture()
def admin_headers(client, make_user):
    def _admin():
        from app.database import SessionLocal
        from app.models import User

        db = SessionLocal()
        try:
            existing = db.query(User).filter(User.email == "root@madad.pk").first()
        finally:
            db.close()
        if existing is None:
            make_user("root@madad.pk", role=Role.ADMIN.value)
        r = client.post(
            "/api/auth/login",
            json={"email": "root@madad.pk", "password": "testpass123"},
        )
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _admin


@pytest.fixture()
def campaign(client, auth_headers, admin_headers):
    """Create + verify a campaign; returns (slug, owner_headers)."""

    def _campaign(target: int = 500_000, amount_raised: int = 0):
        headers, user = auth_headers()
        r = client.post(
            "/api/campaigns",
            headers=headers,
            json={
                "title": "Surgery for a little boy at JPMC Karachi",
                "story": "This is a real emergency. The child needs an urgent operation "
                "and the family cannot afford the hospital bill at all.",
                "category": "surgery",
                "city": "Karachi",
                "hospital": "JPMC",
                "target_amount": target,
            },
        )
        slug = r.json()["slug"]
        # find id for admin verify
        from app.database import SessionLocal
        from app.models import Campaign as C

        db = SessionLocal()
        try:
            c = db.query(C).filter(C.slug == slug).first()
            cid = c.id
        finally:
            db.close()
        aheaders = admin_headers()
        client.post(f"/api/admin/campaigns/{cid}/verify", headers=aheaders)
        return slug, headers

    return _campaign
