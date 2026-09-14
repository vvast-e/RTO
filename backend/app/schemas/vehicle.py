import re
import uuid

from pydantic import BaseModel, field_validator

from app.models.vehicle import VehicleStatus

# Форматы гос. номеров РФ: А000АА00, А000АА000, АА000077 (транзит) и т.п.
# Базовая проверка под легковой/грузовой формат "буква-3цифры-2буквы-регион(2-3цифры)".
PLATE_RE = re.compile(
    r"^[АВЕКМНОРСТУХABEKMHOPCTYX]\d{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\d{2,3}$",
    re.IGNORECASE,
)


class VehicleBase(BaseModel):
    plate_number: str
    brand_model: str
    tachograph_type: str | None = None
    status: VehicleStatus = VehicleStatus.active

    @field_validator("plate_number")
    @classmethod
    def validate_plate(cls, v: str) -> str:
        normalized = v.strip().upper().replace(" ", "")
        if not PLATE_RE.match(normalized):
            raise ValueError(
                "Некорректный формат гос. номера РФ (ожидается, например, А000АА00)"
            )
        return normalized


class VehicleCreate(VehicleBase):
    pass


class VehicleOut(VehicleBase):
    id: uuid.UUID

    class Config:
        from_attributes = True
