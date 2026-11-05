import os

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

INGESTION_URL = os.getenv("INGESTION_URL", "http://ingestion:8001")
FUSION_URL = os.getenv("FUSION_URL", "http://fusion:8002")

app = FastAPI(title="api-gateway")


class RawReport(BaseModel):
    source: str
    payload: dict


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reports")
async def submit(raw: RawReport):
    """Pipeline : gateway -> ingestion (normalisation) -> fusion (corrélation)."""
    async with httpx.AsyncClient(timeout=5) as client:
        n = await client.post(f"{INGESTION_URL}/normalize", json=raw.model_dump())
        if n.status_code != 200:
            raise HTTPException(n.status_code, n.json().get("detail"))
        f = await client.post(f"{FUSION_URL}/reports", json=n.json())
        return f.json()


@app.get("/tracks")
async def tracks():
    async with httpx.AsyncClient(timeout=5) as client:
        return (await client.get(f"{FUSION_URL}/tracks")).json()
