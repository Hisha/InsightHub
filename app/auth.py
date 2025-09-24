from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.utils.security import verify_credentials

templates = Jinja2Templates(directory="templates")
PREFIX = "/insight"
router = APIRouter()


@router.get("/login")
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    if verify_credentials(username, password):
        request.session["user"] = username
        return RedirectResponse(url=f"{PREFIX}/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url=f"{PREFIX}/login", status_code=303)
