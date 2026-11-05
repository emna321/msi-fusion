"""Démo : envoie des rapports synthétiques multi-sources à la gateway et affiche les pistes fusionnées.

Usage : python scripts/demo.py [http://localhost:8000]
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
T0 = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)


def iso(seconds: int) -> str:
    return (T0 + timedelta(seconds=seconds)).isoformat()


def call(method: str, path: str, body=None):
    req = urllib.request.Request(
        BASE + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"content-type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


SCENARIO = [
    # Cible A vue par trois sources différentes -> une seule piste attendue
    ("radar", {"lat": 48.800, "lon": 2.200, "t": int(T0.timestamp()), "snr": 24, "label": "vessel-A"}),
    ("imint", {"geo": [48.805, 2.204], "acquired": iso(90), "label": "vessel-A", "detection_score": 0.8}),
    ("osint", {"location": {"lat": 48.810, "lon": 2.210}, "published": iso(240), "label": "vessel-A", "credibility": 0.6}),
    # Cible B, loin de A -> seconde piste
    ("radar", {"lat": 49.500, "lon": 3.100, "t": int(T0.timestamp()) + 30, "snr": 18, "label": "vessel-B"}),
    # Rapport OSINT isolé et ancien pour A -> hors fenêtre temporelle, nouvelle piste
    ("osint", {"location": {"lat": 48.800, "lon": 2.200}, "published": iso(5000), "label": "vessel-A", "credibility": 0.4}),
]

if __name__ == "__main__":
    for source, payload in SCENARIO:
        track = call("POST", "/reports", {"source": source, "payload": payload})
        print(f"{source:6s} -> track {track['id']} ({track['label']}) n={track['n_reports']} conf={track['confidence']}")
    print("\nPistes fusionnées :")
    for t in call("GET", "/tracks"):
        print(json.dumps(t))
