from fastapi import FastAPI, Request, UploadFile, File, Form, Query, HTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware import Middleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
import os, shutil
import httpx
import pandas as pd
from app.db import slugify, insert_uploaded_file_metadata, insert_dynamic_table, engine
from app.utils.llm_client import submit_llm_prompt, get_llm_response
from sqlalchemy import text, inspect
from app.middleware import AuthMiddleware
from app.auth import router as auth_router
from app.utils.security import SESSION_SECRET
from datetime import datetime

middleware = [
    Middleware(SessionMiddleware, secret_key=SESSION_SECRET, session_cookie="insight_session"),
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

LLAMALITH_URL = "http://192.168.10.23:8000"
LLAMALITH_API_TOKEN = os.getenv("LLAMALITH_API_TOKEN")

#---------------------------------------------------------------------------------------------
# DELETES
#---------------------------------------------------------------------------------------------

@insight_app.delete("/delete_table/{table_name}")
async def delete_table(table_name: str):
    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
        conn.execute(text("DELETE FROM uploaded_files WHERE table_name = :tn"), {"tn": table_name})
    return {"success": True}
    
#---------------------------------------------------------------------------------------------
# GETS
#---------------------------------------------------------------------------------------------

@insight_app.get("/")
async def insight_index(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/insight/login", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

# Route to ask questions about a table
@insight_app.get("/analyze/{table_name}", response_class=HTMLResponse)
async def analyze_table(
    request: Request,
    table_name: str,
    question: str = Query(None),
    job_id: str = Query(None)
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/insight/login", status_code=303)

    # Get column schema
    with engine.connect() as conn:
        inspector = inspect(engine)
        columns = inspector.get_columns(table_name)
        schema = [f"{col['name']} ({str(col['type'])})" for col in columns]

    # If user submitted a question
    if question:
        if not job_id:
            # Build prompt using multi-line style
            prompt_lines = [
                f"You are an expert data analyst. A user has uploaded a table named '{table_name}' with the following schema:",
                "",
                *schema,
                "",
                f'They asked the following question:\n"{question}"',
                "",
                "Write a single SQL query (PostgreSQL dialect) that answers the question.",
                "Do not include any commentary or explanation. Just return the SQL query only.",
            ]
            prompt = "\n".join(prompt_lines)

            # Submit job to Llamalith
            job_id = await submit_llm_prompt(prompt)
            return RedirectResponse(
                url=f"/insight/analyze/{table_name}?question={question}&job_id={job_id}",
                status_code=303
            )

        # Poll for response if job_id present
        try:
            llm_result = await get_llm_response(job_id)
            sql_query = llm_result.strip()

            return templates.TemplateResponse("analyze.html", {
                "request": request,
                "user": user,
                "table_name": table_name,
                "question": question,
                "sql_query": sql_query,
                "result_html": None,
                "job_id": job_id,
            })

        except Exception as e:
            return templates.TemplateResponse("analyze.html", {
                "request": request,
                "user": user,
                "table_name": table_name,
                "question": question,
                "sql_query": None,
                "result_html": f"<div style='color:red;'>LLM Error: {str(e)}</div>",
                "job_id": job_id,
            })

    # No question asked yet
    return templates.TemplateResponse("analyze.html", {
        "request": request,
        "user": user,
        "table_name": table_name,
        "question": None,
        "sql_query": None,
        "result_html": None,
        "job_id": None,
    })

@insight_app.get("/manage", response_class=HTMLResponse)
async def manage_tables(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/insight/login", status_code=303)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT table_name, uploaded_by, uploaded_at FROM uploaded_files ORDER BY uploaded_at ASC"))
        tables = result.mappings().all()
    return templates.TemplateResponse("manage.html", {"request": request, "user": user, "tables": tables})

@insight_app.get("/preview_table")
async def preview_table(name: str):
    try:
        with engine.begin() as conn:
            result = conn.execute(text(f"SELECT * FROM `{name}` LIMIT 20"))
            rows = result.mappings().all()
            if not rows:
                return "<em>No data in table</em>"
            df = pd.DataFrame(rows)
            return df.to_html(classes="excel-preview", index=False)
    except Exception as e:
        return f"<div style='color:red;'>Error previewing table: {str(e)}</div>"

@insight_app.get("/preview_table/{table_name}")
async def preview_table(table_name: str):
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 20"))
        rows = result.fetchall()
        columns = result.keys()
    table_html = "<table><thead><tr>" + "".join(f"<th>{col}</th>" for col in columns) + "</tr></thead><tbody>"
    for row in rows:
        table_html += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
    table_html += "</tbody></table>"
    return HTMLResponse(content=table_html)

#---------------------------------------------------------------------------------------------
# POSTS
#---------------------------------------------------------------------------------------------

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
        preview_html = preview_df.to_html(classes="raw-preview", index=True, header=False, border=0)

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

@insight_app.post("/run_query/{table_name}", response_class=HTMLResponse)
async def run_sql_query(
    request: Request,
    table_name: str,
    sql_query: str = Form(...)
):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/insight/login", status_code=303)

    result_html = ""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            result_html = df.to_html(classes="excel-preview", index=False)
    except Exception as e:
        result_html = f"<div style='color:red;'>Error executing query: {str(e)}</div>"

    return templates.TemplateResponse("analyze.html", {
        "request": request,
        "user": user,
        "table_name": table_name,
        "question": None,
        "sql_query": sql_query,
        "result_html": result_html
    })

async def send_llamalith_job(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {LLAMALITH_API_TOKEN}"}
    payload = {
        "content": prompt,
        "model": "mistral",
        "system_prompt": "",
        "assistant_context": "",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{LLAMALITH_URL}/api/jobs", json=payload, headers=headers)
        if resp.status_code == 200:
            return resp.json().get("job_id")
        return None

@insight_app.post("/analyze/{table_name}/ask")
async def ask_question(table_name: str, request: Request):
    body = await request.json()
    question = body.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="Question not provided")

    # Build schema string for the LLM
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    schema = [f"{col['name']} ({str(col['type'])})" for col in columns]

    prompt_lines = [
        f"You are an expert data analyst. A user has uploaded a table named '{table_name}' with the following schema:",
        "",
        *schema,
        "",
        f'They asked the following question:\n"{question}"',
        "",
        "Write a single SQL query (PostgreSQL dialect) that answers the question.",
        "Do not include any commentary or explanation. Just return the SQL query only.",
    ]
    prompt = "\n".join(prompt_lines)

    job_id = await send_llamalith_job(prompt)
    if not job_id:
        raise HTTPException(status_code=500, detail="Failed to submit job to LLM")

    return {"job_id": job_id}

main_app = FastAPI()
main_app.mount("/insight", insight_app)

@main_app.get("/")
async def redirect_root():
    return RedirectResponse(url="/insight/", status_code=303)
