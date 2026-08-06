from app.database import SessionLocal

from app.models.user_model import User

from app.auth import hash_password


db = SessionLocal()

admin = User(
    username="admin",
    password_hash=hash_password("Admin123!"),
    role="gestionnaire"
)

db.add(admin)

db.commit()

print("Utilisateur admin créé")