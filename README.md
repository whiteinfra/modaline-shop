# ModaLine Shop — клієнт-серверний застосунок для роботи з БД

[![CI](https://github.com/whiteinfra/modaline-shop/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/whiteinfra/modaline-shop/actions/workflows/ci.yml)

Лабораторна робота № 8 з дисципліни «Технології створення програмних продуктів».
Предметна область — **продажі в інтернет-магазині** (індивідуальне завдання № 6): товари, клієнти, замовлення, платежі.

**Виконавець:** Білоус Владислав, група К-41 (усі ролі: Team Lead, Backend, Frontend, DBA/DevOps, QA).

## Стек

| Рівень | Технології |
|---|---|
| Сервер | Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2, Pydantic 2 |
| БД | PostgreSQL 16, SQL-міграції (`backend/migrations`) |
| Автентифікація | JWT (PyJWT), паролі bcrypt, OAuth2 Bearer |
| Клієнт | SPA: HTML + Vanilla JS + Bootstrap 5 (`frontend/`) |
| Документація API | Swagger UI — `/docs`, OpenAPI — `/openapi.json` |
| Тести | pytest + FastAPI TestClient (10 інтеграційних тестів) |
| Запуск | Docker Compose (`db` + `api`) |

## Швидкий запуск (Docker)

```bash
docker compose up --build
```

- Клієнт: <http://localhost:8000/>
- Swagger UI: <http://localhost:8000/docs>
- Демо-акаунти: `manager@modaline.ua` / `Manager123!`, `admin@modaline.ua` / `Admin123!`

Під час старту контейнер `api` чекає на БД, застосовує міграції (`python migrate.py`) і запускає сервер.

## Локальний запуск без Docker

```bash
cd backend
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
createdb modaline_shop                               # або через pgAdmin
export DATABASE_URL=postgresql+psycopg://shop:shop@localhost:5432/modaline_shop   # Windows: set DATABASE_URL=...
python migrate.py                                    # 001_init.sql + 002_seed.sql
uvicorn app.main:app --reload --port 8000
```

## Тести

```bash
cd backend
pytest -v                                            # SQLite у пам'яті (швидко)
TEST_DATABASE_URL=postgresql+psycopg://shop:shop@localhost:5432/modaline_test pytest -v   # з PostgreSQL і міграціями
```

## Якість коду: CI і автовиправлення

- **GitHub Actions** (`.github/workflows/ci.yml`): завдання `lint` (`ruff check`, `ruff format --check`) і `test` (`pytest` на PostgreSQL 16) виконуються паралельно, після них — `docker` (`docker compose up --build` з перевіркою `/api/health`).
- **Автовиправлення** (`.github/workflows/autofix.yml`): на гілках `feature/*` і `hotfix/*` запускає pre-commit і сам комітить виправлення стилю.
- **Локально** — ті самі перевірки перед кожним комітом:

```bash
pip install pre-commit
pre-commit install            # хуки: ruff --fix, ruff format, пробіли, кінці рядків, YAML/JSON
pre-commit run --all-files    # разова перевірка всього репозиторію
```

## REST API

| Метод | Шлях | Опис | Авторизація |
|---|---|---|---|
| POST | `/api/auth/register` | Реєстрація співробітника | — |
| POST | `/api/auth/login` | Вхід (JSON), повертає JWT | — |
| POST | `/api/auth/token` | Вхід (OAuth2 form) для Swagger | — |
| GET | `/api/auth/me` | Поточний користувач | Bearer |
| GET | `/api/products?search=&category=&size=&min_price=&max_price=&in_stock=&sort=&page=&limit=` | Каталог з фільтрами й пагінацією | — |
| GET | `/api/products/{id}`, `/api/products/categories` | Товар, категорії | — |
| POST / PUT / DELETE | `/api/products`, `/api/products/{id}` | Створення, оновлення, видалення товару | Bearer |
| GET / POST | `/api/customers?search=&city=&page=&limit=` | Клієнти: список, створення | Bearer |
| GET / PUT / DELETE | `/api/customers/{id}` | Клієнт | Bearer |
| GET / POST | `/api/orders?status=&customer_id=&page=&limit=` | Замовлення (створення списує залишки) | Bearer |
| GET / PUT / DELETE | `/api/orders/{id}` | Замовлення, зміна статусу, видалення | Bearer |
| GET / POST | `/api/payments?order_id=&status=` | Платежі (успішна оплата → статус `paid`) | Bearer |
| GET / PUT / DELETE | `/api/payments/{id}` | Платіж | Bearer |
| GET | `/api/stats` | Показники для дашборду | Bearer |
| GET | `/api/health` | Перевірка стану | — |

Коди помилок: `400` — бізнес-правило (неможливий перехід статусу), `401` — немає або недійсний токен, `404` — не знайдено, `409` — конфлікт (дублікат SKU/email, недостатньо товару), `422` — помилка валідації.

### Приклади запитів (curl)

```bash
# 1. Вхід і отримання токена
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login -H "Content-Type: application/json" \
  -d '{"email":"manager@modaline.ua","password":"Manager123!"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2. Каталог із фільтрами та пагінацією
curl -s "localhost:8000/api/products?category=%D0%A5%D1%83%D0%B4%D1%96&in_stock=true&sort=-price&page=1&limit=2"

# 3. Створення клієнта (потрібен токен)
curl -s -X POST localhost:8000/api/customers -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"full_name":"Ігор Бондар","email":"igor.b@gmail.com","phone":"+380991112233","city":"Київ"}'

# 4. Замовлення: позиції + автоматичний розрахунок суми і списання залишків
curl -s -X POST localhost:8000/api/orders -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"customer_id":1,"items":[{"product_id":5,"quantity":1},{"product_id":2,"quantity":2}]}'

# 5. Оплата замовлення
curl -s -X POST localhost:8000/api/payments -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"order_id":7,"amount":2088,"method":"card"}'
```

Приклад відповіді `GET /api/products/5`:

```json
{"sku": "HD-BAS-M-GR", "name": "Худі оверсайз «Basic»", "category": "Худі", "size": "M", "color": "сірий",
 "price": 1290.0, "stock": 7, "description": "Футер з начосом", "id": 5, "created_at": "2026-10-11T20:59:00"}
```

## Модель даних

Шість таблиць: `users`, `customers`, `products`, `orders`, `order_items`, `payments` (ER-діаграма — `docs/er.png`).
Обмеження цілісності: PK/FK, `UNIQUE` (sku, email), `CHECK` (ціна > 0, залишок ≥ 0, статуси).

## Структура репозиторію

```
modaline-shop/
├─ backend/
│  ├─ app/            # FastAPI: main.py, models.py, schemas.py, security.py, routers/
│  ├─ migrations/     # 001_init.sql, 002_seed.sql
│  ├─ tests/          # pytest
│  ├─ migrate.py      # застосування міграцій
│  ├─ requirements.txt
│  └─ Dockerfile
├─ frontend/          # index.html, app.js, styles.css, vendor/bootstrap
├─ docs/              # ER-діаграма, архітектура, презентація проєкту (.pptx)
├─ .github/workflows/  # CI (ci.yml) і автовиправлення (autofix.yml)
├─ .pre-commit-config.yaml, ruff.toml, .editorconfig
├─ docker-compose.yml
└─ README.md
```
