"""Previsão D+1 da demanda imediata por zona H3 r7 e hora (Fase 2).

Corte às 20h de D; o treino usa somente datas locais completas anteriores a D (convenção de DT011),
dentro da janela `lookback_days`, sem as datas excluídas (Carnaval por padrão). O alvo é D+1.
Três modelos: média do mesmo dia da semana (baseline do repositório), naïve sazonal (D+1−7) e
regressão de Poisson com efeitos de zona, hora e dia da semana mais defasagens.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from math import log

CARNAVAL_2026 = tuple(date(2026, 2, d) for d in range(14, 19))
MODELS = ("media_dia_semana", "naive_sazonal", "poisson")


@dataclass(frozen=True)
class ForecastConfig:
    lookback_days: int = 56
    excluded_dates: tuple[date, ...] = CARNAVAL_2026
    min_zone_training_count: int = 20
    ridge: float = 1e-2


@dataclass
class DemandHistory:
    """Contagens observadas por (data, hora, zona r7) e datas com dados."""

    counts: dict[tuple[date, int, str], int] = field(default_factory=dict)
    dates: set[date] = field(default_factory=set)

    @classmethod
    def from_gold(cls, demanda_zona_hora: list[dict]) -> DemandHistory:
        counts: dict[tuple[date, int, str], int] = defaultdict(int)
        dates: set[date] = set()
        for row in demanda_zona_hora:
            counts[(row["data_local"], row["hora_local"], row["h3_r7"])] += row["qtd_demanda"]
            dates.add(row["data_local"])
        return cls(dict(counts), dates)

    def value(self, day: date, hour: int, zone: str) -> int:
        return self.counts.get((day, hour, zone), 0)

    def restricted(self, before: date) -> DemandHistory:
        """Cópia só com datas anteriores a `before` (para testes de não vazamento)."""
        return DemandHistory({k: v for k, v in self.counts.items() if k[0] < before}, {d for d in self.dates if d < before})


def cutoff_date(target: date) -> date:
    return target - timedelta(days=1)


def training_dates(target: date, history: DemandHistory, config: ForecastConfig) -> list[date]:
    """Datas completas anteriores ao dia do corte (D = alvo − 1), na janela e sem exclusões."""
    cut = cutoff_date(target)
    first = cut - timedelta(days=config.lookback_days)
    return sorted(d for d in history.dates if first <= d < cut and d not in config.excluded_dates)


def zones_in(history: DemandHistory, dates: list[date]) -> list[str]:
    wanted = set(dates)
    return sorted({z for (d, _, z) in history.counts if d in wanted and z})


def predict(
    model: str, target: date, history: DemandHistory, hours: range, config: ForecastConfig = ForecastConfig()
) -> dict[tuple[int, str], float]:
    """λ[(hora, zona)] para D+1. Usa apenas datas anteriores ao dia do corte."""
    train = training_dates(target, history, config)
    safe = history.restricted(cutoff_date(target))
    zones = zones_in(safe, train)
    if model == "media_dia_semana":
        same = [d for d in train if d.weekday() == target.weekday()]
        if not same:
            return {}
        return {(h, z): sum(safe.value(d, h, z) for d in same) / len(same) for h in hours for z in zones}
    if model == "naive_sazonal":
        ref = target - timedelta(days=7)
        if ref not in safe.dates or ref in config.excluded_dates:
            return {}
        return {(h, z): float(safe.value(ref, h, z)) for h in hours for z in zones}
    if model == "poisson":
        return _poisson(target, safe, train, zones, hours, config)
    raise ValueError(f"modelo desconhecido: {model}")


def _lag_features(history: DemandHistory, day: date, hour: int, zone: str, excluded: tuple[date, ...]) -> tuple[float, float]:
    lag7 = history.value(day - timedelta(days=7), hour, zone)
    weeks = [day - timedelta(days=7 * k) for k in range(1, 5)]
    weeks = [w for w in weeks if w in history.dates and w not in excluded]
    mean4 = sum(history.value(w, hour, zone) for w in weeks) / len(weeks) if weeks else 0.0
    return log(1 + lag7), log(1 + mean4)


def _poisson(
    target: date, history: DemandHistory, train: list[date], zones: list[str], hours: range, config: ForecastConfig
) -> dict[tuple[int, str], float]:
    import numpy as np

    totals = defaultdict(int)
    for d in train:
        for h in range(24):
            for z in zones:
                totals[z] += history.value(d, h, z)
    big = [z for z in zones if totals[z] >= config.min_zone_training_count]
    pooled = [z for z in zones if z not in big]
    labels = big + (["__outros__"] if pooled else [])
    zone_index = {z: i for i, z in enumerate(labels)}
    share = {z: totals[z] / max(1, sum(totals[p] for p in pooled)) for z in pooled}
    hour_list = list(hours)

    def row(day: date, hour: int, label: str) -> list[float]:
        x = [1.0] + [0.0] * (len(labels) - 1) + [0.0] * (len(hour_list) - 1) + [0.0] * 6 + [0.0, 0.0]
        k = zone_index[label]
        if k > 0:
            x[k] = 1.0
        base = len(labels)
        hk = hour_list.index(hour)
        if hk > 0:
            x[base + hk - 1] = 1.0
        base += len(hour_list) - 1
        if day.weekday() > 0:
            x[base + day.weekday() - 1] = 1.0
        base += 6
        members = pooled if label == "__outros__" else [label]
        lags = [_lag_features(history, day, hour, m, config.excluded_dates) for m in members]
        if label == "__outros__":
            raw7 = sum(history.value(day - timedelta(days=7), hour, m) for m in members)
            x[base], x[base + 1] = log(1 + raw7), log(1 + sum(l[1] for l in lags))
        else:
            x[base], x[base + 1] = lags[0]
        return x

    def y(day: date, hour: int, label: str) -> float:
        members = pooled if label == "__outros__" else [label]
        return float(sum(history.value(day, hour, m) for m in members))

    usable = [d for d in train if d - timedelta(days=7) in history.dates]
    if len(usable) < 7:
        return {}
    X = np.array([row(d, h, z) for d in usable for h in hour_list for z in labels])
    Y = np.array([y(d, h, z) for d in usable for h in hour_list for z in labels])
    beta = np.zeros(X.shape[1])
    beta[0] = log(max(Y.mean(), 1e-3))
    penalty = np.full(X.shape[1], config.ridge)
    penalty[0] = 0.0
    for _ in range(50):
        eta = np.clip(X @ beta, -20, 20)
        mu = np.exp(eta)
        grad = X.T @ (Y - mu) - penalty * beta
        hess = (X * mu[:, None]).T @ X + np.diag(penalty)
        step = np.linalg.solve(hess, grad)
        beta += step
        if np.max(np.abs(step)) < 1e-6:
            break
    out: dict[tuple[int, str], float] = {}
    for h in hour_list:
        for label in labels:
            mu = float(np.exp(np.clip(np.array(row(target, h, label)) @ beta, -20, 20)))
            if label == "__outros__":
                for z in pooled:
                    out[(h, z)] = mu * share[z]
            else:
                out[(h, label)] = mu
    return out


def errors(pred: dict[tuple[int, str], float], target: date, history: DemandHistory, hours: range) -> dict[str, float]:
    """WAPE, MAE e desvio de Poisson médio por zona-hora, e erro do total da janela."""
    zones = {z for (_, z) in pred} | {z for (d, h, z) in history.counts if d == target and h in hours}
    abs_err = dev = total_y = 0.0
    n = 0
    total_pred = 0.0
    for h in hours:
        for z in zones:
            yv = history.value(target, h, z)
            mu = max(pred.get((h, z), 0.0), 1e-9)
            abs_err += abs(yv - mu)
            dev += 2 * ((yv * log(yv / mu) if yv > 0 else 0.0) - (yv - mu))
            total_y += yv
            total_pred += pred.get((h, z), 0.0)
            n += 1
    return {
        "wape_zona_hora": abs_err / total_y if total_y else float("nan"),
        "mae_zona_hora": abs_err / n if n else float("nan"),
        "desvio_poisson_medio": dev / n if n else float("nan"),
        "observado_janela": total_y,
        "previsto_janela": total_pred,
        "erro_abs_total_janela": abs(total_pred - total_y),
    }
