"""Location helpers: demo pincode lookup and coordinate validation.

Pincodes resolve only through data/pincodes_demo.json. There is deliberately no
external geocoder: an unknown pincode is an error, never a guess.
"""
import json
import math
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PINCODES: dict[str, dict] = json.loads((_DATA_DIR / "pincodes_demo.json").read_text())["pincodes"]


class LocationError(ValueError):
    """Base class for errors that should be shown to the user as-is."""


class UnknownPincodeError(LocationError):
    pass


class InvalidCoordinatesError(LocationError):
    pass


def available_pincodes() -> list[str]:
    return [f"{code} ({row['city']})" for code, row in _PINCODES.items()]


def resolve_pincode(pincode) -> dict:
    """Returns {"lat", "lng", "address", "pincode"} for a demo pincode, else raises."""
    code = str(pincode).strip() if pincode is not None else ""
    row = _PINCODES.get(code)
    if row is None:
        shown = f"'{code}'" if code else "none was given"
        raise UnknownPincodeError(
            f"Pincode not in demo data: {shown}. Available demo pincodes: {', '.join(available_pincodes())}."
        )
    return {"lat": row["lat"], "lng": row["lng"], "address": f"{row['city']}, {row['state']}", "pincode": code}


def validate_point(point, what: str = "location") -> tuple[float, float]:
    """Returns (lat, lng) as floats or raises InvalidCoordinatesError."""
    lat = point.get("lat") if isinstance(point, dict) else None
    lng = point.get("lng") if isinstance(point, dict) else None
    for name, value, limit in (("lat", lat, 90.0), ("lng", lng, 180.0)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise InvalidCoordinatesError(f"Missing or invalid {name} for {what}: {value!r}. Cannot compute a distance.")
        if abs(value) > limit:
            raise InvalidCoordinatesError(f"Invalid {name} for {what}: {value!r} is outside +/-{limit:g}. Cannot compute a distance.")
    return float(lat), float(lng)
