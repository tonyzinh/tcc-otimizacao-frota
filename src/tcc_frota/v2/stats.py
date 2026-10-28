"""Estatística pareada por dia (Fase 6): bootstrap de razões e teste de permutação por troca de sinal."""

from __future__ import annotations

import random
from itertools import product
from math import isfinite


def ratio(num: float, den: float) -> float:
    return num / den if den else float("nan")


def bootstrap(days: list[dict], statistic, reps: int = 2000, seed: int = 20261016) -> tuple[float, float, float]:
    """Estimativa pontual e IC 95% percentil, reamostrando dias com reposição."""
    point = statistic(days)
    rng = random.Random(seed)
    values = []
    for _ in range(reps):
        sample = [days[rng.randrange(len(days))] for _ in days]
        v = statistic(sample)
        if isfinite(v):
            values.append(v)
    if not values:
        return point, float("nan"), float("nan")
    values.sort()
    lo = values[int(0.025 * (len(values) - 1))]
    hi = values[int(0.975 * (len(values) - 1))]
    return point, lo, hi


def sign_flip_pvalue(diffs: list[float], reps: int = 20000, seed: int = 20261016) -> float:
    """P-valor bilateral do teste de permutação pareado (exato até 16 dias)."""
    diffs = [d for d in diffs if isfinite(d)]
    n = len(diffs)
    if n == 0:
        return float("nan")
    observed = abs(sum(diffs))
    if n <= 16:
        count = total = 0
        for signs in product((1, -1), repeat=n):
            total += 1
            count += abs(sum(s * d for s, d in zip(signs, diffs))) >= observed - 1e-12
        return count / total
    rng = random.Random(seed)
    count = sum(abs(sum(d if rng.random() < 0.5 else -d for d in diffs)) >= observed - 1e-12 for _ in range(reps))
    return (count + 1) / (reps + 1)


# Estatísticas sobre pares de dias {"b": métricas do baseline, "p": métricas do proposto}.
def s_served_ratio(days):
    return ratio(sum(d["p"]["served"] for d in days), sum(d["b"]["served"] for d in days)) - 1


def s_extra_rides_per_day(days):
    return sum(d["p"]["served"] - d["b"]["served"] for d in days) / len(days)


def s_pickup_per_ride_ratio(days):
    p = ratio(sum(d["p"]["pickup_km"] for d in days), sum(d["p"]["served"] for d in days))
    b = ratio(sum(d["b"]["pickup_km"] for d in days), sum(d["b"]["served"] for d in days))
    return ratio(p, b) - 1


def s_reposition_per_day(days):
    return sum(d["p"]["reposition_km"] for d in days) / len(days)


def s_empty_per_ride_ratio(days):
    p = ratio(sum(d["p"]["empty_km"] for d in days), sum(d["p"]["served"] for d in days))
    b = ratio(sum(d["b"]["empty_km"] for d in days), sum(d["b"]["served"] for d in days))
    return ratio(p, b) - 1


def s_incremental_km_per_extra_ride(days):
    dk = sum(d["p"]["empty_km"] - d["b"]["empty_km"] for d in days)
    dr = sum(d["p"]["served"] - d["b"]["served"] for d in days)
    return dk / dr if dr > 0 else float("nan")


def s_wait_diff(days):
    p = ratio(sum(d["p"]["wait_sum"] for d in days), sum(d["p"]["served"] for d in days))
    b = ratio(sum(d["b"]["wait_sum"] for d in days), sum(d["b"]["served"] for d in days))
    return p - b


PRIMARY = {
    "corridas_atendidas_var_pct": (s_served_ratio, 100),
    "corridas_extras_por_dia": (s_extra_rides_per_day, 1),
    "km_busca_por_corrida_var_pct": (s_pickup_per_ride_ratio, 100),
    "km_reposicionamento_por_dia": (s_reposition_per_day, 1),
    "km_vazio_por_corrida_var_pct": (s_empty_per_ride_ratio, 100),
    "km_vazio_incremental_por_corrida_extra": (s_incremental_km_per_extra_ride, 1),
    "tempo_ate_passageiro_dif_s": (s_wait_diff, 1),
}


def compare(days: list[dict], reps: int = 2000, seed: int = 20261016) -> dict[str, float]:
    out: dict[str, float] = {"dias": len(days)}
    for name, (fn, scale) in PRIMARY.items():
        point, lo, hi = bootstrap(days, fn, reps, seed)
        out[name] = point * scale
        out[name + "_ic_inf"] = lo * scale
        out[name + "_ic_sup"] = hi * scale
    out["p_corridas"] = sign_flip_pvalue([d["p"]["served"] - d["b"]["served"] for d in days])
    out["p_km_vazio_por_corrida"] = sign_flip_pvalue(
        [ratio(d["p"]["empty_km"], d["p"]["served"]) - ratio(d["b"]["empty_km"], d["b"]["served"]) for d in days]
    )
    out["p_tempo"] = sign_flip_pvalue(
        [ratio(d["p"]["wait_sum"], d["p"]["served"]) - ratio(d["b"]["wait_sum"], d["b"]["served"]) for d in days]
    )
    for k in ("served", "pickup_km", "reposition_km", "empty_km", "n_requests", "moves_planned", "moves_executed"):
        out[f"soma_base_{k}"] = sum(d["b"][k] for d in days)
        out[f"soma_prop_{k}"] = sum(d["p"][k] for d in days)
    out["taxa_execucao_pct"] = 100 * ratio(out["soma_prop_moves_executed"], out["soma_prop_moves_planned"])
    return out
