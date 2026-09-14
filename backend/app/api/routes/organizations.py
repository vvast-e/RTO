import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization_id
from app.db.session import get_db
from app.models.organization import Organization
from app.schemas.organization import OrganizationMeOut, TelegramLinkCodeOut
from app.services.telegram_link import create_link_code

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.get("/me", response_model=OrganizationMeOut)
def get_organization_me(
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    organization = db.get(Organization, org_id)
    return OrganizationMeOut(
        name=organization.name,
        telegram_linked=organization.telegram_chat_id is not None,
    )


@router.post("/me/telegram-link-code", response_model=TelegramLinkCodeOut)
def get_telegram_link_code(
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    """Выдаёт одноразовый код привязки текущей организации к Telegram-боту.

    Код нужно отправить боту командой /start <код> в течение
    telegram_link.CODE_TTL_MINUTES минут.
    """
    record = create_link_code(db, org_id)
    return TelegramLinkCodeOut(code=record.code, expires_at=record.expires_at)
