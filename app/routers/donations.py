from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Campaign, CampaignStatus, Donation, DonationStatus, User
from ..schemas import DonateIn, DonationOut
from ..security import get_current_user
from ..utils import new_reference

router = APIRouter(tags=["donations"])


def _donation_out(d: Donation) -> DonationOut:
    donor_name = "" if d.is_anonymous else d.donor.name
    return DonationOut(
        id=d.id,
        reference=d.reference,
        campaign_id=d.campaign_id,
        campaign_slug=d.campaign.slug,
        campaign_title=d.campaign.title,
        amount=d.amount,
        message=d.message,
        is_anonymous=d.is_anonymous,
        status=d.status,
        created_at=d.created_at,
        confirmed_at=d.confirmed_at,
        donor_name=donor_name,
    )


@router.post(
    "/api/campaigns/{slug}/donate", response_model=DonationOut, status_code=status.HTTP_201_CREATED
)
def donate(
    slug: str,
    payload: DonateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Pledge a donation to a live campaign. Owner confirming the transfer later
    marks it confirmed — the donor only pledges here."""
    c = (
        db.query(Campaign)
        .filter(Campaign.slug == slug, Campaign.status == CampaignStatus.VERIFIED.value)
        .first()
    )
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if c.owner_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="You cannot donate to your own campaign"
        )
    remaining = c.target_amount - c.amount_raised
    if remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign has already reached its goal"
        )
    if payload.amount > remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amount exceeds the remaining goal (max PKR {remaining:,})",
        )
    donation = Donation(
        reference=new_reference(),
        campaign_id=c.id,
        donor_id=user.id,
        amount=payload.amount,
        message=payload.message.strip(),
        is_anonymous=payload.is_anonymous,
        status=DonationStatus.PLEDGED.value,
    )
    db.add(donation)
    db.commit()
    db.refresh(donation)
    return _donation_out(donation)


@router.post("/api/campaigns/{slug}/donations/{donation_id}/confirm", response_model=DonationOut)
def confirm_donation(
    slug: str,
    donation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Campaign owner confirms a pledge was received in their bank account.
    Confirmation credits the raised amount atomically; reaching the goal
    auto-closes the campaign."""
    c = db.query(Campaign).filter(Campaign.slug == slug).first()
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if c.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the campaign owner can confirm donations",
        )
    if c.status != CampaignStatus.VERIFIED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign is not accepting confirmations",
        )
    d = (
        db.query(Donation)
        .filter(
            Donation.id == donation_id,
            Donation.campaign_id == c.id,
            Donation.status == DonationStatus.PLEDGED.value,
        )
        .first()
    )
    if d is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pledge not found")
    if d.donor_id == c.owner_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Self-donations cannot be confirmed"
        )

    remaining = c.target_amount - c.amount_raised
    if d.amount > remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pledge exceeds the remaining goal — ask the donor to reduce it",
        )
    d.status = DonationStatus.CONFIRMED.value
    d.confirmed_at = datetime.now(UTC)
    c.amount_raised += d.amount
    if c.amount_raised >= c.target_amount:
        c.status = CampaignStatus.CLOSED.value
    db.commit()
    db.refresh(d)
    return _donation_out(d)


@router.post("/api/donations/{donation_id}/cancel", response_model=DonationOut)
def cancel_pledge(
    donation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """A donor may cancel their own pledge as long as it hasn't been confirmed."""
    d = (
        db.query(Donation)
        .options(joinedload(Donation.campaign), joinedload(Donation.donor))
        .filter(Donation.id == donation_id, Donation.donor_id == user.id)
        .first()
    )
    if d is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")
    if d.status == DonationStatus.CONFIRMED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmed donations cannot be cancelled — contact the campaign owner",
        )
    if d.status == DonationStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Donation already cancelled"
        )
    d.status = DonationStatus.CANCELLED.value
    db.commit()
    db.refresh(d)
    return _donation_out(d)


@router.get("/api/my/donations", response_model=list[DonationOut])
def my_donations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Donation)
        .options(joinedload(Donation.campaign), joinedload(Donation.donor))
        .filter(Donation.donor_id == user.id)
        .order_by(Donation.created_at.desc())
        .all()
    )
    return [_donation_out(d) for d in rows]


@router.get("/api/campaigns/{slug}/donations", response_model=list[DonationOut])
def campaign_donations(
    slug: str,
    status_filter: str = Query(default="confirmed", pattern="^(confirmed|pledged|all)$"),
    db: Session = Depends(get_db),
):
    """Public ledger of confirmed donations for a live campaign."""
    c = db.query(Campaign).filter(Campaign.slug == slug).first()
    if c is None or c.status not in (CampaignStatus.VERIFIED.value, CampaignStatus.CLOSED.value):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    q = (
        db.query(Donation)
        .options(joinedload(Donation.campaign), joinedload(Donation.donor))
        .filter(Donation.campaign_id == c.id)
    )
    if status_filter == "confirmed":
        q = q.filter(Donation.status == DonationStatus.CONFIRMED.value)
    elif status_filter == "pledged":
        q = q.filter(Donation.status == DonationStatus.PLEDGED.value)
    return [_donation_out(d) for d in q.order_by(Donation.created_at.desc()).limit(50).all()]


@router.get("/api/my/campaigns/{slug}/pledges", response_model=list[DonationOut])
def my_campaign_pledges(
    slug: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner-only view of all pledges (confirmed + pending) on their campaign."""
    c = db.query(Campaign).filter(Campaign.slug == slug, Campaign.owner_id == user.id).first()
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    rows = (
        db.query(Donation)
        .options(joinedload(Donation.campaign), joinedload(Donation.donor))
        .filter(Donation.campaign_id == c.id)
        .order_by(Donation.created_at.desc())
        .all()
    )
    return [_donation_out(d) for d in rows]
