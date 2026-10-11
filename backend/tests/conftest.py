"""Тестове середовище.
За замовчуванням — SQLite у пам'яті (схема з ORM-моделей).
Якщо задано TEST_DATABASE_URL (PostgreSQL) — схема створюється SQL-міграцією 001_init.sql,
тобто тести перевіряють і міграції."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

TEST_URL = os.getenv("TEST_DATABASE_URL")
TABLES = "payments, order_items, orders, products, customers, users"

if TEST_URL:
    import migrate

    engine = create_engine(TEST_URL)
    with engine.begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    migrate.apply(TEST_URL, seed=False, verbose=False)
else:
    from sqlalchemy import event

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _unicode_lower(dbapi_conn, _):  # SQLite lower() не працює з кирилицею
        dbapi_conn.create_function("lower", 1, lambda s: s.lower() if isinstance(s, str) else s)

    Base.metadata.create_all(engine)

TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db


@pytest.fixture(autouse=True)
def clean_db():
    with engine.begin() as c:
        if TEST_URL:
            c.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
        else:
            for t in TABLES.split(", "):
                c.execute(text(f"DELETE FROM {t}"))
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth(client):
    client.post(
        "/api/auth/register",
        json={"email": "tester@modaline.ua", "password": "Passw0rd!", "full_name": "Тест Тестович"},
    )
    r = client.post("/api/auth/login", json={"email": "tester@modaline.ua", "password": "Passw0rd!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def product(client, auth):
    def make(sku="HD-BAS-L-GR", price=1290, stock=5, **kw):
        body = {
            "sku": sku,
            "name": kw.get("name", "Худі оверсайз"),
            "category": kw.get("category", "Худі"),
            "size": kw.get("size", "L"),
            "color": "сірий",
            "price": price,
            "stock": stock,
        }
        r = client.post("/api/products", json=body, headers=auth)
        assert r.status_code == 201, r.text
        return r.json()

    return make


@pytest.fixture
def customer(client, auth):
    r = client.post(
        "/api/customers",
        json={"full_name": "Ірина Петренко", "email": "iryna@example.com", "phone": "+380671234567", "city": "Київ"},
        headers=auth,
    )
    assert r.status_code == 201, r.text
    return r.json()
