class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if any(path.startswith(p) for p in ["/login", "/static", "/favicon.ico"]):
            return await call_next(request)

        if not request.session.get("user"):
            return RedirectResponse(url="/insight/login", status_code=303)

        return await call_next(request)
