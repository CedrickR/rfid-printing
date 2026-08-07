import os

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base
from app.database import engine

from app.auth import WebAuthRequired

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


# CORS : origines autorisées pour le frontend (configurable via env)
allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
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