from fastapi import Request
from fastapi.responses import RedirectResponse

EXEMPT_PATHS = ["/login", "/static", "/favicon.ico"]

async def auth_middleware(request: Request, call_next):
    for path in EXEMPT_PATHS:
        if request.url.path.startswith(path):
            return await call_next(request)

    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    return await call_next(request)
