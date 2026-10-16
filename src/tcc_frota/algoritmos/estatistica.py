"""Estatística da bateria: reaproveita `v2.stats.compare` e acrescenta Holm, IC de Bonferroni e os critérios.

O bootstrap de Bonferroni usa a mesma semente e a mesma sequência de reamostragens de `v2.stats.bootstrap`
(o IC 95% sai idêntico); só muda o quantil (1 − 0,05/m).
"""
from __future__ import annotations

import random
from math import isfinite

from tcc_frota.v2.stats import compare, s_empty_per_ride_ratio, s_served_ratio

SEED = 20261016
REPS = 2000


def bootstrap_ci(days: list[dict], statistic, level: float, reps: int = REPS, seed: int = SEED) -> tuple[float, float]:
    rng = random.Random(seed)
    values = []
    for _ in range(reps):
        sample = [days[rng.randrange(len(days))] for _ in days]
        v = statistic(sample)
        if isfinite(v):
            values.append(v)
    if not values:
        return float("nan"), float("nan")
    values.sort()
    a = (1 - level) / 2
    return values[int(a * (len(values) - 1))], values[int((1 - a) * (len(values) - 1))]


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    """p ajustado de Holm–Bonferroni (passo a passo, monotônico)."""
    items = sorted((p if isfinite(p) else 1.0, k) for k, p in pvalues.items())
    m = len(items)
    out, running = {}, 0.0
    for i, (p, k) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def breakeven_fraction(days: list[dict]) -> float:
    """f* = 1 − (N_p·B_b/N_b − B_p)/R_p: fração do reposicionamento que precisaria ser "gratuita"
    (não incremental) para o KM vazio por corrida empatar com o baseline. f* ≤ 0: já é menor; f* > 1:
    nem com todo o reposicionamento gratuito empataria; nan: sem reposicionamento."""
    bp = sum(d["p"]["pickup_km"] for d in days)
    rp = sum(d["p"]["reposition_km"] for d in days)
    np_ = sum(d["p"]["served"] for d in days)
    bb = sum(d["b"]["pickup_km"] for d in days)
    nb = sum(d["b"]["served"] for d in days)
    if rp <= 0:
        return float("nan")
    return 1 - (np_ * bb / nb - bp) / rp


def analyse(days: list[dict], m: int) -> dict:
    out = compare(days, REPS, SEED)
    level = 1 - 0.05 / max(1, m)
    lo, hi = bootstrap_ci(days, s_empty_per_ride_ratio, level)
    out["km_vazio_por_corrida_var_pct_ic_bonf_inf"], out["km_vazio_por_corrida_var_pct_ic_bonf_sup"] = 100 * lo, 100 * hi
    lo, hi = bootstrap_ci(days, s_served_ratio, level)
    out["corridas_atendidas_var_pct_ic_bonf_inf"], out["corridas_atendidas_var_pct_ic_bonf_sup"] = 100 * lo, 100 * hi
    out["nivel_bonferroni"] = level
    red = [d["p"]["empty_km"] / d["p"]["served"] < d["b"]["empty_km"] / d["b"]["served"] - 1e-12
           for d in days if d["p"]["served"] and d["b"]["served"]]
    out["dias_com_reducao"] = sum(red)
    out["prop_dias_com_reducao"] = sum(red) / len(red) if red else float("nan")
    tot = {k: sum(d["p"][k] for d in days) for k in ("served", "pickup_km", "reposition_km", "empty_km", "moves_executed",
                                                    "plan_seconds", "km_planejado")}
    base = {k: sum(d["b"][k] for d in days) for k in ("served", "pickup_km", "empty_km")}
    out["km_busca_por_corrida"] = tot["pickup_km"] / tot["served"]
    out["km_repos_por_corrida"] = tot["reposition_km"] / tot["served"]
    out["km_vazio_por_corrida"] = tot["empty_km"] / tot["served"]
    out["km_vazio_por_corrida_base"] = base["empty_km"] / base["served"]
    out["km_busca_por_corrida_base"] = base["pickup_km"] / base["served"]
    out["soma_confere_b_mais_r"] = abs(tot["pickup_km"] + tot["reposition_km"] - tot["empty_km"]) < 1e-6 * max(1.0, tot["empty_km"])
    out["km_medio_por_movimento"] = tot["reposition_km"] / tot["moves_executed"] if tot["moves_executed"] else float("nan")
    drivers = sum(d["p"].get("motoristas_mundo", 0) for d in days)
    out["fracao_motoristas_movidos_pct"] = 100 * tot["moves_executed"] / drivers if drivers else float("nan")
    out["tempo_plano_medio_s"] = tot["plan_seconds"] / len(days)
    out["tempo_plano_max_s"] = max(d["p"].get("plan_seconds_max", d["p"]["plan_seconds"]) for d in days)
    out["fracao_nao_incremental_equilibrio"] = breakeven_fraction(days)
    return out


def criteria(by_month: dict[str, dict], by_month_a: dict[str, dict], holm_p: dict[str, float]) -> dict:
    """Critérios pré-registrados (docs/ORCAMENTO_CONFIGURACOES.md §2) para um algoritmo."""
    months = sorted(by_month)
    c1_raw = all(by_month[m]["km_vazio_por_corrida_var_pct_ic_sup"] < 0 for m in months)
    c1_conf = c1_raw and all(holm_p[m] < 0.05 and by_month[m]["km_vazio_por_corrida_var_pct_ic_bonf_sup"] < 0 for m in months)
    c2 = all(by_month[m]["corridas_atendidas_var_pct_ic_inf"] >= -1.0 for m in months)
    c3 = c1_raw   # medido no simulador por construção
    c4 = (all(by_month[m]["prop_dias_com_reducao"] >= 0.5 for m in months)
          and all(by_month_a.get(m, {}).get("km_vazio_por_corrida_var_pct", float("inf")) <= 0 for m in months))
    c5 = all(by_month[m]["tempo_plano_medio_s"] <= 900 and by_month[m]["tempo_plano_max_s"] <= 3600 for m in months)
    verdict = ("superior (confirmado)" if c1_conf and c2 and c3 and c4 and c5
               else "indício, não confirmado" if c1_raw and c2 and c3 and c4 and c5 else "não passa")
    return {"c1_km_vazio_menor": c1_raw, "c1_confirmado_holm": c1_conf, "c2_nao_inferior_atendimento": c2,
            "c3_reducao_no_simulador": c3, "c4_consistencia": c4, "c5_tempo": c5, "veredito": verdict}
