from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from app.middleware import auth_middleware
from app.auth import router as auth_router
from app.utils.security import SESSION_SECRET

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.middleware("http")(auth_middleware)

app.include_router(auth_router)

# Static files (favicon, css, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount the insight app under a subpath
main_app = FastAPI()
main_app.mount("/insight", insight_app)

@app.get("/")
async def home():
    return {"message": "Welcome to InsightHub. You're logged in."}
