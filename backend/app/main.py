import os
from pathlib import Path

from alembic import command
from alembic.config import Config

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.auth import WebAuthRequired

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


# CORS : l'UI Jinja2 est servie en same-origin (pas besoin de CORS).
# À renseigner via CORS_ALLOWED_ORIGINS uniquement pour d'éventuels
# clients API externes (intégrations, scripts...).
allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        ""
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Redirige vers la page de connexion quand une page Jinja2 est visitée
# sans session cookie valide (voir app.auth.get_current_user_web)
@app.exception_handler(WebAuthRequired)
def handle_web_auth_required(request: Request, exc: WebAuthRequired):

    return RedirectResponse(
        url=f"/login?next={exc.next_path}",
        status_code=303
    )


# Applique les migrations Alembic (crée le schéma s'il n'existe pas
# encore, ou le met à niveau sinon). Remplace l'ancien
# Base.metadata.create_all() : le schéma est désormais versionné dans
# alembic/versions/ au lieu de scripts de migration ponctuels.
BACKEND_DIR = Path(__file__).resolve().parent.parent

alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
command.upgrade(alembic_cfg, "head")


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