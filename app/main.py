from fastapi import FastAPI, Request, UploadFile, File
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware import Middleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import os, shutil
import pandas as pd

from app.middleware import AuthMiddleware
from app.auth import router as auth_router
from app.utils.security import SESSION_SECRET

# -----------------------------------------------------------------------------
# InsightHub Sub-App (mounted at /insight)
# -----------------------------------------------------------------------------
middleware = [
    Middleware(SessionMiddleware, secret_key=SESSION_SECRET),
    Middleware(AuthMiddleware),
]

insight_app = FastAPI(middleware=middleware)

insight_app.include_router(auth_router)
insight_app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
templates.env.globals["root_path"] = "/insight/"

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# GETS
# -----------------------------------------------------------------------------

# INDEX PAGE — secured
@insight_app.get("/")
async def insight_index(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/insight/login", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

# -----------------------------------------------------------------------------
# POSTS
# -----------------------------------------------------------------------------

@insight_app.post("/parse_with_header")
async def parse_with_header(request: Request, filename: str = Form(...), header_row: int = Form(...)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/insight/login", status_code=303)

    try:
        file_path = os.path.join(UPLOAD_DIR, filename)

        # header=header_row-1 makes that row the header
        # skiprows=range(header_row-1) skips everything before the header
        df = pd.read_excel(
            file_path,
            header=0,
            skiprows=range(header_row - 1),
            engine="openpyxl"
        )

        cleaned_html = df.head(20).to_html(classes="excel-preview", index=False)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user": user,
                "message": f"Parsed '{filename}' with headers from row {header_row}",
                "preview_table": cleaned_html
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user": user,
                "error": f"Header parsing failed: {str(e)}"
            }
        )

# FILE UPLOAD HANDLER
@insight_app.post("/upload")
async def upload_excel(request: Request, file: UploadFile = File(...)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/insight/login", status_code=303)

    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Load WITHOUT headers (so we show all raw rows)
        df_raw = pd.read_excel(file_path, header=None, engine="openpyxl")
        preview_html = df_raw.head(10).to_html(classes="raw-preview", index=True, header=False)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user": user,
                "message": f"File '{file.filename}' uploaded successfully!",
                "raw_preview": preview_html,
                "uploaded_filename": file.filename
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "user": user, "error": f"Upload failed: {str(e)}"}
        )

# -----------------------------------------------------------------------------
# Root App (exposed via uvicorn and NGINX)
# -----------------------------------------------------------------------------
main_app = FastAPI()

# Mount InsightHub at /insight
main_app.mount("/insight", insight_app)

# Redirect root (/) to /insight/
@main_app.get("/")
async def redirect_root():
    return RedirectResponse(url="/insight/", status_code=303)
