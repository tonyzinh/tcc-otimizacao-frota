"""Média interpretável por zona, hora e tipo de dia."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
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


def forecast_hour(requests: Iterable[Request], zones: Iterable[str], target_date: date, hour: int, cutoff: datetime) -> Forecast:
    aware(cutoff)
    if not 0 <= hour <= 23 or target_date <= cutoff.date():
        raise ValueError("previsão D+1 requer data posterior ao corte e hora válida")
    training = [r for r in requests if r.created_at < cutoff]
    days = sorted({r.created_at.date() for r in training})
    same_weekday = [day for day in days if day.weekday() == target_date.weekday()]
    fallback = not bool(same_weekday)
    selected = same_weekday or days
    counts = Counter((r.created_at.date(), r.origin.zone) for r in training if r.created_at.hour == hour)
    expected = {zone: sum(counts[(day, zone)] for day in selected) / len(selected) if selected else 0.0 for zone in sorted(set(zones))}
    return Forecast(target_date, hour, expected, len(selected), cutoff, fallback)


def forecast_error(forecast: Forecast, observed: Iterable[Request]) -> dict[str, float]:
    counts = Counter(r.origin.zone for r in observed if r.created_at.date() == forecast.target_date and r.created_at.hour == forecast.hour)
    return {zone: abs(value - counts[zone]) for zone, value in forecast.expected_by_zone.items()}
