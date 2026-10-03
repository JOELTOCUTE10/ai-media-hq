"""Authentication endpoints: register (creates organization), login, me."""
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.events import EventType
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.organization import Organization, User
from app.seed import seed_org
from app.services.event_bus import publish

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=200)
    organization_name: str = Field(default="My Media Company", max_length=200)


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    org_id: int
    organization_name: str

    model_config = {"from_attributes": True}


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


def _issue_token(user: User) -> TokenOut:
    settings = get_settings()
    return TokenOut(access_token=create_access_token(str(user.id), settings.SECRET_KEY,
                                                    settings.ACCESS_TOKEN_EXPIRE_MINUTES))


@router.post("/register", response_model=TokenOut, status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    base_slug = _slugify(data.organization_name)
    slug, n = base_slug, 2
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base_slug}-{n}"
        n += 1
    org = Organization(name=data.organization_name, slug=slug,
                       settings={"operations_paused": False, "publishing_paused": True,
                                 "auto_publish": False, "monthly_budget_usd": 100.0})
    db.add(org)
    db.flush()
    user = User(email=data.email.lower(), hashed_password=hash_password(data.password),
                full_name=data.full_name, role="owner", org_id=org.id)
    db.add(user)
    db.flush()
    seed_org(db, org.id)
    publish(db, EventType.ORG_REGISTERED, {"org": org.slug}, org_id=org.id, commit=True)
    return _issue_token(user)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return _issue_token(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org = db.get(Organization, user.org_id)
    return UserOut(id=user.id, email=user.email, full_name=user.full_name, role=user.role,
                   org_id=user.org_id, organization_name=org.name if org else "")
