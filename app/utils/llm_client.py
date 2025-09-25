import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()
LLAMALITH_URL = "http://192.168.10.23:8000"
LLAMALITH_TOKEN = os.getenv("LLAMALITH_API_TOKEN")

HEADERS = {"Authorization": f"Bearer {LLAMALITH_TOKEN}"}

async def submit_llm_prompt(prompt: str, model: str = "mistral-7b-instruct"):
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{LLAMALITH_URL}/api/jobs", headers=HEADERS, json={
            "content": prompt,
            "model": model,
            "system_prompt": "You are an expert data analyst. Given a schema and a user question, write a SQL query using PostgreSQL dialect with no commentary.",
        })
        res.raise_for_status()
        return res.json()["job_id"]

async def get_llm_response(job_id: str):
    async with httpx.AsyncClient() as client:
        for _ in range(60):  # Wait up to 60 tries (e.g., 60s or more)
            res = await client.get(f"{LLAMALITH_URL}/api/jobs/{job_id}", headers=HEADERS)
            res.raise_for_status()
            data = res.json()
            if data["status"] == "done":
                return data["result"]
            elif data["status"] == "error":
                raise Exception(f"LLM failed: {data.get('error', 'Unknown error')}")
            await asyncio.sleep(2)  # Wait between polls
    raise TimeoutError("Timed out waiting for LLM")
