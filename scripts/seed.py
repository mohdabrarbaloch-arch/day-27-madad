#!/usr/bin/env python3
"""Seed Madad with an admin user and demo campaigns.

Usage:
    cd project-day-27-madad && python scripts/seed.py

Creates:
    - admin user (env ADMIN_SEED_EMAIL / ADMIN_SEED_PASSWORD or defaults)
    - 3 verified demo campaigns with a couple of updates each
"""

import os
import sys
from datetime import UTC, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Campaign, CampaignStatus, CampaignUpdate, Role, User  # noqa: E402
from app.security import hash_password  # noqa: E402

settings = get_settings()

DEMO = [
    {
        "title": "Zainab's bone marrow transplant — thalassemia treatment",
        "category": "thalassemia",
        "city": "Karachi",
        "hospital": "National Institute of Child Health, Karachi",
        "target_amount": 2_500_000,
        "amount_raised": 1_100_000,
        "owner": ("Fatima Ahmed", "fatima@example.com"),
        "story": (
            "Zainab is 6 years old and was diagnosed with beta-thalassemia major when she was 11 months old. "
            "For the last five years she has needed a blood transfusion every three weeks. Her doctors at NICH "
            "Karachi have identified a matching bone marrow donor, but the transplant procedure costs around "
            "2.5 million rupees after the hospital's partial subsidy. Her father drives a rickshaw and her "
            "mother stitches clothes at home — the family has already sold their plot and borrowed from "
            "relatives. We are raising the remaining amount so Zainab can get her transplant before the donor "
            "window closes."
        ),
        "updates": [
            "Alhamdulillah we have reached the first milestone. The hospital has completed the pre-transplant "
            "workup and Zainab's donor has confirmed availability for next month. Every rupee is being tracked "
            "and will be shared in the final statement.",
            "A local charity has pledged an additional 500,000 rupees against the hospital bill directly. "
            "We remain grateful to every single donor — please keep Zainab in your prayers.",
        ],
    },
    {
        "title": "Ayesha's open heart surgery at PIMS Islamabad",
        "category": "cardiac",
        "city": "Islamabad",
        "hospital": "Pakistan Institute of Medical Sciences",
        "target_amount": 1_800_000,
        "amount_raised": 720_000,
        "owner": ("Muhammad Bilal", "bilal@example.com"),
        "story": (
            "Ayesha (34) is a schoolteacher and the sole earner for her family of five. Last month she collapsed "
            "in class and was rushed to PIMS where doctors found a congenital heart defect that requires urgent "
            "open heart surgery. The procedure and post-op ICU stay are estimated at 1.8 million rupees. Her "
            "school has given her paid leave but cannot cover the bill. We are her brothers and sisters raising "
            "this with full transparency — hospital estimates and payment receipts will be posted as updates."
        ),
        "updates": [
            "Ayesha's angiography has been completed and the surgery date is confirmed for next month at PIMS. "
            "The hospital has provided a written estimate which we have shared with donors on request.",
        ],
    },
    {
        "title": "Emergency road accident recovery for Hamza — ICU support",
        "category": "accident",
        "city": "Lahore",
        "hospital": "Jinnah Hospital, Lahore",
        "target_amount": 900_000,
        "amount_raised": 900_000,
        "owner": ("Sana Tariq", "sana@example.com"),
        "story": (
            "Hamza (22), a final-year university student, was hit by a motorbike while crossing Ferozepur Road. "
            "He has been in the Jinnah Hospital ICU for three weeks with multiple fractures and internal "
            "bleeding. His family runs a small tea stall and has already spent their life savings. We are "
            "raising funds for his remaining ICU and rehabilitation costs so he can walk again and sit his "
            "final exams next year."
        ),
        "updates": [
            "Hamza has been moved out of ICU to a private ward and his doctors are happy with his recovery. "
            "The campaign goal has been reached — thank you to every donor. Final receipts will be posted here "
            "within two weeks.",
        ],
    },
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == settings.admin_seed_email.lower()).first()
        if admin is None:
            admin = User(
                email=settings.admin_seed_email.lower(),
                name="Madad Admin",
                phone="",
                password_hash=hash_password(settings.admin_seed_password),
                role=Role.ADMIN.value,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"admin created: {admin.email}")
        else:
            print(f"admin exists: {admin.email}")

        for d in DEMO:
            owner = db.query(User).filter(User.email == d["owner"][1]).first()
            if owner is None:
                owner = User(
                    email=d["owner"][1],
                    name=d["owner"][0],
                    phone="",
                    password_hash=hash_password("demo12345"),
                )
                db.add(owner)
                db.commit()
                db.refresh(owner)
            exists = db.query(Campaign).filter(Campaign.title == d["title"]).first()
            if exists:
                print(f"campaign exists: {exists.slug}")
                continue
            slug = d["title"].lower().replace("'", "").replace("&", "and")
            for ch in "():.,—–-":
                slug = slug.replace(ch, " ")
            slug = "-".join(slug.split())[:80].rstrip("-")
            campaign = Campaign(
                slug=slug,
                owner_id=owner.id,
                title=d["title"],
                story=d["story"],
                category=d["category"],
                city=d["city"],
                hospital=d["hospital"],
                target_amount=d["target_amount"],
                amount_raised=d["amount_raised"],
                status=(
                    CampaignStatus.CLOSED.value
                    if d["amount_raised"] >= d["target_amount"]
                    else CampaignStatus.VERIFIED.value
                ),
                created_at=datetime.now(UTC),
            )
            db.add(campaign)
            db.commit()
            db.refresh(campaign)
            for body in d["updates"]:
                db.add(CampaignUpdate(campaign_id=campaign.id, author_id=owner.id, body=body))
            db.commit()
            print(f"campaign created: {campaign.slug} ({campaign.status})")
        print("seed complete")
    finally:
        db.close()


if __name__ == "__main__":
    main()
