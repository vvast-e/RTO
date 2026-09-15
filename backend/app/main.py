import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Без этого корневой логгер молчит на уровне INFO, и заглушки вроде
# ConsoleSmsSender/ConsoleReminderSender (см. app/services/sms.py,
# app/services/reminder_sender.py) не печатают код/напоминание никуда —
# в тестах это незаметно (pytest caplog перехватывает логи независимо от
# хендлеров), а при локальном запуске просто исчезает.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from app.api.routes import (
    auth,
    vehicles,
    drivers,
    trips,
    worktime,
    violations,
    waybills,
    reminders,
    organizations,
    telegram,
    subscriptions,
)

app = FastAPI(title="RTO-аналитика API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: сузить до домена фронтенда перед продом
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(vehicles.router)
app.include_router(drivers.router)
app.include_router(trips.router)
app.include_router(worktime.router)
app.include_router(violations.router)
app.include_router(waybills.router)
app.include_router(reminders.router)
app.include_router(organizations.router)
app.include_router(telegram.router)
app.include_router(subscriptions.router)


@app.get("/health")
def health():
    return {"status": "ok"}
