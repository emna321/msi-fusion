import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "services"
sys.path.insert(0, str(ROOT / "fusion"))
sys.path.insert(0, str(ROOT / "ingestion"))

import pytest  # noqa: E402

from fusion import FusionEngine, Report, haversine_km  # noqa: E402
from normalize import normalize  # noqa: E402

T0 = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)


def rep(source, rel, lat, lon, dt_s, conf, label="vessel-A"):
    return Report(source, rel, lat, lon, T0 + timedelta(seconds=dt_s), conf, label)


def test_haversine_paris_london():
    assert haversine_km(48.8566, 2.3522, 51.5074, -0.1278) == pytest.approx(344, abs=5)


def test_close_reports_fuse_into_one_track():
    e = FusionEngine(gate_km=5, gate_s=600)
    e.ingest(rep("radar", 0.9, 48.80, 2.20, 0, 0.8))
    t = e.ingest(rep("osint", 0.5, 48.81, 2.21, 120, 0.6))
    assert len(e.tracks) == 1
    assert t.sources == ["osint", "radar"]


def test_far_or_old_reports_create_new_track():
    e = FusionEngine(gate_km=5, gate_s=600)
    e.ingest(rep("radar", 0.9, 48.80, 2.20, 0, 0.8))
    e.ingest(rep("radar", 0.9, 49.50, 2.20, 60, 0.8))  # trop loin
    e.ingest(rep("radar", 0.9, 48.80, 2.20, 5000, 0.8))  # trop tard
    assert len(e.tracks) == 3


def test_different_labels_do_not_fuse():
    e = FusionEngine()
    e.ingest(rep("radar", 0.9, 48.8, 2.2, 0, 0.8, "A"))
    e.ingest(rep("radar", 0.9, 48.8, 2.2, 10, 0.8, "B"))
    assert len(e.tracks) == 2


def test_confidence_increases_with_independent_sources():
    e = FusionEngine()
    t = e.ingest(rep("radar", 0.9, 48.8, 2.2, 0, 0.8))
    c1 = t.confidence
    t = e.ingest(rep("imint", 0.8, 48.8, 2.2, 30, 0.7))
    assert t.confidence > c1
    assert t.confidence <= 1.0


def test_position_weighted_toward_reliable_source():
    e = FusionEngine()
    e.ingest(rep("radar", 0.9, 48.80, 2.20, 0, 0.9))
    t = e.ingest(rep("osint", 0.3, 48.82, 2.22, 30, 0.3))
    assert abs(t.lat - 48.80) < abs(t.lat - 48.82)


def test_normalize_three_sources():
    r = normalize("radar", {"lat": 1, "lon": 2, "t": 1_700_000_000, "snr": 15, "label": "X"})
    o = normalize("osint", {"location": {"lat": 1, "lon": 2}, "published": "2026-11-05T12:00:00Z", "label": "X"})
    i = normalize("imint", {"geo": [1, 2], "acquired": "2026-11-05T12:00:00Z", "label": "X"})
    for rep_ in (r, o, i):
        assert {"source", "reliability", "lat", "lon", "timestamp", "confidence", "label"} <= rep_.keys()
    assert r["confidence"] == pytest.approx(0.5)


def test_normalize_unknown_source():
    with pytest.raises(ValueError):
        normalize("sigint", {})
