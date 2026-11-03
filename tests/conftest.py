"""Shared test setup. Tests run against their own database, built by the real migrations."""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.orm import Session

from app.db.models import Category, Product
from app.db.session import get_session
from app.main import app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://ebag:ebag@localhost:5433/products_test")
engine = create_engine(TEST_DATABASE_URL)


def create_database_if_missing() -> None:
    url = make_url(TEST_DATABASE_URL)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists = connection.scalar(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database})
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def database():
    """Once per run: start from an empty database and apply the migrations."""
    create_database_if_missing()
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        config = Config(Path(__file__).parent.parent / "alembic.ini")
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


@pytest.fixture
def session():
    """A database session for one test; the tables are emptied afterwards."""
    with Session(engine, expire_on_commit=False) as session:
        yield session
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE products, categories RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    """The whole app over HTTP, with each request getting a session on the test database."""

    def test_session():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def catalog(session):
    """A small catalogue, with prices in cents:

    food                        drinks
    └── dairy                   ├── watr-015  Mineral water 1.5 l      99
        ├── milk-001  249       └── natu-001  Milk drink 100% natural  150
        ├── yogh-400  389
        └── cheese
            └── chee-200  599
    """
    food = Category(name="food")
    drinks = Category(name="drinks")
    session.add_all([food, drinks])
    session.flush()
    dairy = Category(name="dairy", parent_id=food.id)
    session.add(dairy)
    session.flush()
    cheese = Category(name="cheese", parent_id=dairy.id)
    session.add(cheese)
    session.flush()

    session.add_all(
        [
            Product(sku="milk-001", title="Fresh milk 1 l", price=249, category_id=dairy.id),
            Product(sku="yogh-400", title="Greek yogurt 400 g", price=389, category_id=dairy.id),
            Product(sku="chee-200", title="Cheddar cheese 200 g", price=599, category_id=cheese.id),
            Product(sku="watr-015", title="Mineral water 1.5 l", price=99, category_id=drinks.id),
            Product(sku="natu-001", title="Milk drink 100% natural", price=150, category_id=drinks.id),
        ]
    )
    session.commit()
    return {"food": food.id, "drinks": drinks.id, "dairy": dairy.id, "cheese": cheese.id}
