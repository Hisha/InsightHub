from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

from app.middleware import auth_middleware
from app.auth import router as auth_router
from app.utils.security import SESSION_SECRET

# Create the sub-app first (InsightHub's core functionality)
insight_app = FastAPI()

# Middleware and routes for InsightHub
insight_app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
insight_app.middleware("http")(auth_middleware)
insight_app.include_router(auth_router)
insight_app.mount("/static", StaticFiles(directory="static"), name="static")

# Root app that mounts InsightHub at /insight
main_app = FastAPI()
main_app.mount("/insight", insight_app)

@app.get("/")
async def home():
    return {"message": "Welcome to InsightHub. You're logged in."}
