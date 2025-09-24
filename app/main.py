from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware import Middleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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

# Routers & static
insight_app.include_router(auth_router)
insight_app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja templates setup
templates = Jinja2Templates(directory="templates")
templates.env.globals["root_path"] = "/insight/"


@insight_app.get("/")
async def insight_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


# -----------------------------------------------------------------------------
# Root App (exposed via uvicorn and NGINX)
# -----------------------------------------------------------------------------
main_app = FastAPI()

# Mount InsightHub at /insight
main_app.mount("/insight", insight_app)


@main_app.get("/")
async def health_check():
    return {"status": "InsightHub is running"}
