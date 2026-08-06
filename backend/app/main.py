from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base
from app.database import engine

# Chargement des modèles
from app.models.user_model import User
from app.models.import_model import Import
from app.models.asset_model import Asset
from app.models.print_job_model import PrintJob
from app.models.print_job_line_model import PrintJobLine
from app.models.print_history_model import PrintHistory

# Routeurs API
from app.routers.auth_router import router as auth_router
from app.routers.import_router import router as import_router
from app.routers.print_router import router as print_router
from app.routers.history_router import router as history_router
from app.routers.dashboard_router import router as dashboard_router

# Routeur Web (Jinja2)
from app.routers.web_router import router as web_router


# Création de l'application FastAPI
app = FastAPI(
    title="RFID Printing API",
    version="0.2"
)


# Création des tables SQLite
Base.metadata.create_all(
    bind=engine
)


# Répertoire des fichiers statiques
app.mount(
    "/static",
    StaticFiles(
        directory="app/static"
    ),
    name="static"
)


# Routeurs API
app.include_router(auth_router)
app.include_router(import_router)
app.include_router(print_router)
app.include_router(history_router)
app.include_router(dashboard_router)

# Interface Web
app.include_router(web_router)


@app.get("/")
def root():

    return {
        "application": "RFID PRINTING",
        "version": "0.2",
        "status": "running"
    }