# РТО-аналитика — MVP

SaaS для мелких автоперевозчиков (ИП с 1–20 машинами): учёт автопарка,
контроль режима труда и отдыха (РТО) водителей, генерация путевых листов,
напоминания через Telegram.

## Стек

- Backend: FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL 16
- Frontend: Next.js 14 (App Router) + TypeScript + Tailwind
- Фоновые задачи: Celery + Redis
- Оркестрация: Docker Compose (backend, frontend, postgres, redis, nginx)

## Быстрый старт

```bash
cp .env.example .env
docker compose up --build
```

- Backend: http://localhost:8000/health
- Frontend: http://localhost:3000
- Через nginx: http://localhost/

Локальный запуск бэкенда без Docker:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest
```

## Структура

```
backend/app/
  models/     — SQLAlchemy-модели (Organization, Vehicle, Driver, Trip, ...)
  schemas/    — Pydantic-схемы запросов/ответов
  api/routes/ — REST-эндпоинты
  services/   — бизнес-логика (RtoCalculator — ядро продукта)
frontend/app/ — Next.js App Router
```

## ⚠️ Открытые вопросы, требующие ручной проверки перед продом

1. **Нормативы РТО** (`backend/app/services/rto_rules.py`) — используются
   заглушечные цифры, НЕ сверенные с приказом Минтранса, действующим с
   01.09.2026. Обязательно проверить по официальному источнику перед тем,
   как показывать пользователям реальные нарушения.
2. **Форма путевого листа** — не реализована, нужно определить актуальный
   утверждённый бланк (грузовой транспорт) перед вёрсткой PDF-шаблона.
3. **SMS-агрегатор** для входа по телефону — не выбран (сравнить SMS.ru,
   Devino, SMSC). Аутентификация в MVP-скелете пока не реализована.
4. **Формат CSV/Excel с тахографа** — уточнить у пилотных клиентов перед
   реализацией импорта WorkTimeEntry.

## Статус реализации (по спринтам из ТЗ)

- [x] Спринт 1 (частично): каркас FastAPI/Next.js/Docker Compose, модели
      данных, CRUD для Vehicle/Driver/Trip (без аутентификации — заглушка
      через заголовок `X-Organization-Id`)
- [x] Спринт 3 (частично): `RtoCalculator` с юнит-тестами на заглушечных
      нормативах — требует сверки цифр перед продом
- [ ] Аутентификация по SMS, дашборд "светофор", импорт CSV, PDF путевых
      листов, Telegram-бот, ЮKassa — не реализованы
