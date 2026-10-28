"""Inferência por dia da Fase 1: estatísticas pareadas, bootstrap, Romano–Wolf, Fieller, MDE e benefício líquido.

Substitui a razão `e` como estatística de decisão (docs/V2_PREREGISTRO.md §5). Unidade de reamostragem: o dia.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from math import isfinite, sqrt
from pathlib import Path

import numpy as np
from scipy import stats as sps

FIELDS = ("n_requests", "served", "pickup_km", "reposition_km", "empty_km", "wait_sum")
BASELINE = "sem_reposicionamento"
Z_MDE = 1.959964 + 0.841621  # 5% bilateral, poder 80%
NON_INFERIORITY_PP = -1.0     # margem primária para ΔN% (desvio D1); -2 pp é sensibilidade
NON_INFERIORITY_SENS_PP = -2.0


@dataclass(frozen=True)
class Pairs:
    """Métricas por dia do baseline (`b`) e do plano (`p`) para uma linha (período, janela, regime, cenário)."""
    key: tuple[str, str, str, str]
    dates: tuple[date, ...]
    b: dict[str, np.ndarray]
    p: dict[str, np.ndarray]


def load_pairs(path: str | Path) -> dict[tuple[str, str, str, str], Pairs]:
    """Lê `dias_cenarios.csv` (derivado agregado por dia; sem IDs nem coordenadas) e pareia plano × baseline."""
    base: dict[tuple, dict] = {}
    plans: dict[tuple, dict[date, dict]] = {}
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            day = date.fromisoformat(row["data"])
            values = {k: float(row[k]) for k in FIELDS}
            if row["cenario"] == BASELINE:
                base[(row["periodo"], row["janela"], row["regime"], day)] = values
            else:
                plans.setdefault((row["periodo"], row["janela"], row["regime"], row["cenario"]), {})[day] = values
    out = {}
    for key, days in plans.items():
        ordered = sorted(days)
        try:
            b_rows = [base[(key[0], key[1], key[2], d)] for d in ordered]
        except KeyError as err:
            raise ValueError(f"dia sem baseline pareado: {err}") from None
        out[key] = Pairs(key, tuple(ordered),
                         {k: np.array([r[k] for r in b_rows]) for k in FIELDS},
                         {k: np.array([days[d][k] for d in ordered]) for k in FIELDS})
    return out


def _tot(a: np.ndarray, idx: np.ndarray | None):
    return a.sum() if idx is None else a[idx].sum(axis=1)


def _div(a, b):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(np.asarray(b) != 0, np.asarray(a, dtype=float) / np.where(np.asarray(b) == 0, 1, b), np.nan)


def stat_km_vazio_pct(pr: Pairs, idx=None):
    """Variação % do KM vazio por corrida (razão de somas), como na v1."""
    p = _div(_tot(pr.p["empty_km"], idx), _tot(pr.p["served"], idx))
    b = _div(_tot(pr.b["empty_km"], idx), _tot(pr.b["served"], idx))
    return (_div(p, b) - 1) * 100


def stat_served_pct(pr: Pairs, idx=None):
    return (_div(_tot(pr.p["served"], idx), _tot(pr.b["served"], idx)) - 1) * 100


def stat_d_served_day(pr: Pairs, idx=None):
    n = len(pr.dates)
    return _tot(pr.p["served"] - pr.b["served"], idx) / n


def stat_d_empty_day(pr: Pairs, idx=None):
    n = len(pr.dates)
    return _tot(pr.p["empty_km"] - pr.b["empty_km"], idx) / n


def stat_nb(pr: Pairs, e_star: float, idx=None):
    """NB(e*) = ΔN_dia − Δ(B+R)_dia / e*, em corridas-equivalentes por dia (sem razão)."""
    return stat_d_served_day(pr, idx) - stat_d_empty_day(pr, idx) / e_star


@dataclass(frozen=True)
class Interval:
    point: float
    lo: float
    hi: float
    se: float
    boot: np.ndarray  # replicações (B,), mantidas para Romano–Wolf


def summarize(point, boot: np.ndarray) -> Interval:
    v = boot[np.isfinite(boot)]
    if len(v) < 0.9 * len(boot):
        return Interval(float(point), float("nan"), float("nan"), float("nan"), boot)
    return Interval(float(point), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)),
                    float(np.std(v, ddof=1)), boot)


def widest(intervals: dict[str, Interval]) -> tuple[str, Interval]:
    """Variante de IC mais largo (regra pré-registrada para não escolher o IC mais conveniente)."""
    ok = {k: v for k, v in intervals.items() if isfinite(v.lo) and isfinite(v.hi)}
    if not ok:
        name = next(iter(intervals))
        return name, intervals[name]
    name = max(ok, key=lambda k: ok[k].hi - ok[k].lo)
    return name, ok[name]


def t_stat(iv: Interval, direction: str) -> float:
    """Estatística studentizada; valor alto = evidência a favor da hipótese alternativa da direção."""
    if not isfinite(iv.se) or iv.se == 0:
        return 0.0
    if direction == "reducao":
        return -iv.point / iv.se
    if direction == "aumento":
        return iv.point / iv.se
    if direction == "nao_inferior":
        return (iv.point - NON_INFERIORITY_PP) / iv.se
    if direction == "nao_inferior_sens":
        return (iv.point - NON_INFERIORITY_SENS_PP) / iv.se
    raise ValueError(direction)


def t_boot(iv: Interval, direction: str) -> np.ndarray:
    """Réplicas centradas e studentizadas sob H0 (E2/E3 do pré-registro)."""
    if not isfinite(iv.se) or iv.se == 0:
        return np.zeros_like(iv.boot)
    z = (iv.boot - iv.point) / iv.se
    out = -z if direction == "reducao" else z  # demais direções: caudas à direita
    return np.where(np.isfinite(out), out, 0.0)


def raw_p(t_obs: float, tb: np.ndarray) -> float:
    return float((1 + np.sum(tb >= t_obs)) / (len(tb) + 1))


def romano_wolf(t_obs: np.ndarray, t_boots: np.ndarray) -> np.ndarray:
    """P-valores ajustados de Romano–Wolf (stepdown, máximo das estatísticas). `t_boots` tem forma (B, m)."""
    m = len(t_obs)
    order = np.argsort(-t_obs, kind="stable")
    adj = np.empty(m)
    running = 0.0
    for rank, j in enumerate(order):
        maxima = t_boots[:, order[rank:]].max(axis=1)
        running = max(running, (1 + np.sum(maxima >= t_obs[j])) / (len(maxima) + 1))
        adj[j] = min(running, 1.0)
    return adj


def holm(pvalues: np.ndarray) -> np.ndarray:
    from statsmodels.stats.multitest import multipletests
    return multipletests(pvalues, alpha=0.05, method="holm")[1]


def fieller(a: np.ndarray, b: np.ndarray, level: float = 0.95) -> tuple[float, float] | None:
    """IC de Fieller para mean(a)/mean(b). `None` = intervalo ilimitado (denominador não distinguível de zero)."""
    n = len(a)
    ma, mb = a.mean(), b.mean()
    va, vb = a.var(ddof=1), b.var(ddof=1)
    cov = np.cov(a, b, ddof=1)[0, 1]
    t2 = sps.t.ppf(0.5 + level / 2, n - 1) ** 2
    qa = mb**2 - t2 * vb / n
    qb = -2 * (ma * mb - t2 * cov / n)
    qc = ma**2 - t2 * va / n
    if qa <= 0:
        return None
    disc = qb**2 - 4 * qa * qc
    if disc < 0:
        return None
    r = sqrt(disc)
    return (-qb - r) / (2 * qa), (-qb + r) / (2 * qa)


def mde(se: float) -> float:
    """Menor efeito detectável (bilateral 5%, poder 80%) para um erro-padrão `se`."""
    return Z_MDE * se
