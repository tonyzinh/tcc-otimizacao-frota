"""Bronze/Silver/Gold local, restrito a sintéticos nesta versão."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from tcc_frota.ingestion.files import read_rows
from tcc_frota.ingestion.history import parse_coordinate, parse_time
from tcc_frota.quality.audit import audit_rows
from tcc_frota.synthetic.generator import SyntheticDataset, export_synthetic


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_local_medallion(dataset: SyntheticDataset, root: str | Path) -> dict[str, object]:
    """Produz artefatos idempotentes e apenas sintéticos para ensaio local."""
    root = Path(root)
    bronze_requests, bronze_vehicles = export_synthetic(dataset, root / "bronze")
    raw_requests = list(read_rows(bronze_requests, dataset_kind="synthetic"))
    raw_vehicles = list(read_rows(bronze_vehicles, dataset_kind="synthetic"))
    request_audit = audit_rows(raw_requests, ("request_id", "created_at", "origin_lat", "origin_lon", "destination_lat", "destination_lon"), key="request_id")
    vehicle_audit = audit_rows(raw_vehicles, ("vehicle_id", "available_from", "available_until"), key="vehicle_id")
    excluded = Counter()
    silver_requests: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in raw_requests:
        try:
            request_id = str(row["request_id"]).strip()
            if not request_id or request_id in seen:
                excluded["missing_or_duplicate_request_id"] += 1
                continue
            stamp = parse_time(row["created_at"])
            lat = parse_coordinate(row["origin_lat"], latitude=True)
            lon = parse_coordinate(row["origin_lon"], latitude=False)
            dest_lat = parse_coordinate(row["destination_lat"], latitude=True)
            dest_lon = parse_coordinate(row["destination_lon"], latitude=False)
            duration = float(row["trip_minutes"])
            if None in (stamp, lat, lon, dest_lat, dest_lon) or duration <= 0:
                raise ValueError("campo ausente ou inválido")
        except (KeyError, ValueError, TypeError):
            excluded["invalid_request"] += 1
            continue
        seen.add(request_id)
        silver_requests.append({
            "request_id": request_id, "created_at": stamp.isoformat(), "zone": row["origin_zone"],
            "origin_lat": lat, "origin_lon": lon, "destination_zone": row["destination_zone"],
            "destination_lat": dest_lat, "destination_lon": dest_lon,
            "trip_minutes": duration, "split": row["split"], "dataset_kind": "synthetic",
        })
    silver_path = root / "silver" / "requests.csv"
    _write_csv(silver_path, ("request_id", "created_at", "zone", "origin_lat", "origin_lon", "destination_zone", "destination_lat", "destination_lon", "trip_minutes", "split", "dataset_kind"), silver_requests)
    silver_vehicles: list[dict[str, object]] = []
    seen_vehicles: set[str] = set()
    for row in raw_vehicles:
        try:
            vehicle_id = str(row["vehicle_id"]).strip()
            start = parse_time(row["available_from"])
            end = parse_time(row["available_until"])
            lat = parse_coordinate(row["lat"], latitude=True)
            lon = parse_coordinate(row["lon"], latitude=False)
            if not vehicle_id or vehicle_id in seen_vehicles or None in (start, end, lat, lon) or end <= start:
                raise ValueError("veículo inválido")
        except (KeyError, ValueError, TypeError):
            excluded["invalid_or_duplicate_vehicle"] += 1
            continue
        seen_vehicles.add(vehicle_id)
        silver_vehicles.append({
            "vehicle_id": vehicle_id, "zone": row["zone"], "lat": lat, "lon": lon,
            "available_from": start.isoformat(), "available_until": end.isoformat(),
            "dataset_kind": "synthetic",
        })
    silver_vehicle_path = root / "silver" / "vehicles.csv"
    _write_csv(silver_vehicle_path, ("vehicle_id", "zone", "lat", "lon", "available_from", "available_until", "dataset_kind"), silver_vehicles)
    counts = Counter((row["split"], row["zone"], datetime.fromisoformat(str(row["created_at"])).hour) for row in silver_requests)
    gold_rows = [
        {"split": split, "zone": zone, "hour": hour, "request_count": count, "dataset_kind": "synthetic"}
        for (split, zone, hour), count in sorted(counts.items())
    ]
    gold_path = root / "gold" / "demand.csv"
    _write_csv(gold_path, ("split", "zone", "hour", "request_count", "dataset_kind"), gold_rows)
    availability_path = root / "gold" / "availability_planned.csv"
    _write_csv(availability_path, ("zone", "vehicle_count", "dataset_kind"), [
        {"zone": zone, "vehicle_count": count, "dataset_kind": "synthetic"}
        for zone, count in sorted(Counter(row["zone"] for row in silver_vehicles).items())
    ])
    manifest = {
        "dataset_kind": "synthetic",
        "seed": dataset.seed,
        "bronze_requests": len(raw_requests),
        "bronze_vehicles": len(raw_vehicles),
        "silver_requests": len(silver_requests),
        "silver_vehicles": len(silver_vehicles),
        "gold_cells": len(gold_rows),
        "request_audit": request_audit.as_dict(),
        "vehicle_audit": vehicle_audit.as_dict(),
        "excluded": dict(excluded),
        "sha256": {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (bronze_requests, bronze_vehicles, silver_path, silver_vehicle_path, gold_path, availability_path)
        },
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
