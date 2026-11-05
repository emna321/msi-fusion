"""Moteur de fusion : corrélation spatio-temporelle de rapports multi-sources en pistes (tracks)."""
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime

EARTH_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_KM * math.asin(math.sqrt(a))


@dataclass
class Report:
    source: str
    reliability: float  # 0..1, fiabilité de la source
    lat: float
    lon: float
    timestamp: datetime
    confidence: float  # 0..1, confiance du rapport
    label: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    @property
    def weight(self) -> float:
        return self.reliability * self.confidence


@dataclass
class Track:
    label: str
    reports: list = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    @property
    def last(self) -> Report:
        return max(self.reports, key=lambda r: r.timestamp)

    @property
    def lat(self) -> float:
        w = sum(r.weight for r in self.reports)
        return sum(r.lat * r.weight for r in self.reports) / w

    @property
    def lon(self) -> float:
        w = sum(r.weight for r in self.reports)
        return sum(r.lon * r.weight for r in self.reports) / w

    @property
    def confidence(self) -> float:
        # combinaison "noisy-OR" de supports indépendants (cas simple de Dempster-Shafer)
        p = 1.0
        for r in self.reports:
            p *= 1.0 - r.weight
        return 1.0 - p

    @property
    def sources(self) -> list:
        return sorted({r.source for r in self.reports})

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "lat": round(self.lat, 5),
            "lon": round(self.lon, 5),
            "confidence": round(self.confidence, 3),
            "sources": self.sources,
            "n_reports": len(self.reports),
            "last_seen": self.last.timestamp.isoformat(),
        }


class FusionEngine:
    def __init__(self, gate_km: float = 5.0, gate_s: float = 600.0):
        self.gate_km = gate_km
        self.gate_s = gate_s
        self.tracks: list[Track] = []

    def ingest(self, report: Report) -> Track:
        best, best_d = None, None
        for t in self.tracks:
            if t.label != report.label:
                continue
            last = t.last
            dt = abs((report.timestamp - last.timestamp).total_seconds())
            d = haversine_km(report.lat, report.lon, last.lat, last.lon)
            if dt <= self.gate_s and d <= self.gate_km and (best_d is None or d < best_d):
                best, best_d = t, d
        if best is None:
            best = Track(label=report.label)
            self.tracks.append(best)
        best.reports.append(report)
        return best
