import re
import uuid


def slugify(title: str) -> str:
    """Turn a title into a URL-safe slug, romanizing nothing — drops non-ascii."""
    s = title.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    if not s:
        s = "campaign"
    return s[:80].rstrip("-")


def unique_slug(db, title: str) -> str:
    """Return a slug guaranteed unique in the campaigns table."""
    from .models import Campaign

    base = slugify(title)
    candidate = base
    while db.query(Campaign.id).filter(Campaign.slug == candidate).first() is not None:
        candidate = f"{base}-{uuid.uuid4().hex[:5]}"
    return candidate


def new_reference() -> str:
    """Short human-friendly donation reference like MAD-A1B2C3D4."""
    return f"MAD-{uuid.uuid4().hex[:8].upper()}"
