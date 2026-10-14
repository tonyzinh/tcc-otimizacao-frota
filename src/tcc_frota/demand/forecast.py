"""Média interpretável por zona, hora e tipo de dia."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

from tcc_frota.models import Request, aware


@dataclass(frozen=True)
class Forecast:
    target_date: date
    hour: int
    expected_by_zone: dict[str, float]
    training_days: int
    cutoff: datetime
    fallback_all_days: bool


def _comparable_days(days: Iterable[date], target_date: date) -> tuple[list[date], bool]:
    ordered = sorted(set(days))
    same_weekday = [day for day in ordered if day.weekday() == target_date.weekday()]
    return same_weekday or ordered, not bool(same_weekday)


def forecast_hour(requests: Iterable[Request], zones: Iterable[str], target_date: date, hour: int, cutoff: datetime) -> Forecast:
    aware(cutoff)
    if not 0 <= hour <= 23 or target_date <= cutoff.date():
        raise ValueError("previsão D+1 requer data posterior ao corte e hora válida")
    training = [r for r in requests if r.created_at < cutoff]
    selected, fallback = _comparable_days((r.created_at.date() for r in training), target_date)
    counts = Counter((r.created_at.date(), r.origin.zone) for r in training if r.created_at.hour == hour)
    expected = {zone: sum(counts[(day, zone)] for day in selected) / len(selected) if selected else 0.0 for zone in sorted(set(zones))}
    return Forecast(target_date, hour, expected, len(selected), cutoff, fallback)


def forecast_error(forecast: Forecast, observed: Iterable[Request]) -> dict[str, float]:
    counts = Counter(r.origin.zone for r in observed if r.created_at.date() == forecast.target_date and r.created_at.hour == forecast.hour)
    return {zone: abs(value - counts[zone]) for zone, value in forecast.expected_by_zone.items()}


def forecast_temporal_counts(
    counts: Iterable[tuple[date, int, int]], complete_months: Iterable[str],
    target_date: date, cutoff: datetime, *, slot_hours: int = 1,
) -> dict[str, object]:
    """Use the existing same-weekday mean on complete historical calendar days.

    The cutoff day is excluded because its late hours may still be unknown.
    Status snapshots and target-day counts never enter training.
    """
    aware(cutoff)
    if target_date <= cutoff.date() or slot_hours not in {1, 2, 3, 4, 6, 12, 24}:
        raise ValueError("alvo/corte ou granularidade inválida")
    available = set(complete_months)
    days: list[date] = []
    for month in sorted(available):
        year, number = map(int, month.split("-"))
        day = date(year, number, 1)
        while day.month == number and day < cutoff.date():
            days.append(day)
            day += timedelta(days=1)
    selected, fallback = _comparable_days(days, target_date)
    if not selected:
        raise ValueError("nenhum dia histórico completo antes do corte")
    selected_set = set(selected)
    bucket: Counter[tuple[date, int]] = Counter()
    for day, hour, count in counts:
        if day in selected_set and 0 <= hour <= 23 and count >= 0:
            bucket[(day, hour // slot_hours * slot_hours)] += count
    expected = {str(hour): sum(bucket[(day, hour)] for day in selected) / len(selected)
                for hour in range(0, 24, slot_hours)}
    return {"target_date": target_date.isoformat(), "cutoff": cutoff.isoformat(),
            "slot_hours": slot_hours, "training_days": len(selected),
            "fallback_all_days": fallback, "expected_by_hour": expected,
            "spatial_status": "origin_unavailable"}
