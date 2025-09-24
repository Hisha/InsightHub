from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

from app.middleware import auth_middleware
from app.auth import router as auth_router
from app.utils.security import SESSION_SECRET

# Single unified app (mounted at / in FastAPI, but accessed via /insight due to nginx rewrite)
app = FastAPI()

# Middleware and route setup
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.middleware("http")(auth_middleware)
app.include_router(auth_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def home():
    return {"message": "Welcome to InsightHub. You're logged in."}
