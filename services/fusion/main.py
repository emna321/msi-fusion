from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

from fusion import FusionEngine, Report

app = FastAPI(title="fusion-service")
engine = FusionEngine()


class ReportIn(BaseModel):
    source: str
    reliability: float
    lat: float
    lon: float
    timestamp: datetime
    confidence: float
    label: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reports")
def add_report(r: ReportIn):
    track = engine.ingest(Report(**r.model_dump()))
    return track.to_dict()


@app.get("/tracks")
def tracks():
    return [t.to_dict() for t in engine.tracks]


@app.delete("/tracks")
def reset():
    engine.tracks.clear()
    return {"status": "cleared"}
