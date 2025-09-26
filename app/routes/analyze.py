import httpx
from fastapi import APIRouter, Request, HTTPException
from starlette.config import Config

router = APIRouter()

# Load from .env
config = Config(".env")
LLAMALITH_API_URL = config("LLAMALITH_API_URL", default="http://192.168.10.23:8000")
LLAMALITH_API_TOKEN = config("LLAMALITH_API_TOKEN", default="")

# One-shot LLM question about a table
@router.post("/analyze/{table_name}/ask")
async def ask_table_question(request: Request, table_name: str):
    require_login(request)
    data = await request.json()
    question = data.get("question", "").strip()
    preview = data.get("preview", "").strip()

    if not question or not preview:
        return JSONResponse({"error": "Missing question or preview"}, status_code=400)

    system_prompt = (
        "You are a helpful data analyst. Use the table preview and the user’s question "
        "to provide a clear, concise, and relevant answer. Only base your answer on the data shown.\n\n"
        f"TABLE PREVIEW:\n{preview}"
    )

    payload = {
        "model": "mistral",
        "content": question,
        "system_prompt": system_prompt
    }

    headers = {"Authorization": f"Bearer {LLAMALITH_API_TOKEN}"}

    async with httpx.AsyncClient() as client:
        job_resp = await client.post(f"{LLAMALITH_API_URL}/api/jobs", json=payload, headers=headers)

    if job_resp.status_code != 200:
        return JSONResponse({"error": f"Failed to queue LLM job: HTTP {job_resp.status_code}"}, status_code=500)

    try:
        job_data = job_resp.json()
    except Exception:
        return JSONResponse({"error": "Failed to parse LLM response"}, status_code=500)

    job_id = job_data.get("job_id")
        if not job_id:
            return JSONResponse({"error": f"LLM returned no job_id. Response: {job_data}"}, status_code=500)

    return {"ok": True, "job_id": job_id}

@router.get("/analyze/status/{job_id}")
async def check_llamalith_status(job_id: str):
    headers = {"Authorization": f"Bearer {LLAMALITH_API_TOKEN}"}

    async with httpx.AsyncClient() as client:
        try:
            status_resp = await client.get(f"{LLAMALITH_API_URL}/api/jobs/{job_id}", headers=headers)
        except httpx.RequestError as e:
            return JSONResponse({"error": f"Llamalith connection error: {str(e)}"}, status_code=502)

    if status_resp.status_code != 200:
        return JSONResponse({"error": "Failed to get job status"}, status_code=500)

    result = status_resp.json()

    if result.get("status") == "done":
        return {"done": True, "output": result.get("output", "").strip()}

    return {"done": False}
