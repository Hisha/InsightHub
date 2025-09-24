from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware import Middleware

from app.middleware import AuthMiddleware
from app.auth import router as auth_router
from app.utils.security import SESSION_SECRET

# Define app with middleware list (ensures correct order)
middleware = [
    Middleware(SessionMiddleware, secret_key=SESSION_SECRET),
    Middleware(AuthMiddleware),
]

app = FastAPI(middleware=middleware)

# Mount routes and static files
app.include_router(auth_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --------------------------------------------------------------------
# Templates & Globals
# --------------------------------------------------------------------
templates = Jinja2Templates(directory="templates")
templates.env.globals["root_path"] = app.root_path


@app.get("/")
async def home():
    return {"message": "Welcome to InsightHub. You're logged in."}

@app.get("/debug")
async def debug_root_path(request: Request):
    return {"root_path": request.scope.get("root_path", ""), "path": request.url.path}
