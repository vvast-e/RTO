import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization_id
from app.db.session import get_db
from app.models.reminder import Reminder, ReminderType
from app.schemas.reminder import ReminderCreate, ReminderOut
from app.services.reminder_sender import TelegramChatNotLinkedError, get_reminder_sender
from app.services.reminder_service import send_reminder as send_reminder_via_sender

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderOut])
def list_reminders(
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
    sent: bool | None = None,
    type: ReminderType | None = None,
    skip: int = 0,
    limit: int = 50,
):
    stmt = select(Reminder).where(Reminder.organization_id == org_id)
    if sent is not None:
        stmt = stmt.where(Reminder.sent == sent)
    if type is not None:
        stmt = stmt.where(Reminder.type == type)
    stmt = stmt.order_by(Reminder.target_date).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


@router.post("", response_model=ReminderOut, status_code=201)
def create_reminder(
    payload: ReminderCreate,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    reminder = Reminder(organization_id=org_id, **payload.model_dump())
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.post("/{reminder_id}/send", response_model=ReminderOut)
def send_reminder(
    reminder_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    reminder = db.get(Reminder, reminder_id)
    if reminder is None or reminder.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Напоминание не найдено")

    sender = get_reminder_sender()
    try:
        return send_reminder_via_sender(db, reminder, sender)
    except TelegramChatNotLinkedError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
