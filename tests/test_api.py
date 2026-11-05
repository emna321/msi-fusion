"""Tests d'API des services (ingestion et fusion), chargés par chemin pour éviter le conflit de noms `main`."""
import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SERVICES = Path(__file__).resolve().parent.parent / "services"


def load_app(service: str):
    folder = SERVICES / service
    sys.path.insert(0, str(folder))
    try:
        spec = importlib.util.spec_from_file_location(f"{service}_main", folder / "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.app
    finally:
        sys.path.remove(str(folder))
        sys.modules.pop("fusion", None) if service != "fusion" else None


@pytest.fixture(scope="module")
def ingestion():
    return TestClient(load_app("ingestion"))


@pytest.fixture()
def fusion():
    client = TestClient(load_app("fusion"))
    client.delete("/tracks")
    return client


def test_ingestion_normalizes_radar(ingestion):
    r = ingestion.post(
        "/normalize",
        json={"source": "radar", "payload": {"lat": 1, "lon": 2, "t": 1_700_000_000, "snr": 30, "label": "X"}},
    )
    assert r.status_code == 200
    assert r.json()["confidence"] == 1.0
    assert r.json()["reliability"] == 0.9


def test_ingestion_rejects_unknown_source(ingestion):
    r = ingestion.post("/normalize", json={"source": "sigint", "payload": {}})
    assert r.status_code == 422


def test_ingestion_rejects_malformed_payload(ingestion):
    r = ingestion.post("/normalize", json={"source": "radar", "payload": {"lat": 1}})
    assert r.status_code == 422


def _report(source, rel, lat, lon, ts, conf, label="A"):
    return {"source": source, "reliability": rel, "lat": lat, "lon": lon,
            "timestamp": ts, "confidence": conf, "label": label}


def test_fusion_merges_and_lists_tracks(fusion):
    fusion.post("/reports", json=_report("radar", 0.9, 48.80, 2.20, "2026-11-05T12:00:00+00:00", 0.8))
    r = fusion.post("/reports", json=_report("osint", 0.5, 48.81, 2.21, "2026-11-05T12:02:00+00:00", 0.6))
    assert r.json()["n_reports"] == 2
    assert r.json()["sources"] == ["osint", "radar"]
    assert len(fusion.get("/tracks").json()) == 1


def test_fusion_reset(fusion):
    fusion.post("/reports", json=_report("radar", 0.9, 48.80, 2.20, "2026-11-05T12:00:00+00:00", 0.8))
    fusion.delete("/tracks")
    assert fusion.get("/tracks").json() == []
