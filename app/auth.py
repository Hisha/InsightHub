from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.utils.security import verify_credentials

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/login")
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@router.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    if verify_credentials(username, password):
        request.session["user"] = username
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    root = request.scope.get("root_path", "")
    return RedirectResponse(url=f"{root}/login", status_code=303)
