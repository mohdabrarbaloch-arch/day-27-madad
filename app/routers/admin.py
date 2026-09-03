from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import (
    Campaign,
    CampaignStatus,
    Donation,
    DonationStatus,
    User,
)
from ..schemas import AdminAction, CampaignSummary
from ..security import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _summary_with(c: Campaign) -> CampaignSummary:
    donor_count = sum(1 for d in c.donations if d.status == DonationStatus.CONFIRMED.value)
    return CampaignSummary(
        id=c.id,
        slug=c.slug,
        title=c.title,
        category=c.category,
        city=c.city,
        hospital=c.hospital,
        target_amount=c.target_amount,
        amount_raised=c.amount_raised,
        progress_percent=c.progress_percent,
        status=c.status,
        created_at=c.created_at,
        owner_name=c.owner.name,
        update_count=len(c.updates),
        donor_count=donor_count,
    )


@router.get("/campaigns", response_model=list[CampaignSummary])
def admin_campaigns(
    status_filter: str = Query(
        default="pending", pattern="^(pending|verified|closed|rejected|all)$"
    ),
    db: Session = Depends(get_db),
):
    q = db.query(Campaign).options(joinedload(Campaign.owner))
    if status_filter != "all":
        q = q.filter(Campaign.status == status_filter)
    rows = q.order_by(Campaign.created_at.desc()).limit(100).all()
    return [_summary_with(c) for c in rows]


@router.post("/campaigns/{campaign_id}/verify", response_model=CampaignSummary)
def verify_campaign(campaign_id: int, db: Session = Depends(get_db)):
    c = db.get(Campaign, campaign_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if c.status != CampaignStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending campaigns can be verified"
        )
    c.status = CampaignStatus.VERIFIED.value
    c.reject_reason = ""
    db.commit()
    db.refresh(c)
    return _summary_with(c)


@router.post("/campaigns/{campaign_id}/reject", response_model=CampaignSummary)
def reject_campaign(campaign_id: int, payload: AdminAction, db: Session = Depends(get_db)):
    c = db.get(Campaign, campaign_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if c.status != CampaignStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending campaigns can be rejected"
        )
    if len(payload.reason.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A reason (min 10 chars) is required",
        )
    c.status = CampaignStatus.REJECTED.value
    c.reject_reason = payload.reason.strip()
    db.commit()
    db.refresh(c)
    return _summary_with(c)


@router.post("/campaigns/{campaign_id}/close", response_model=CampaignSummary)
def admin_close_campaign(campaign_id: int, db: Session = Depends(get_db)):
    c = db.get(Campaign, campaign_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if c.status != CampaignStatus.VERIFIED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only live campaigns can be closed"
        )
    c.status = CampaignStatus.CLOSED.value
    db.commit()
    db.refresh(c)
    return _summary_with(c)


@router.post("/users/{user_id}/suspend", response_model=dict)
def suspend_user(user_id: int, db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if u.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot suspend an admin"
        )
    u.is_suspended = True
    db.commit()
    return {"ok": True, "id": u.id, "is_suspended": True}


@router.post("/users/{user_id}/unsuspend", response_model=dict)
def unsuspend_user(user_id: int, db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    u.is_suspended = False
    db.commit()
    return {"ok": True, "id": u.id, "is_suspended": False}


@router.get("/users", response_model=list[dict])
def admin_users(db: Session = Depends(get_db)):
    rows = db.query(User).order_by(User.created_at.desc()).limit(100).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "is_suspended": u.is_suspended,
            "campaigns": len(u.campaigns),
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in rows
    ]


@router.get("/stats", response_model=dict)
def admin_stats(db: Session = Depends(get_db)):
    statuses = dict(
        db.query(Campaign.status, func.count(Campaign.id)).group_by(Campaign.status).all()
    )
    donations = (
        db.query(
            Donation.status, func.count(Donation.id), func.coalesce(func.sum(Donation.amount), 0)
        )
        .group_by(Donation.status)
        .all()
    )
    return {
        "campaigns": {k: int(v) for k, v in statuses.items()},
        "users": db.query(User).count(),
        "donations": {
            d: {"count": int(cnt), "amount": int(amount or 0)} for d, cnt, amount in donations
        },
    }
