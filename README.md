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
alembic upgrade head
uvicorn app.main:app --reload
pytest
```

Применение миграций к БД (после `docker compose up -d postgres` либо на
локальном Postgres 16):

```bash
cd backend
alembic upgrade head
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
3. **SMS-агрегатор** для входа по телефону — окончательно не выбран
   (сравнить SMS.ru, Devino, SMSC). Реализован абстрактный `SmsSender`
   (`backend/app/services/sms.py`) с дефолтной реализацией под SMS.ru
   (`SMS_PROVIDER=smsru`, нужен `SMS_API_KEY`) и консольной заглушкой для
   разработки/тестов (`SMS_PROVIDER=console` или не задан — код просто
   логируется). Смена агрегатора — добавить ещё один класс `SmsSender` и
   ветку в `get_sms_sender()`.
4. **Формат CSV/Excel с тахографа** — уточнить у пилотных клиентов перед
   реализацией импорта WorkTimeEntry.

## Аутентификация

Вход и регистрация организации — по номеру телефона через одноразовый
SMS-код (см. `backend/app/api/routes/auth.py`):

- `POST /api/auth/register/request-code`, `POST /api/auth/register/confirm`
  — регистрация новой организации + первого пользователя (роль `owner`).
- `POST /api/auth/login/request-code`, `POST /api/auth/login/confirm`
  — вход существующего пользователя.
- `POST /api/auth/refresh` — обновление пары токенов по refresh-токену.

Выдаётся пара JWT: access (`ACCESS_TOKEN_EXPIRE_MINUTES`, payload
`{sub: user_id, organization_id, role}`) и refresh
(`REFRESH_TOKEN_EXPIRE_DAYS`). Защищённые эндпоинты требуют заголовок
`Authorization: Bearer <access_token>` — заглушка `X-Organization-Id`
удалена, `get_current_organization_id`/`get_current_user` в
`backend/app/api/deps.py` теперь реально проверяют JWT.

Антиабьюз (`backend/app/services/auth_service.py`): повторную отправку
кода на один номер можно запросить не чаще раза в 60 секунд; на ввод кода
даётся 5 попыток, после чего код инвалидируется и нужно запросить новый;
код действует 5 минут.

Фронтенд (`frontend/app/login/page.tsx`) хранит токены в `localStorage`
(решение задокументировано в `frontend/lib/auth.ts`) и редиректит на
`/login` при отсутствии токена через `frontend/components/AuthGuard.tsx`,
подключённый в корневом layout.

## Статус реализации (по спринтам из ТЗ)

- [x] Спринт 1 (частично): каркас FastAPI/Next.js/Docker Compose, модели
      данных, CRUD для Vehicle/Driver/Trip
- [x] Аутентификация по SMS-коду (JWT access/refresh, rate limiting,
      минимальный фронтенд входа/регистрации) — см. раздел выше
- [x] Спринт 3 (частично): `RtoCalculator` с юнит-тестами на заглушечных
      нормативах — требует сверки цифр перед продом
- [ ] Дашборд "светофор", импорт CSV, PDF путевых листов, Telegram-бот,
      ЮKassa — не реализованы
