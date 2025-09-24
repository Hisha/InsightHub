from fastapi import FastAPI, Request, UploadFile, File
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware import Middleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import os, shutil

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

# INDEX PAGE — secured
@insight_app.get("/")
async def insight_index(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/insight/login", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

# FILE UPLOAD HANDLER
@insight_app.post("/upload")
async def upload_excel(request: Request, file: UploadFile = File(...)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/insight/login", status_code=303)

    try:
        # Save the file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Parse with pandas (only first sheet)
        df = pd.read_excel(file_path, engine="openpyxl")
        preview_html = df.head(10).to_html(classes="excel-preview", index=False)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user": user,
                "message": f"File '{file.filename}' uploaded successfully!",
                "preview_table": preview_html,
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
