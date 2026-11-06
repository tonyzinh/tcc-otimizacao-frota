"""Validação do simulador no cenário sem reposicionamento (dias de teste, 4h às 11h), só com agregados.

Uso: TCC_REAL_DATA_AUTHORIZED=YES PYTHONPATH=src python scripts/validar_simulador.py
Saídas (fora do Git): resultados/validacao_simulador/*.csv e resumo.json.

Usa os parâmetros congelados da rodada do artigo (`bateria.load_frozen`) e o rastro opcional do simulador
(`trace`), que não altera nenhuma decisão. Antes de agregar, confere a assinatura SHA-256 das entradas de cada
dia contra `dias_cenarios.csv` da rodada de referência. Nenhum identificador, coordenada ou registro sai do
script: só contagens, quantis e razões agregadas.

a) tempo até o passageiro: simulado (pedido → chegada ao passageiro) × observado (`s_registro_ate_chegada` das
   atendidas, a mesma medida do Quadro de calibração);
b) atendimento por hora: atendidas no simulado × aceitas observadas, sobre os mesmos pedidos;
c) distância até o passageiro nas corridas com `distMotorista` registrado: (i) Haversine da posição real do
   motorista antes do aceite × fator rua/reta calibrado, sobre a registrada (testa o fator); (ii) distância do
   motorista que o simulador despachou, sobre a registrada (fator + despacho/posição); (iii) linha reta do
   motorista simulado sobre a do motorista real (só despacho/posição).
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from statistics import mean

from tcc_frota.algoritmos import bateria
from tcc_frota.v2 import experiment as ex
from tcc_frota.v2.sim import reta_km, simulate

OUT = Path("resultados/validacao_simulador")
WINDOW = "04-11"
QS = (10, 25, 50, 75, 90)
ECDF_GRID = range(0, 3601, 30)
REFERENCE = "guloso_marginal_a0.2"


def quantile(values: list[float], q: float) -> float:
    """Quantil por interpolação linear (q em %)."""
    v = sorted(values)
    if not v:
        return float("nan")
    pos = q / 100 * (len(v) - 1)
    i = int(pos)
    return v[i] if i + 1 >= len(v) else v[i] + (v[i + 1] - v[i]) * (pos - i)


def describe(values: list[float]) -> dict:
    out = {"n": len(values), "media": mean(values) if values else float("nan")}
    out.update({f"p{q}": quantile(values, q) for q in QS})
    return out


def ecdf(values: list[float], x: float) -> float:
    return sum(v <= x for v in values) / len(values) if values else float("nan")


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()})


def reference_signatures(run_id: str) -> dict:
    path = Path(f"reports/runs/tcc_final/{run_id}/individual/dias_cenarios.csv")
    with path.open(encoding="utf-8") as h:
        return {
            (r["periodo"], r["data"]): r["signature"]
            for r in csv.DictReader(h)
            if r["janela"] == WINDOW and r["regime"] == "B" and r["cenario"] == "sem_reposicionamento"
        }


def period_data(study, period: str, sim, signatures: dict) -> dict:
    window = ex.WINDOWS[WINDOW]
    w = (window[0] * 3600.0, window[1] * 3600.0)
    hist: dict = {}
    for h in study.silver.historico:
        hist.setdefault(h["codigo"], h)
    acc = {"t_sim": [], "t_obs": [], "hora": {}, "c_fator": [], "c_fator_05": [], "c_sim": [], "c_reta": [], "soma": [0.0, 0.0, 0.0]}
    acc["contagem"] = {"aceitas": 0, "com_registro": 0, "registro_zero": 0, "sem_posicao_real": 0, "nao_atendida_no_sim": 0}
    checked = 0
    for day in ex.PERIODS[period].test:
        reqs, drivers = study.world(period, day, window)
        trace: list = []
        base = simulate(reqs, drivers, sim, w, trace=trace)
        if base.signature != signatures[(period, day.isoformat())]:
            raise AssertionError(f"assinatura diferente da rodada de referência em {period}/{day}")
        checked += 1
        by_id = {r.rid: r for r in reqs}
        dispatch = {rid: km for (_, kind, _, rid, _, km) in trace if kind == "dispatch"}
        pickup_t = {rid: t for (t, kind, _, rid, _, _) in trace if kind == "pickup"}
        assert len(dispatch) == base.served and abs(sum(dispatch.values()) - base.pickup_km) < 1e-6
        acc["t_sim"] += [pickup_t[rid] - by_id[rid].t for rid in pickup_t]
        for hour, n in base.requests_by_hour.items():
            slot = acc["hora"].setdefault(hour, [0, 0, 0])
            slot[0] += n
            slot[1] += base.served_by_hour.get(hour, 0)
        observed = [r for r in study.requests_by_date.get(day, []) if r["codigo"] in by_id]
        assert len(observed) == base.n_requests
        for r in observed:
            if r["fl_aceito"]:
                acc["hora"][by_id[r["codigo"]].hour][2] += 1
            if r["grupo_desfecho"] == "atendida" and r["s_registro_ate_chegada"]:
                acc["t_obs"].append(r["s_registro_ate_chegada"])
            if not r["fl_aceito"]:
                continue
            acc["contagem"]["aceitas"] += 1
            h = hist.get(r["codigo"])
            if not h or h["dist_motorista_m"] in (None, ""):
                continue
            acc["contagem"]["com_registro"] += 1
            reg_km = float(h["dist_motorista_m"]) / 1000
            if reg_km <= 0:
                acc["contagem"]["registro_zero"] += 1
                continue
            p = study.fleet.last_position(h["motorista_pseud"], r["ts_aceite"]) if h["motorista_pseud"] and r["ts_aceite"] else None
            reta_real = reta_km(p[0], p[1], r["lat_origem"], r["lon_origem"]) if p else None
            if reta_real is None:
                acc["contagem"]["sem_posicao_real"] += 1
            else:
                acc["c_fator"].append(reta_real * sim.road_factor / reg_km)
                if reta_real >= 0.5:
                    acc["c_fator_05"].append(reta_real * sim.road_factor / reg_km)
            if r["codigo"] not in dispatch:
                acc["contagem"]["nao_atendida_no_sim"] += 1
                continue
            sim_km = dispatch[r["codigo"]]
            acc["c_sim"].append(sim_km / reg_km)
            if reta_real is not None and reta_real > 0:
                acc["c_reta"].append(sim_km / sim.road_factor / reta_real)
                acc["soma"][0] += reg_km
                acc["soma"][1] += sim_km
                acc["soma"][2] += reta_real * sim.road_factor
    acc["dias_conferidos"] = checked
    return acc


def main() -> None:
    if os.environ.get("TCC_REAL_DATA_AUTHORIZED") != "YES":
        sys.exit("defina TCC_REAL_DATA_AUTHORIZED=YES (processamento local autorizado)")
    frozen = bateria.load_frozen()
    ref = json.loads(bateria.REFERENCE_RUN.read_text(encoding="utf-8"))
    signatures = reference_signatures(ref["run_id"])
    study = bateria.build_study(Path("data/raw"))
    quant, curve, hours, ratios, summary = [], [], [], [], {"run_referencia": ref["run_id"], "janela": WINDOW, "periodos": {}}
    for period in ex.PERIODS:
        sim = frozen.sims[period]
        a = period_data(study, period, sim, signatures)
        for fonte, vals in (("simulado", a["t_sim"]), ("observado", a["t_obs"])):
            quant.append({"periodo": period, "fonte": fonte, **describe(vals)})
        ks = 0.0
        for x in ECDF_GRID:
            fs, fo = ecdf(a["t_sim"], x), ecdf(a["t_obs"], x)
            ks = max(ks, abs(fs - fo))
            curve.append({"periodo": period, "segundos": x, "acumulada_simulado": fs, "acumulada_observado": fo})
        for hour in sorted(a["hora"]):
            n, s, o = a["hora"][hour]
            hours.append(
                {"periodo": period, "hora": hour, "pedidos": n, "atendidas_simulado": s, "aceitas_observado": o,
                 "taxa_simulado_pct": 100 * s / n, "taxa_observado_pct": 100 * o / n, "diferenca_pp": 100 * (s - o) / n}
            )
        for medida, vals in (
            ("fator: reta real x fator / registrada", a["c_fator"]),
            ("fator: idem, reta >= 0,5 km", a["c_fator_05"]),
            ("simulada / registrada", a["c_sim"]),
            ("reta do simulado / reta real", a["c_reta"]),
        ):
            ratios.append({"periodo": period, "medida": medida, **describe(vals)})
        reg, simk, fat = a["soma"]
        p = next(x for x in ref["principal"] if x["periodo"] == period and x["janela"] == WINDOW and x["regime"] == "B" and x["cenario"] == REFERENCE)
        base_ride = p["soma_base_empty_km"] / p["soma_base_served"]
        inc_ride = p["soma_prop_empty_km"] / p["soma_prop_served"] - base_ride
        scale = simk / reg if reg else float("nan")
        summary["periodos"][period] = {
            "parametros_simulador": {"raio_km": sim.radius_km, "velocidade_kmh": sim.speed_kmh, "fator_rua_reta": sim.road_factor, "paciencia_s": sim.patience_s},
            "dias_com_assinatura_conferida": a["dias_conferidos"],
            "contagens_c": a["contagem"],
            "ks_tempo_max_dif": ks,
            "pareadas_c_n": len(a["c_reta"]),
            "razao_somas_simulada_registrada": scale,
            "razao_somas_fator_registrada": fat / reg if reg else float("nan"),
            "razao_somas_reta_simulado_reta_real": simk / fat if fat else float("nan"),
            f"{REFERENCE}_km_vazio_base_por_corrida": base_ride,
            f"{REFERENCE}_incremento_km_por_corrida": inc_ride,
            f"{REFERENCE}_var_pct_simulada": 100 * inc_ride / base_ride,
            f"{REFERENCE}_var_pct_com_base_reescalada": 100 * inc_ride / (base_ride / scale),
        }
    write(OUT / "tempo_quantis.csv", quant)
    write(OUT / "tempo_acumulada.csv", curve)
    write(OUT / "atendimento_hora.csv", hours)
    write(OUT / "razao_distancia.csv", ratios)
    (OUT / "resumo.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"ok: {sum(v['dias_com_assinatura_conferida'] for v in summary['periodos'].values())} dias conferidos; saídas em {OUT}")


if __name__ == "__main__":
    main()
