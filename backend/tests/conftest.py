import shutil

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastapi.testclient import TestClient

from app.main import app
from app.database import Base
from app.database import get_db

from app.models.user_model import User
from app.auth import hash_password
from app.services.backup_service import BASE_DIR


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

TEST_BACKUP_DIR = BASE_DIR / "backups" / "test_rfid"


@pytest.fixture(autouse=True)
def setup_database():

    Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def cleanup_backup_dir():
    """
    Les imports CSV déclenchent une sauvegarde automatique (voir
    app.services.backup_service) qui écrit de vrais fichiers sur
    disque, en dehors de la base de test elle-même. Isole chaque test
    en vidant ce dossier avant/après, quel que soit le fichier de test
    qui déclenche l'import.
    """

    if TEST_BACKUP_DIR.exists():
        shutil.rmtree(TEST_BACKUP_DIR)

    yield

    if TEST_BACKUP_DIR.exists():
        shutil.rmtree(TEST_BACKUP_DIR)


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