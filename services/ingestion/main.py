from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from normalize import normalize

app = FastAPI(title="ingestion-service")


class RawReport(BaseModel):
    source: str
    payload: dict


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/normalize")
def normalize_report(raw: RawReport):
    try:
        return normalize(raw.source, raw.payload)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
