import logging
import os
from pathlib import Path

from alembic import command
from alembic.config import Config

from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth import WebAuthRequired

logger = logging.getLogger("rfid_printing")

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


error_templates = Jinja2Templates(directory="app/templates")


def _is_api_route(request: Request) -> bool:

    path = request.url.path

    return path.startswith("/api/") or path.startswith("/auth/")


# Format d'erreur cohérent : JSON pour l'API (comportement par défaut de
# FastAPI), page HTML à l'identique du reste de l'UI pour les pages
# Jinja2 (qui, sans ce handler, recevaient elles aussi du JSON brut).
@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):

    if _is_api_route(request):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers
        )

    return error_templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "status_code": exc.status_code,
            "detail": exc.detail
        },
        status_code=exc.status_code
    )


# Filet de sécurité pour toute exception non prévue : jamais de
# traceback exposé au client, toujours tracée côté serveur.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):

    logger.exception(
        "Erreur non gérée sur %s %s",
        request.method,
        request.url.path
    )

    detail = "Une erreur inattendue est survenue."

    if _is_api_route(request):
        return JSONResponse(
            status_code=500,
            content={"detail": detail}
        )

    return error_templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "status_code": 500,
            "detail": detail
        },
        status_code=500
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