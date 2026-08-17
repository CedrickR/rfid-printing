import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastapi.testclient import TestClient

from app.main import app
from app.database import Base
from app.database import get_db

from app.models.user_model import User
from app.auth import hash_password


TEST_DATABASE_URL = "sqlite:///./test_rfid.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={
        "check_same_thread": False
    }
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def override_get_db():
    db = TestingSessionLocal()

    try:
        yield db

    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():

    Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def admin_user():

    db = TestingSessionLocal()

    user = User(
        username="admin",
        password_hash=hash_password(
            "Admin123!"
        ),
        role="administrateur"
    )

    db.add(user)
    db.commit()

    yield user

    db.close()


@pytest.fixture
def manager_user():

    db = TestingSessionLocal()

    user = User(
        username="gestionnaire",
        password_hash=hash_password(
            "Gestionnaire123!"
        ),
        role="gestionnaire"
    )

    db.add(user)
    db.commit()

    yield user

    db.close()


@pytest.fixture
def standard_user():

    db = TestingSessionLocal()

    user = User(
        username="employe",
        password_hash=hash_password(
            "Employe123!"
        ),
        role="lecteur"
    )

    db.add(user)
    db.commit()

    yield user

    db.close()


@pytest.fixture
def client():

    with TestClient(app) as client:
        yield client