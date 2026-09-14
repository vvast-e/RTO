from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth,
    vehicles,
    drivers,
    trips,
    worktime,
    violations,
    reminders,
    organizations,
    telegram,
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
app.include_router(reminders.router)
app.include_router(organizations.router)
app.include_router(telegram.router)


@app.get("/health")
def health():
    return {"status": "ok"}
