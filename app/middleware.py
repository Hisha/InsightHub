from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

EXEMPT_PATHS = ["/login", "/static", "/favicon.ico"]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        root = request.scope.get("root_path", "")

        if any(path.startswith(p) for p in EXEMPT_PATHS):
            return await call_next(request)

        if not request.session.get("user"):
            return RedirectResponse(url=f"{root}/login")

        return await call_next(request)
