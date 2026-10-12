from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.routes.auth import require_auth

BASE_DIR = Path(__file__).resolve().parents[2]
router = APIRouter(dependencies=[Depends(require_auth)])
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/")
@router.get("/dashboard")
def index():
    return RedirectResponse("/dashboard/campaigns")


@router.get("/dashboard/settings")
def settings(request: Request):
    return templates.TemplateResponse(request, "settings.html", {"page": "settings"})


@router.get("/dashboard/campaigns")
def campaigns(request: Request):
    return templates.TemplateResponse(request, "campaigns.html", {"page": "campaigns"})
