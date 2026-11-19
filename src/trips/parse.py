"""Turn CSV rows into validated trip events. Pure functions, no I/O beyond reading the file."""

from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

COLUMNS = ("region", "origin_coord", "destination_coord", "date_time", "datasource")
_POINT = re.compile(r"^\s*POINT\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)\s*$")


@dataclass(frozen=True)
class Rejected:
    source_file: str
    source_line: int
    reason: str


def parse_point(text: str) -> tuple[float, float]:
    """`POINT (lon lat)` as (lon, lat). Raises ValueError on anything else."""
    match = _POINT.match(text or "")
    if not match:
        raise ValueError(f"not a WKT point: {text!r}")
    lon, lat = float(match[1]), float(match[2])
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError(f"coordinates out of range: {text!r}")
    return lon, lat


def trip_id(region: str, origin: tuple, destination: tuple, at: datetime, datasource: str) -> str:
    """Content hash of the trip. The same trip sent twice gets the same id."""
    key = f"{region}|{origin[0]!r},{origin[1]!r}|{destination[0]!r},{destination[1]!r}|{at.isoformat()}|{datasource}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def to_event(row: dict, source_file: str, source_line: int) -> dict:
    """Validate one CSV row and return the event sent to Kafka. Raises ValueError if invalid."""
    missing = [c for c in COLUMNS if not (row.get(c) or "").strip()]
    if missing:
        raise ValueError(f"missing: {', '.join(missing)}")
    region, datasource = row["region"].strip(), row["datasource"].strip()
    origin = parse_point(row["origin_coord"])
    destination = parse_point(row["destination_coord"])
    try:
        at = datetime.strptime(row["date_time"].strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise ValueError(f"bad date_time: {row['date_time']!r}") from exc
    return {
        "trip_id": trip_id(region, origin, destination, at, datasource),
        "region": region,
        "origin_lon": origin[0],
        "origin_lat": origin[1],
        "destination_lon": destination[0],
        "destination_lat": destination[1],
        "date_time": at.strftime("%Y-%m-%d %H:%M:%S"),
        "datasource": datasource,
        "source_file": source_file,
        "source_line": source_line,
    }


def read_events(path: str) -> Iterator[dict | Rejected]:
    """Yield an event or a Rejected for every data line. Line numbers match the file (header is 1)."""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError(f"{path}: expected header {','.join(COLUMNS)}, got {reader.fieldnames}")
        for row in reader:
            line = reader.line_num
            try:
                yield to_event(row, path, line)
            except ValueError as exc:
                yield Rejected(path, line, str(exc))
