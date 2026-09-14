import re

from pydantic import BaseModel, field_validator

PHONE_RE = re.compile(r"^\+7\d{10}$")


class PhoneRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        normalized = v.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if normalized.startswith("8") and len(normalized) == 11:
            normalized = "+7" + normalized[1:]
        if not PHONE_RE.match(normalized):
            raise ValueError(
                "Некорректный номер телефона, ожидается формат +7XXXXXXXXXX"
            )
        return normalized


class RegisterConfirmRequest(PhoneRequest):
    code: str
    organization_name: str
    user_name: str


class LoginConfirmRequest(PhoneRequest):
    code: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
