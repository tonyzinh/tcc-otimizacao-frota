"""Fase 2: controles negativo e positivo, poder e cobertura do procedimento de inferência (semi-sintético).

Pseudopopulação: os dias pareados reais de um plano de referência, com as diferenças diárias recentradas (média zero, logo o
efeito verdadeiro é nulo) e um efeito conhecido injetado em esperança. Cada réplica sorteia uma amostra de dias dessa
pseudopopulação (iid ou em blocos circulares de 3 dias, para preservar parte da dependência serial), injeta o efeito com
ruído binomial e é analisada com o procedimento real da Fase 1. A verdade é calculada sobre a pseudopopulação, não nominal.
Limite: a dependência entre dias só entra pelos blocos; o simulador em si não é exercitado (ver `fase2_simulador`).
"""

from __future__ import annotations

from math import isfinite

import numpy as np

from . import inferencia as inf
from .reamostragem import SCHEMES, indices, scheme_seed

N_EFFECTS = (0.0, 0.25, 0.5, 1.0, 2.0, 5.0)  # ΔN% injetado (pré-registro §8, Fase 2)
KM_EFFECTS = (1.0, 2.0, 5.0, 10.0)  # redução % injetada no KM vazio por corrida


def population(ref: inf.Pairs, n_pct: float, km_pct: float) -> inf.Pairs:
    """Pseudopopulação com efeito esperado: diferenças reais recentradas + ΔN% e redução de KM em esperança."""
    b, p = ref.b, ref.p
    d_s = p["served"] - b["served"]
    d_e = p["empty_km"] - b["empty_km"]
    served = np.maximum(b["served"] + (d_s - d_s.mean()), 0.0)
    empty = b["empty_km"] + (d_e - d_e.mean())
    lost = np.maximum(b["n_requests"] - b["served"], 0.0)
    km_ride = np.divide(b["empty_km"], b["served"], out=np.zeros_like(b["empty_km"]), where=b["served"] > 0)
    if n_pct:
        extra = np.minimum(n_pct / 100.0 * b["served"], lost)  # esperança do binomial
        served = served + extra
        empty = empty + extra * km_ride
    if km_pct:
        empty = empty * (1 - km_pct / 100.0)
    p2 = dict(p)
    p2["served"], p2["empty_km"] = served, empty
    return inf.Pairs(ref.key, ref.dates, b, p2)


def sample(pop: inf.Pairs, ref: inf.Pairs, idx: np.ndarray, rng: np.random.Generator, n_pct: float) -> inf.Pairs:
    """Uma réplica: dias `idx` da pseudopopulação, com extras binomiais (ruído do efeito injetado)."""
    b = {k: v[idx] for k, v in pop.b.items()}
    p = {k: v[idx] for k, v in pop.p.items()}
    if n_pct:
        lost = np.maximum(ref.b["n_requests"][idx] - ref.b["served"][idx], 0.0)
        prob = np.clip(n_pct / 100.0 * ref.b["served"][idx] / np.maximum(lost, 1.0), 0.0, 1.0)
        extra = rng.binomial(lost.astype(int), prob).astype(float)
        mean_extra = np.minimum(n_pct / 100.0 * ref.b["served"][idx], lost)
        km_ride = np.divide(ref.b["empty_km"][idx], ref.b["served"][idx], out=np.zeros(len(idx)), where=ref.b["served"][idx] > 0)
        p["served"] = p["served"] + (extra - mean_extra)
        p["empty_km"] = p["empty_km"] + (extra - mean_extra) * km_ride
    return inf.Pairs(pop.key, pop.dates, b, p)


def decide(pr: inf.Pairs, boot_idx: dict[str, np.ndarray]) -> dict:
    """IC (variante mais larga e iid) de ΔN% e ΔKM%, com as rejeições de H0 = 0."""
    out = {}
    for name, fn in (("n", inf.stat_served_pct), ("km", inf.stat_km_vazio_pct)):
        point = fn(pr)
        ivs = {s: inf.summarize(point, np.asarray(fn(pr, I))) for s, I in boot_idx.items()}
        _, w = inf.widest(ivs)
        out[name] = {
            "point": float(point),
            "lo": w.lo,
            "hi": w.hi,
            "reject_widest": bool(isfinite(w.lo) and (w.lo > 0 or w.hi < 0)),
            "reject_iid": bool(isfinite(ivs["iid"].lo) and (ivs["iid"].lo > 0 or ivs["iid"].hi < 0)),
            "reject_any_variant": any(isfinite(v.lo) and (v.lo > 0 or v.hi < 0) for v in ivs.values()),
        }
    return out


def curve(
    ref: inf.Pairs,
    label: str,
    replicas: int = 1000,
    reps: int = 1000,
    seed: int = 20261028,
    worlds: tuple[str, ...] = ("iid", "circular_b3"),
) -> list[dict]:
    """Poder, falsos positivos e cobertura por efeito injetado. `label` (período) fixa as matrizes de reamostragem do IC."""
    boot_idx = {s: indices(s, list(ref.dates), reps, scheme_seed(label, s)) for s in SCHEMES}
    rows = []
    cases = [("N", e, 0.0) for e in N_EFFECTS] + [("KM", 0.0, e) for e in KM_EFFECTS]
    for world in worlds:
        sample_idx = indices(world, list(ref.dates), replicas, scheme_seed(label + "|mundo", world))
        for kind, n_pct, km_pct in cases:
            pop = population(ref, n_pct, km_pct)
            truth_n, truth_km = inf.stat_served_pct(pop), inf.stat_km_vazio_pct(pop)
            rng = np.random.default_rng(seed + int(10 * n_pct + 100 * km_pct))
            hits = [decide(sample(pop, ref, sample_idx[r], rng, n_pct), boot_idx) for r in range(replicas)]
            row = {
                "periodo": label,
                "mundo_de_amostragem": world,
                "efeito": kind,
                "delta_n_pct_injetado": n_pct,
                "reducao_km_pct_injetada": -km_pct,
                "verdade_delta_n_pct": float(truth_n),
                "verdade_delta_km_pct": float(truth_km),
                "replicas": replicas,
            }
            for k, truth in (("n", truth_n), ("km", truth_km)):
                h = [x[k] for x in hits]
                row[f"rejeita_{k}_ic_mais_largo"] = float(np.mean([x["reject_widest"] for x in h]))
                row[f"rejeita_{k}_ic_iid"] = float(np.mean([x["reject_iid"] for x in h]))
                row[f"rejeita_{k}_qualquer_variante"] = float(np.mean([x["reject_any_variant"] for x in h]))
                row[f"cobertura_{k}_ic_mais_largo"] = float(np.mean([x["lo"] <= truth <= x["hi"] for x in h if isfinite(x["lo"])]))
                row[f"vies_{k}_pp"] = float(np.mean([x["point"] for x in h]) - truth)
            rows.append(row)
    return rows
