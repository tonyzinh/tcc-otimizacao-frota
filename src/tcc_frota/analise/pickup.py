"""Bloco 2 (exploratório, `docs/ESCOPO_FECHADO.md`): pickup das corridas extras e atendimento.

Reexecuta os cenários já testados (regime B, 04–11h, mesmas sementes e mesmos planejadores congelados) com o
rastro opcional do simulador (`trace`), que não altera nenhuma decisão, para obter o pickup simulado de cada
corrida. Corridas extras = atendidas no cenário e não no baseline do mesmo dia; comuns = atendidas nos dois;
perdidas = atendidas só no baseline. Antes de usar o rastro, confere corridas e KM de busca de cada dia contra
os CSV diários existentes. Só agregados saem do módulo.
"""

from __future__ import annotations

import bisect
from collections import defaultdict
from statistics import mean, median

from tcc_frota.algoritmos.base import PlanContext, PlannerSpec, latlon
from tcc_frota.algoritmos.bateria import build_planner, build_scenarios
from tcc_frota.v2 import experiment as ex
from tcc_frota.v2 import forecast as fc
from tcc_frota.v2.fleet import end_of_day
from tcc_frota.v2.sim import reta_km, simulate

DIST_BANDS = ((0, 1), (1, 2), (2, 3), (3, 5), (5, 8), (8, float("inf")))


def _pickups(trace: list) -> dict[int, float]:
    return {rid: km for (_, kind, _, rid, _, km) in trace if kind == "dispatch"}


def day_rides(study, period: str, target, sim, spec: PlannerSpec, model: str, seed: int) -> dict:
    """Pickup por corrida no baseline e no cenário de um dia (mesma lógica de `bateria.evaluate_day`)."""
    window = ex.WINDOWS[ex.MAIN_WINDOW]
    regime = "B"
    reqs, drivers = study.world(period, target, window)
    w = (window[0] * 3600.0, window[1] * 3600.0)
    tb: list = []
    base = simulate(reqs, drivers, sim, w, trace=tb)
    inputs, _ = study.plan_inputs(target, window, regime, drivers, sim.road_factor, model, fc.ForecastConfig())
    origins = {d.did: p for d in drivers if (p := study.fleet.last_position(d.did, end_of_day(target)))}
    planner = build_planner(spec)
    scen = build_scenarios(study, period, target, window, fc.ForecastConfig()) if getattr(planner, "needs_scenarios", False) else ()
    moves = planner.plan(PlanContext(inputs, target, window, regime, sim, ex.EXECUTION[regime], scen, seed))
    tp: list = []
    res = simulate(
        reqs, drivers, sim, w, latlon(moves), max_move_km=planner.max_km, move_mode=ex.EXECUTION[regime], move_origins=origins, trace=tp
    )
    pb, pp = _pickups(tb), _pickups(tp)
    assert len(pb) == base.served and abs(sum(pb.values()) - base.pickup_km) < 1e-6
    assert len(pp) == res.served and abs(sum(pp.values()) - res.pickup_km) < 1e-6
    return {
        "data": target.isoformat(),
        "semente": seed if planner.stochastic else "",
        "cenario": spec.name,
        "served_base": base.served,
        "pickup_base": base.pickup_km,
        "served": res.served,
        "pickup": res.pickup_km,
        "extras": [pp[r] for r in pp.keys() - pb.keys()],
        "comuns": [pp[r] for r in pp.keys() & pb.keys()],
        "perdidas_base": [pb[r] for r in pb.keys() - pp.keys()],
        "baseline": list(pb.values()),
    }


def summary(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "media_km": float("nan"), "mediana_km": float("nan"), "p90_km": float("nan")}
    v = sorted(values)
    return {"n": len(v), "media_km": mean(v), "mediana_km": median(v), "p90_km": v[int(0.9 * (len(v) - 1))]}


def deciles(values: list[float]) -> list[float]:
    v = sorted(values)
    return [v[int(q / 10 * (len(v) - 1))] for q in range(1, 10)] if v else []


def real_pickup(study, days) -> dict:
    """Pickup realizado (`distMotorista`, m → km) das aceitas imediatas 04–11h nos dias dados, com cobertura."""
    hist: dict = {}
    for h in study.silver.historico:
        hist.setdefault(h["codigo"], h)
    accepted = [r for d in days for r in study.requests_by_date.get(d, []) if r["fl_aceito"] and 4 <= r["hora_local"] < 11]
    vals = [
        hist[r["codigo"]]["dist_motorista_m"] / 1000
        for r in accepted
        if r["codigo"] in hist and hist[r["codigo"]]["dist_motorista_m"] not in (None, "")
    ]
    return {
        "aceitas": len(accepted),
        "com_pickup_realizado": len(vals),
        "cobertura_pct": 100 * len(vals) / len(accepted) if accepted else float("nan"),
        "valores": vals,
    }


def unserved_by_distance(study, days) -> list[dict]:
    """Não aceite por distância (reta) ao livre mais próximo na última foto até 10 min antes do pedido."""
    free: dict = defaultdict(list)
    for p in study.gold.frota_snapshot:
        if p["estado"] == 1 and p["fl_coordenada_valida"]:
            free[p["ts_snapshot"]].append((p["lat"], p["lon"]))
    times = sorted(free)
    acc: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    total = 0
    for d in days:
        for r in study.requests_by_date.get(d, []):
            if not (4 <= r["hora_local"] < 11):
                continue
            total += 1
            i = bisect.bisect_right(times, r["ts_pedido"]) - 1
            if i < 0 or (r["ts_pedido"] - times[i]).total_seconds() > 600:
                band = "sem_foto_ate_10min"
            elif not free[times[i]]:
                band = "sem_livre_na_foto"
            else:
                dist = min(reta_km(r["lat_origem"], r["lon_origem"], la, lo) for la, lo in free[times[i]])
                band = next(f"[{a:g},{b:g})" if b != float("inf") else f">={a:g}" for a, b in DIST_BANDS if a <= dist < b)
            a = acc[band]
            a[0] += 1
            a[1] += not r["fl_aceito"]
    order = [f"[{a:g},{b:g})" if b != float("inf") else f">={a:g}" for a, b in DIST_BANDS] + ["sem_livre_na_foto", "sem_foto_ate_10min"]
    return [
        {
            "faixa_distancia_km": b,
            "pedidos": acc[b][0],
            "nao_aceitos": acc[b][1],
            "nao_aceite_pct": 100 * acc[b][1] / acc[b][0] if acc[b][0] else float("nan"),
            "participacao_pct": 100 * acc[b][0] / total if total else float("nan"),
        }
        for b in order
    ]
