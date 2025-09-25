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

# -----------------------------------------------------------------------------
# InsightHub Sub-App (mounted at /insight)
# -----------------------------------------------------------------------------
middleware = [
    Middleware(SessionMiddleware, secret_key=SESSION_SECRET),
    Middleware(AuthMiddleware),
]

insight_app = FastAPI(middleware=middleware)

insight_app.include_router(auth_router)
insight_app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
templates.env.globals["root_path"] = "/insight/"

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# GETS
# -----------------------------------------------------------------------------

# INDEX PAGE — secured
@insight_app.get("/")
async def insight_index(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/insight/login", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

# -----------------------------------------------------------------------------
# POSTS
# -----------------------------------------------------------------------------

@insight_app.post("/parse_with_header")
async def parse_with_header(
    request: Request,
    filename: str = Form(...),
    header_row: int = Form(...)
):
    import pandas as pd

    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/insight/login", status_code=303)

    try:
        file_path = os.path.join(UPLOAD_DIR, filename)

        # Read all rows without header
        df_raw = pd.read_excel(file_path, header=None, engine="openpyxl")

        # Check row exists
        if header_row > len(df_raw):
            raise ValueError(f"Header row {header_row} is beyond file length.")

        # Manually set header row
        header_values = df_raw.iloc[header_row - 1].tolist()

        # Remove all rows before header
        df = df_raw.iloc[header_row:].copy()
        df.columns = header_values

        # Replace NaNs with empty string
        df = df.fillna("")

        # Generate safe base name
        base_name = os.path.splitext(filename)[0]
        user_slug = slugify(base_name)

        # Insert metadata first (we’ll use returned ID to name the data table)
        row_count = len(df)
        upload_id = insert_uploaded_file_metadata(
            filename=filename,
            table_name="",  # placeholder for now
            uploaded_by=user,
            header_row=header_row,
            row_count=row_count,
        )

        # Generate actual table name
        table_name = f"data_{upload_id}_{user_slug}"
        table_name = table_name[:64]  # Limit to safe length

        # Now insert the DataFrame into the new table
        insert_dynamic_table(df, table_name)

        # Update uploaded_files with the correct table name
        with engine.begin() as conn:
            conn.execute(text("UPDATE uploaded_files SET table_name = :tn WHERE id = :id"), {"tn": table_name, "id": upload_id})
        
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

# FILE UPLOAD HANDLER
@insight_app.post("/upload")
async def upload_excel(request: Request, file: UploadFile = File(...)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/insight/login", status_code=303)

    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Load WITHOUT headers (so we show all raw rows)
        df_raw = pd.read_excel(file_path, header=None, engine="openpyxl")

        # Fix index so it displays as Excel-style (1-based)
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

# -----------------------------------------------------------------------------
# Root App (exposed via uvicorn and NGINX)
# -----------------------------------------------------------------------------
main_app = FastAPI()

# Mount InsightHub at /insight
main_app.mount("/insight", insight_app)

# Redirect root (/) to /insight/
@main_app.get("/")
async def redirect_root():
    return RedirectResponse(url="/insight/", status_code=303)
