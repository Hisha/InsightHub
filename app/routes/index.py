from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import os, shutil

templates = Jinja2Templates(directory="templates")
router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

PREFIX = "/insight"

@router.get(f"{PREFIX}/")
async def index(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@router.post(f"{PREFIX}/upload")
async def upload_excel(request: Request, file: UploadFile = File(...)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "user": user, "message": f"File '{file.filename}' uploaded successfully!"}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "user": user, "error": f"Upload failed: {str(e)}"}
        )
