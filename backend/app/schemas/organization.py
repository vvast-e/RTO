from datetime import datetime

from pydantic import BaseModel


class TelegramLinkCodeOut(BaseModel):
    code: str
    expires_at: datetime


class OrganizationMeOut(BaseModel):
    name: str
    telegram_linked: bool
