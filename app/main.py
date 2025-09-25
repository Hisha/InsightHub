from fastapi import FastAPI, Request, UploadFile, File, Form
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware import Middleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import os, shutil
import pandas as pd
from app.db import slugify, insert_uploaded_file_metadata, insert_dynamic_table, engine
from sqlalchemy import text
from app.middleware import AuthMiddleware
from app.auth import router as auth_router
from app.utils.security import SESSION_SECRET
from datetime import datetime

middleware = [
    Middleware(SessionMiddleware, secret_key=SESSION_SECRET),
    Middleware(AuthMiddleware),
]

insight_app = FastAPI(middleware=middleware)

insight_app.include_router(auth_router)
insight_app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
templates.env.globals["root_path"] = "/insight/"
templates.env.globals["current_year"] = datetime.now().year

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@insight_app.get("/")
async def insight_index(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/insight/login", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@insight_app.post("/upload")
async def upload_excel(request: Request, file: UploadFile = File(...)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/insight/login", status_code=303)

    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        df_raw = pd.read_excel(file_path, header=None, engine="openpyxl")

        preview_df = df_raw.head(10).copy()
        preview_df.index = list(preview_df.index + 1)
        preview_html = preview_df.to_html(classes="raw-preview", index=True, header=False)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user": user,
                "message": f"File '{file.filename}' uploaded successfully!",
                "raw_preview": preview_html,
                "uploaded_filename": file.filename
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "user": user, "error": f"Upload failed: {str(e)}"}
        )

@insight_app.post("/parse_with_header")
async def parse_with_header(
    request: Request,
    filename: str = Form(...),
    header_row: int = Form(...)
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/insight/login", status_code=303)

    try:
        file_path = os.path.join(UPLOAD_DIR, filename)
        df_raw = pd.read_excel(file_path, header=None, engine="openpyxl")

        if header_row > len(df_raw):
            raise ValueError(f"Header row {header_row} is beyond file length.")

        header_values = df_raw.iloc[header_row - 1].tolist()
        df = df_raw.iloc[header_row:].copy()
        df.columns = header_values
        df = df.fillna("")

        base_name = os.path.splitext(filename)[0]
        user_slug = slugify(base_name)

        row_count = len(df)
        upload_id = insert_uploaded_file_metadata(
            filename=filename,
            table_name="",
            uploaded_by=user,
            header_row=header_row,
            row_count=row_count,
        )

        table_name = f"data_{upload_id}_{user_slug}"[:64]
        insert_dynamic_table(df, table_name)

        with engine.begin() as conn:
            conn.execute(
                text("UPDATE uploaded_files SET table_name = :tn WHERE id = :id"),
                {"tn": table_name, "id": upload_id}
            )

        cleaned_html = df.head(20).to_html(classes="excel-preview", index=False)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user": user,
                "message": f"Parsed '{filename}' using row {header_row} as header.",
                "preview_table": cleaned_html
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user": user,
                "error": f"Header parsing failed: {str(e)}"
            }
        )

main_app = FastAPI()
main_app.mount("/insight", insight_app)

@main_app.get("/")
async def redirect_root():
    return RedirectResponse(url="/insight/", status_code=303)
