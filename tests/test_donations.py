def client_register(client, email, password="testpass123", name="Tester"):
    r = client.post("/api/auth/register", json={"email": email, "password": password, "name": name})
    tok = r.json()["access_token"]
    return {"Authorization": "Bearer " + tok}, r.json()["user"]


def test_donate_requires_auth(client, campaign):
    slug, _ = campaign()
    assert client.post(f"/api/campaigns/{slug}/donate", json={"amount": 500}).status_code == 401


def test_cannot_donate_to_own_campaign(client, campaign):
    slug, owner_h = campaign()
    r = client.post(f"/api/campaigns/{slug}/donate", headers=owner_h, json={"amount": 5000})
    assert r.status_code == 409


def test_donate_pledged_status(client, campaign):
    slug, _ = campaign()
    donor_h, _ = client_register(client, "donor1@test.pk")
    r = client.post(
        f"/api/campaigns/{slug}/donate",
        headers=donor_h,
        json={"amount": 10_000, "message": "Shifa mile InshaAllah", "is_anonymous": False},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pledged"
    assert data["reference"].startswith("MAD-")
    # not yet counted in raised
    detail = client.get(f"/api/campaigns/{slug}").json()
    assert detail["amount_raised"] == 0


def test_donate_over_remaining_rejected(client, campaign):
    slug, _ = campaign(target=50_000)
    donor_h, _ = client_register(client, "donor2@test.pk")
    r = client.post(f"/api/campaigns/{slug}/donate", headers=donor_h, json={"amount": 60_000})
    assert r.status_code == 400


def test_donate_amount_below_min(client, campaign):
    slug, _ = campaign()
    donor_h, _ = client_register(client, "donor3@test.pk")
    assert (
        client.post(
            f"/api/campaigns/{slug}/donate", headers=donor_h, json={"amount": 5}
        ).status_code
        == 422
    )


def test_confirm_donation_owner_only(client, campaign):
    slug, owner_h = campaign()
    donor_h, _ = client_register(client, "donor4@test.pk")
    don = client.post(
        f"/api/campaigns/{slug}/donate", headers=donor_h, json={"amount": 5000}
    ).json()
    # donor cannot confirm own pledge
    r = client.post(f"/api/campaigns/{slug}/donations/{don['id']}/confirm", headers=donor_h)
    assert r.status_code == 403
    # stranger cannot either
    stranger_h, _ = client_register(client, "stranger@test.pk")
    assert (
        client.post(
            f"/api/campaigns/{slug}/donations/{don['id']}/confirm", headers=stranger_h
        ).status_code
        == 403
    )


def test_confirm_donation_credits_raised(client, campaign):
    slug, owner_h = campaign(target=100_000)
    donor_h, _ = client_register(client, "donor5@test.pk")
    don = client.post(
        f"/api/campaigns/{slug}/donate",
        headers=donor_h,
        json={"amount": 25_000, "message": "Allah kare jaldi shifa"},
    ).json()
    r = client.post(f"/api/campaigns/{slug}/donations/{don['id']}/confirm", headers=owner_h)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"
    detail = client.get(f"/api/campaigns/{slug}").json()
    assert detail["amount_raised"] == 25_000
    assert detail["donor_count"] == 1


def test_goal_reached_auto_closes(client, campaign):
    slug, owner_h = campaign(target=50_000)
    donor_h, _ = client_register(client, "donor6@test.pk")
    don = client.post(
        f"/api/campaigns/{slug}/donate", headers=donor_h, json={"amount": 50_000}
    ).json()
    r = client.post(f"/api/campaigns/{slug}/donations/{don['id']}/confirm", headers=owner_h)
    assert r.status_code == 200
    # campaign auto-closed at 100%
    my = client.get("/api/my/campaigns", headers=owner_h).json()
    assert my[0]["status"] == "closed"
    assert my[0]["progress_percent"] == 100


def test_donor_cancel_own_pledge(client, campaign):
    slug, owner_h = campaign()
    donor_h, _ = client_register(client, "donor7@test.pk")
    don = client.post(
        f"/api/campaigns/{slug}/donate", headers=donor_h, json={"amount": 10_000}
    ).json()
    r = client.post(f"/api/donations/{don['id']}/cancel", headers=donor_h)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    # owner still sees the cancelled pledge but raised is untouched
    my = client.get(f"/api/my/campaigns/{slug}/pledges", headers=owner_h).json()
    assert my[0]["status"] == "cancelled"
    assert client.get(f"/api/campaigns/{slug}").json()["amount_raised"] == 0


def test_cannot_cancel_others_pledge(client, campaign):
    slug, _ = campaign()
    donor_h, _ = client_register(client, "donor8@test.pk")
    other_h, _ = client_register(client, "donor8b@test.pk")
    don = client.post(
        f"/api/campaigns/{slug}/donate", headers=donor_h, json={"amount": 1000}
    ).json()
    assert client.post(f"/api/donations/{don['id']}/cancel", headers=other_h).status_code == 404


def test_public_ledger_hides_anonymous(client, campaign):
    slug, owner_h = campaign()
    donor_h, _ = client_register(client, "donor9@test.pk")
    client.post(
        f"/api/campaigns/{slug}/donate",
        headers=donor_h,
        json={"amount": 5000, "is_anonymous": True},
    )
    ledger = client.get(f"/api/campaigns/{slug}/donations").json()
    assert ledger == []  # pledged not confirmed yet, so not in the confirmed ledger
    # confirm then check anonymity
    from app.database import SessionLocal
    from app.models import Donation

    db = SessionLocal()
    try:
        d = db.query(Donation).first()
        did = d.id
    finally:
        db.close()
    client.post(f"/api/campaigns/{slug}/donations/{did}/confirm", headers=owner_h)
    ledger = client.get(f"/api/campaigns/{slug}/donations").json()
    assert ledger[0]["is_anonymous"] is True
    assert ledger[0]["donor_name"] == ""


def test_my_donations_receipts(client, campaign):
    slug, _ = campaign()
    donor_h, _ = client_register(client, "donor10@test.pk")
    don = client.post(
        f"/api/campaigns/{slug}/donate", headers=donor_h, json={"amount": 15_000}
    ).json()
    mine = client.get("/api/my/donations", headers=donor_h).json()
    assert len(mine) == 1
    assert mine[0]["reference"] == don["reference"]
    assert mine[0]["campaign_title"]
