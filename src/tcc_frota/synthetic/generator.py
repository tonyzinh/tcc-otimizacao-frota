"""Geração sintética sem IDs, placas ou trajetórias da empresa."""
from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from tcc_frota.models import Position, Request, Vehicle


@dataclass(frozen=True)
class SyntheticDataset:
    zones: dict[str, Position]
    historical: list[Request]
    evaluation: list[Request]
    vehicles: list[Vehicle]
    target_date: date
    seed: int


def make_synthetic(
    seed: int = 20261014,
    fleet_size: int = 5,
    target_date: date = date(2026, 10, 15),
    *,
    leste_train_count: int = 3,
    leste_eval_count: int = 3,
    initial_distribution: str = "center",
) -> SyntheticDataset:
    if fleet_size < 0 or not 0 <= leste_train_count <= 4 or not 0 <= leste_eval_count <= 4:
        raise ValueError("frota ou demanda inválida")
    if initial_distribution not in {"center", "spread"}:
        raise ValueError("distribuição inicial inválida")
    rng = random.Random(seed)
    zones = {
        "centro": Position("centro", -20.315, -40.300),
        "leste": Position("leste", -20.335, -40.275),
        "norte": Position("norte", -20.275, -40.295),
    }
    history: list[Request] = []
    for days_before in range(28, 0, -1):
        day = target_date - timedelta(days=days_before)
        for hour in (8, 9):
            for zone_id, n in (("leste", leste_train_count), ("centro", 1), ("norte", 1)):
                for index in range(n):
                    minute = 5 + index * 11 + rng.randrange(3)
                    origin = zones[zone_id]
                    destination = zones[zone_id if index % 2 == 0 else "centro"]
                    stamp = datetime.combine(day, time(hour, minute), tzinfo=timezone.utc)
                    history.append(Request(f"train-{days_before}-{hour}-{zone_id}-{index}", stamp, origin, destination, 10 + rng.randrange(5)))
    evaluation: list[Request] = []
    for hour in (8, 9):
        for zone_id, n in (("leste", leste_eval_count), ("centro", 1), ("norte", 1)):
            for index in range(n):
                minute = 5 + index * 11 + rng.randrange(3)
                origin = zones[zone_id]
                destination = zones[zone_id if index % 2 == 0 else "centro"]
                stamp = datetime.combine(target_date, time(hour, minute), tzinfo=timezone.utc)
                evaluation.append(Request(f"test-{hour}-{zone_id}-{index}", stamp, origin, destination, 10 + rng.randrange(5)))
    start = datetime.combine(target_date, time(7), tzinfo=timezone.utc)
    end = datetime.combine(target_date + timedelta(days=1), time(0), tzinfo=timezone.utc)
    positions = ("centro",) if initial_distribution == "center" else ("centro", "leste", "norte")
    vehicles = [Vehicle(f"synthetic-{i:03d}", zones[positions[i % len(positions)]], start, end) for i in range(fleet_size)]
    return SyntheticDataset(zones, history, evaluation, vehicles, target_date, seed)


def export_synthetic(dataset: SyntheticDataset, directory: str | Path) -> tuple[Path, Path]:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    request_file = root / "requests.csv"
    vehicle_file = root / "vehicles.csv"
    with request_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("request_id", "created_at", "origin_zone", "origin_lat", "origin_lon", "destination_zone", "destination_lat", "destination_lon", "trip_minutes", "split", "dataset_kind"))
        for split, requests in (("train", dataset.historical), ("test", dataset.evaluation)):
            for request in requests:
                writer.writerow((request.request_id, request.created_at.isoformat(), request.origin.zone, request.origin.lat, request.origin.lon, request.destination.zone, request.destination.lat, request.destination.lon, request.trip_minutes, split, "synthetic"))
    with vehicle_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("vehicle_id", "zone", "lat", "lon", "available_from", "available_until", "dataset_kind"))
        for vehicle in dataset.vehicles:
            assert vehicle.position is not None
            writer.writerow((vehicle.vehicle_id, vehicle.position.zone, vehicle.position.lat, vehicle.position.lon, vehicle.available_from.isoformat(), vehicle.available_until.isoformat(), "synthetic"))
    return request_file, vehicle_file
