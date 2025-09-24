from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

# Hardcoded prefix for now (switch to root_path later if Nginx passes it)
PREFIX = "/insight"

# Any paths under these should bypass login checks
EXEMPT_PATHS = [
    "/login",       # login page
    "/static",      # css, js, images
    "/favicon.ico", # favicon
]

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow exempt paths under PREFIX
        for exempt in EXEMPT_PATHS:
            if path == f"{PREFIX}{exempt}" or path.startswith(f"{PREFIX}{exempt}/"):
                return await call_next(request)

        # Check session for user
        if not request.session.get("user"):
            return RedirectResponse(f"{PREFIX}/login", status_code=303)

        return await call_next(request)
