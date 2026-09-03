from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str = Field(default="", max_length=30)

    @field_validator("password")
    @classmethod
    def password_not_common(cls, v: str) -> str:
        if v.lower() in {"password", "12345678", "qwertyuiop", "admin12345"}:
            raise ValueError("choose a stronger password")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    phone: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class CampaignCreate(BaseModel):
    title: str = Field(min_length=10, max_length=150)
    story: str = Field(min_length=50, max_length=10000)
    category: str = Field(min_length=3, max_length=40)
    city: str = Field(default="", max_length=80)
    hospital: str = Field(default="", max_length=150)
    target_amount: int = Field(ge=1000, le=100_000_000)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, v: str) -> str:
        return v.strip().lower()


class CampaignSummary(BaseModel):
    id: int
    slug: str
    title: str
    category: str
    city: str
    hospital: str
    target_amount: int
    amount_raised: int
    progress_percent: int
    status: str
    created_at: datetime
    owner_name: str
    update_count: int = 0
    donor_count: int = 0

    model_config = {"from_attributes": True}


class CampaignDetail(CampaignSummary):
    story: str
    owner_id: int
    reject_reason: str


class CampaignUpdateIn(BaseModel):
    body: str = Field(min_length=10, max_length=5000)


class CampaignUpdateOut(BaseModel):
    id: int
    campaign_id: int
    author_name: str
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DonateIn(BaseModel):
    amount: int = Field(ge=100, le=2_000_000)
    message: str = Field(default="", max_length=500)
    is_anonymous: bool = False


class DonationOut(BaseModel):
    id: int
    reference: str
    campaign_id: int
    campaign_slug: str = ""
    campaign_title: str = ""
    amount: int
    message: str
    is_anonymous: bool
    status: str
    created_at: datetime
    confirmed_at: datetime | None
    donor_name: str = ""

    model_config = {"from_attributes": True}


class StatsOut(BaseModel):
    total_campaigns: int
    verified_campaigns: int
    total_raised: int
    total_donations: int
    cities: int


class AdminAction(BaseModel):
    reason: str = Field(default="", max_length=500)
