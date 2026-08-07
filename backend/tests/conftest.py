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


class client(TestClient):
    def __init__(self, app):
        super().__init__(app)

    def request(self, method, url, **kwargs):
        return super().request(method, url, **kwargs)

    def get(self, url, **kwargs):
        return super().get(url, **kwargs)

    def post(self, url, **kwargs):
        return super().post(url, **kwargs)

    def put(self, url, **kwargs):
        return super().put(url, **kwargs)

    def patch(self, url, **kwargs):
        return super().patch(url, **kwargs)

    def delete(self, url, **kwargs):
        return super().delete(url, **kwargs)

    def options(self, url, **kwargs):
        return super().options(url, **kwargs)

    def head(self, url, **kwargs):
        return super().head(url, **kwargs)

    def trace(self, url, **kwargs):
        return self.request("TRACE", url, **kwargs)

    def close(self):
        super().close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def request_json(self, method, url, json=None, headers=None, **kwargs):
        headers = {} if headers is None else dict(headers)
        headers.setdefault("Content-Type", "application/json")
        return self.request(method, url, json=json, headers=headers, **kwargs)

    def post_json(self, url, json=None, headers=None, **kwargs):
        return self.request_json("POST", url, json=json, headers=headers, **kwargs)

    def put_json(self, url, json=None, headers=None, **kwargs):
        return self.request_json("PUT", url, json=json, headers=headers, **kwargs)

    def patch_json(self, url, json=None, headers=None, **kwargs):
        return self.request_json("PATCH", url, json=json, headers=headers, **kwargs)

    def delete_json(self, url, json=None, headers=None, **kwargs):
        return self.request_json("DELETE", url, json=json, headers=headers, **kwargs)

    def auth_headers(self, token: str):
        return {"Authorization": f"Bearer {token}"}


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
        role="employe"
    )

    db.add(user)
    db.commit()

    yield user

    db.close()


@pytest.fixture
def client():

    with TestClient(app) as client:
        yield client