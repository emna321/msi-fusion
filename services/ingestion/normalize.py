"""Normalisation de sources hétérogènes vers un schéma commun de rapport."""
from datetime import datetime, timezone

# Fiabilité a priori par type de source (0..1)
RELIABILITY = {"radar": 0.9, "imint": 0.8, "osint": 0.5}


def _parse_ts(value) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def normalize(source: str, payload: dict) -> dict:
    """Retourne un rapport au schéma commun : source, reliability, lat, lon, timestamp, confidence, label."""
    if source == "radar":
        # {"lat","lon","t"(epoch),"snr"(dB),"label"}
        return {
            "source": source,
            "reliability": RELIABILITY[source],
            "lat": payload["lat"],
            "lon": payload["lon"],
            "timestamp": _parse_ts(payload["t"]).isoformat(),
            "confidence": min(1.0, max(0.0, payload.get("snr", 10) / 30)),
            "label": payload["label"],
        }
    if source == "osint":
        # {"location":{"lat","lon"},"published"(ISO),"label","credibility"(0..1)}
        loc = payload["location"]
        return {
            "source": source,
            "reliability": RELIABILITY[source],
            "lat": loc["lat"],
            "lon": loc["lon"],
            "timestamp": _parse_ts(payload["published"]).isoformat(),
            "confidence": payload.get("credibility", 0.5),
            "label": payload["label"],
        }
    if source == "imint":
        # {"geo":[lat,lon],"acquired"(ISO),"label","detection_score"(0..1)}
        lat, lon = payload["geo"]
        return {
            "source": source,
            "reliability": RELIABILITY[source],
            "lat": lat,
            "lon": lon,
            "timestamp": _parse_ts(payload["acquired"]).isoformat(),
            "confidence": payload.get("detection_score", 0.7),
            "label": payload["label"],
        }
    raise ValueError(f"source inconnue: {source}")
