"""Bloco 1 (exploratório, `docs/ESCOPO_FECHADO.md`): previsão D+1 da demanda por célula H3 r7 × hora e erro (WAPE).

Unidade célula × hora cheia (4–10) × dia, a mesma do simulador. Cada previsão usa só dias anteriores ao dia do
corte (D = alvo − 1, excluído), sem o Carnaval, como `v2/forecast.training_dates`.

- M0: média de alvo − 7 e alvo − 14 (mesmo dia da semana, duas últimas semanas) — linha de base ingênua.
- M1: média por célula × hora × tipo de dia (útil/fim de semana) nos 56 dias anteriores ao corte.
- M2: `PoissonRegressor` (scikit-learn) com one-hot de célula, hora e dia da semana; α escolhido na calibração.
- Msim: o modelo que o simulador usa (`media_dia_semana`, 56 dias), para conferência com o artigo.

WAPE = Σ|ŷ − y| / Σy, sempre a partir dos erros por hora; faixas e global somam erros e solicitações das horas.
"""
from __future__ import annotations

import random
from collections import defaultdict
from datetime import date, timedelta

from tcc_frota.v2 import forecast as fc

HOURS = tuple(range(4, 11))
BANDS = {"04-07": (4, 5, 6), "07-10": (7, 8, 9), "10-11": (10,)}
ALPHAS = (0.01, 0.1, 1.0)
SEED, REPS = 20261016, 2000
MODELS = ("M0", "M1", "M2", "Msim")


def train_dates(target: date, history: fc.DemandHistory, cfg: fc.ForecastConfig) -> list[date]:
    return fc.training_dates(target, history, cfg)


def zones_of(history: fc.DemandHistory, days: list[date]) -> list[str]:
    return fc.zones_in(history, days)


def m0(target, history, cfg) -> dict[tuple[int, str], float]:
    cut = fc.cutoff_date(target)
    refs = [target - timedelta(days=k) for k in (7, 14)]
    refs = [d for d in refs if d in history.dates and d < cut and d not in cfg.excluded_dates]
    if not refs:
        return {}
    zones = zones_of(history, train_dates(target, history, cfg))
    return {(h, z): sum(history.value(d, h, z) for d in refs) / len(refs) for h in HOURS for z in zones}


def m1(target, history, cfg) -> dict[tuple[int, str], float]:
    train = train_dates(target, history, cfg)
    weekend = target.weekday() >= 5
    same = [d for d in train if (d.weekday() >= 5) == weekend]
    if not same:
        return {}
    zones = zones_of(history, train)
    return {(h, z): sum(history.value(d, h, z) for d in same) / len(same) for h in HOURS for z in zones}


def m2(target, history, cfg, alpha: float) -> dict[tuple[int, str], float]:
    import numpy as np
    from scipy.sparse import csr_matrix
    from sklearn.linear_model import PoissonRegressor

    train = train_dates(target, history, cfg)
    zones = zones_of(history, train)
    if len(train) < 7 or not zones:
        return {}
    zi = {z: i for i, z in enumerate(zones)}
    nz, nh = len(zones), len(HOURS)

    def cols(day: date, h: int, z: str) -> list[int]:
        return [zi[z], nz + HOURS.index(h), nz + nh + day.weekday()]

    rows, cidx, y = [], [], []
    r = 0
    for d in train:
        for h in HOURS:
            for z in zones:
                rows += [r, r, r]
                cidx += cols(d, h, z)
                y.append(history.value(d, h, z))
                r += 1
    x = csr_matrix((np.ones(len(rows)), (rows, cidx)), shape=(r, nz + nh + 7))
    model = PoissonRegressor(alpha=alpha, max_iter=1000).fit(x, np.array(y, dtype=float))
    rows, cidx, keys = [], [], []
    for k, (h, z) in enumerate((h, z) for h in HOURS for z in zones):
        rows += [k, k, k]
        cidx += cols(target, h, z)
        keys.append((h, z))
    xt = csr_matrix((np.ones(len(rows)), (rows, cidx)), shape=(len(keys), nz + nh + 7))
    return dict(zip(keys, model.predict(xt).tolist()))


def msim(target, history, cfg) -> dict[tuple[int, str], float]:
    return fc.predict("media_dia_semana", target, history, range(4, 11), cfg)


def strata(target, history, cfg) -> dict[str, str]:
    """'alto' = ≥ 1 solicitação/dia em média na janela 04–11h dos dias de treino (definido antes do alvo)."""
    train = train_dates(target, history, cfg)
    tot: dict[str, float] = defaultdict(float)
    for (d, h, z), v in history.counts.items():
        if d in train and h in HOURS and z:
            tot[z] += v
    return {z: ("alto" if train and v / len(train) >= 1.0 else "baixo") for z, v in tot.items()}


def day_errors(pred: dict, target: date, history: fc.DemandHistory, strat: dict[str, str]) -> list[dict]:
    """Uma linha por hora e estrato: soma de |erro|, de y e de ŷ (base de todas as agregações)."""
    zones = {z for (_, z) in pred} | {z for (d, h, z) in history.counts if d == target and h in HOURS and z}
    acc: dict[tuple[int, str], list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
    for h in HOURS:
        for z in zones:
            yv, mu = history.value(target, h, z), pred.get((h, z), 0.0)
            a = acc[(h, strat.get(z, "baixo"))]
            a[0] += abs(mu - yv)
            a[1] += yv
            a[2] += mu
    return [{"hora": h, "estrato": s, "abs_err": a[0], "y": a[1], "yhat": a[2]} for (h, s), a in sorted(acc.items())]


def scopes() -> dict[str, callable]:
    out = {f"hora_{h:02d}": (lambda r, h=h: r["hora"] == h) for h in HOURS}
    out.update({f"faixa_{b}": (lambda r, hs=hs: r["hora"] in hs) for b, hs in BANDS.items()})
    out["global"] = lambda r: True
    out["estrato_alto"] = lambda r: r["estrato"] == "alto"
    out["estrato_baixo"] = lambda r: r["estrato"] == "baixo"
    return out


def aggregate(records: list[dict], days: list[str]) -> list[dict]:
    """WAPE, viés e IC 95% por bootstrap de dias para cada escopo (horas, faixas, global, estratos)."""
    by_day: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_day[r["data"]].append(r)
    sc = scopes()
    sums = {name: {d: [sum(r[k] for r in by_day[d] if f(r)) for k in ("abs_err", "y", "yhat")] for d in days}
            for name, f in sc.items()}
    rng = random.Random(SEED)
    samples = [[days[rng.randrange(len(days))] for _ in days] for _ in range(REPS)]
    out = []
    for name in sc:
        s = sums[name]
        e, y, yh = (sum(s[d][i] for d in days) for i in range(3))
        boot = []
        for smp in samples:
            ey = sum(s[d][1] for d in smp)
            if ey > 0:
                boot.append(sum(s[d][0] for d in smp) / ey)
        boot.sort()
        lo = boot[int(0.025 * (len(boot) - 1))] if boot else float("nan")
        hi = boot[int(0.975 * (len(boot) - 1))] if boot else float("nan")
        out.append({"escopo": name, "dias": len(days), "solicitacoes": y, "previsto": yh,
                    "wape": e / y if y else float("nan"), "wape_ic_inf": lo, "wape_ic_sup": hi,
                    "vies": yh / y - 1 if y else float("nan")})
    return out


def dates(year: int, month: int, first: int, last: int) -> list[date]:
    return [date(year, month, d) for d in range(first, last + 1)]
