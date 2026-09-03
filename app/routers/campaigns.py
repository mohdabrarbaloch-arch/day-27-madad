from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import (
    Campaign,
    CampaignStatus,
    CampaignUpdate,
    Donation,
    DonationStatus,
    User,
)
from ..schemas import (
    CampaignCreate,
    CampaignDetail,
    CampaignSummary,
    CampaignUpdateIn,
    CampaignUpdateOut,
)
from ..security import get_current_user
from ..utils import unique_slug

router = APIRouter(tags=["campaigns"])

CATEGORIES = [
    "cancer",
    "surgery",
    "child-health",
    "thalassemia",
    "dialysis",
    "accident",
    "maternity",
    "cardiac",
    "other",
]


def _to_summary(c: Campaign) -> CampaignSummary:
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


def _get_verified_campaign_by_slug(db: Session, slug: str) -> Campaign:
    c = (
        db.query(Campaign)
        .options(joinedload(Campaign.owner), joinedload(Campaign.updates))
        .filter(Campaign.slug == slug)
        .first()
    )
    if c is None or c.status != CampaignStatus.VERIFIED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return c


@router.get("/api/public/stats")
def public_stats(db: Session = Depends(get_db)):
    verified = CampaignStatus.VERIFIED.value
    total_raised = (
        db.query(func.coalesce(func.sum(Donation.amount), 0))
        .join(Campaign, Donation.campaign_id == Campaign.id)
        .filter(Donation.status == DonationStatus.CONFIRMED.value)
        .filter(Campaign.status == verified)
        .scalar()
    )
    return {
        "total_campaigns": db.query(Campaign).count(),
        "verified_campaigns": db.query(Campaign).filter(Campaign.status == verified).count(),
        "total_raised": int(total_raised or 0),
        "total_donations": (
            db.query(Donation)
            .join(Campaign, Donation.campaign_id == Campaign.id)
            .filter(Donation.status == DonationStatus.CONFIRMED.value)
            .filter(Campaign.status == verified)
            .count()
        ),
        "cities": (
            db.query(Campaign.city)
            .filter(Campaign.status == verified, Campaign.city != "")
            .distinct()
            .count()
        ),
    }


@router.get("/api/campaigns", response_model=list[CampaignSummary])
def list_campaigns(
    category: str | None = Query(default=None, max_length=40),
    city: str | None = Query(default=None, max_length=80),
    q: str | None = Query(default=None, max_length=120),
    sort: str = Query(default="recent", pattern="^(recent|urgent|raised)$"),
    limit: int = Query(default=12, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Campaign).filter(Campaign.status == CampaignStatus.VERIFIED.value)
    if category:
        query = query.filter(Campaign.category == category.lower())
    if city:
        query = query.filter(Campaign.city.ilike(f"%{city.strip()}%"))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(Campaign.title.ilike(like) | Campaign.story.ilike(like))

    if sort == "urgent":
        # closest to goal first
        query = query.order_by((Campaign.target_amount - Campaign.amount_raised).asc())
    elif sort == "raised":
        query = query.order_by(Campaign.amount_raised.desc())
    else:
        query = query.order_by(Campaign.created_at.desc())

    rows = query.offset(offset).limit(limit).all()
    # eager-load owners/updates/donations per row for the summary
    ids = [c.id for c in rows]
    if not ids:
        return []
    owners = {
        u.id: u.name for u in db.query(User).filter(User.id.in_({c.owner_id for c in rows})).all()
    }
    upd_counts = dict(
        db.query(CampaignUpdate.campaign_id, func.count(CampaignUpdate.id))
        .filter(CampaignUpdate.campaign_id.in_(ids))
        .group_by(CampaignUpdate.campaign_id)
        .all()
    )
    don_counts = dict(
        db.query(Donation.campaign_id, func.count(Donation.id))
        .filter(
            Donation.campaign_id.in_(ids),
            Donation.status == DonationStatus.CONFIRMED.value,
        )
        .group_by(Donation.campaign_id)
        .all()
    )
    out = []
    for c in rows:
        donor_count = don_counts.get(c.id, 0)
        out.append(
            CampaignSummary(
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
                owner_name=owners.get(c.owner_id, ""),
                update_count=upd_counts.get(c.id, 0),
                donor_count=donor_count,
            )
        )
    return out


@router.get("/api/campaigns/{slug}", response_model=CampaignDetail)
def get_campaign(slug: str, db: Session = Depends(get_db)):
    c = (
        db.query(Campaign)
        .options(joinedload(Campaign.owner), joinedload(Campaign.updates))
        .filter(Campaign.slug == slug)
        .first()
    )
    if c is None or c.status != CampaignStatus.VERIFIED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    s = _to_summary(c)
    return CampaignDetail(
        **s.model_dump(), story=c.story, owner_id=c.owner_id, reject_reason=c.reject_reason
    )


@router.get("/api/campaigns/{slug}/updates", response_model=list[CampaignUpdateOut])
def list_updates(slug: str, db: Session = Depends(get_db)):
    c = _get_verified_campaign_by_slug(db, slug)
    return [
        CampaignUpdateOut(
            id=u.id,
            campaign_id=u.campaign_id,
            author_name=u.author.name,
            body=u.body,
            created_at=u.created_at,
        )
        for u in c.updates
    ]


@router.post("/api/campaigns", response_model=CampaignDetail, status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: CampaignCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.is_suspended:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended")
    if payload.category not in CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid category"
        )
    campaign = Campaign(
        slug=unique_slug(db, payload.title),
        owner_id=user.id,
        title=payload.title.strip(),
        story=payload.story.strip(),
        category=payload.category,
        city=payload.city.strip(),
        hospital=payload.hospital.strip(),
        target_amount=payload.target_amount,
        status=CampaignStatus.PENDING.value,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    s = _to_summary(campaign)
    return CampaignDetail(
        **s.model_dump(),
        story=campaign.story,
        owner_id=campaign.owner_id,
        reject_reason=campaign.reject_reason,
    )


@router.get("/api/my/campaigns", response_model=list[CampaignSummary])
def my_campaigns(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Campaign)
        .filter(Campaign.owner_id == user.id)
        .order_by(Campaign.created_at.desc())
        .all()
    )
    return [_to_summary(c) for c in rows]


@router.post(
    "/api/campaigns/{slug}/updates",
    response_model=CampaignUpdateOut,
    status_code=status.HTTP_201_CREATED,
)
def post_update(
    slug: str,
    payload: CampaignUpdateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.query(Campaign).filter(Campaign.slug == slug, Campaign.owner_id == user.id).first()
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if c.status != CampaignStatus.VERIFIED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only live campaigns can receive updates",
        )
    u = CampaignUpdate(campaign_id=c.id, author_id=user.id, body=payload.body.strip())
    db.add(u)
    db.commit()
    db.refresh(u)
    return CampaignUpdateOut(
        id=u.id,
        campaign_id=u.campaign_id,
        author_name=user.name,
        body=u.body,
        created_at=u.created_at,
    )


@router.post("/api/campaigns/{slug}/close", response_model=CampaignDetail)
def close_campaign(
    slug: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.query(Campaign).filter(Campaign.slug == slug, Campaign.owner_id == user.id).first()
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if c.status != CampaignStatus.VERIFIED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only live campaigns can be closed",
        )
    c.status = CampaignStatus.CLOSED.value
    db.commit()
    db.refresh(c)
    s = _to_summary(c)
    return CampaignDetail(
        **s.model_dump(), story=c.story, owner_id=c.owner_id, reject_reason=c.reject_reason
    )
