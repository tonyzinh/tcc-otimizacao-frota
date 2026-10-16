"""`tcc-frota final-run`: dos extratos brutos às tabelas finais, de forma reprodutível.

Saída individual (pedido a pedido, dias) fica em `<out>/<run_id>/`, ignorado pelo Git; apenas
agregados sem dados individuais são copiados para `reports/tcc_final/` quando `--publish`.
"""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import time
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median

from tcc_frota.v2 import experiment as ex
from tcc_frota.v2 import forecast as fc
from tcc_frota.v2 import rules
from tcc_frota.v2.gold import build_gold
from tcc_frota.v2.raw import input_hashes, prepare_raw
from tcc_frota.v2.silver import build_silver
from tcc_frota.v2.sim import reta_km, simulate
from tcc_frota.v2.stats import compare

SEED = 20261016
BOOTSTRAP_REPS = 2000


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with path.open("w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})


def code_version() -> dict:
    root = Path(__file__).resolve().parents[3]
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "src"], cwd=root, capture_output=True, text=True).stdout.strip())
    except OSError:
        head, dirty = "desconhecido", True
    return {"git_head": head, "src_com_alteracoes_nao_commitadas": dirty}


# ---------------------------------------------------------------- descritivos
def outcome_table(silver) -> list[dict]:
    counts: Counter = Counter()
    for r in silver.solicitacoes:
        counts[(r["tag_lote"], r["status"], r["fl_imediata"])] += 1
    out = []
    for status in sorted({k[1] for k in counts}):
        t = rules.treatment(status)
        row = {"status": status, "grupo_desfecho": t.grupo, "conta_como_demanda": t.demanda, "aceito": t.aceito,
               "tratamento": t.descricao}
        for tag in ("historico56", "mar2026", "historico56_set", "set2026"):
            row[f"{tag}_imediatas"] = counts[(tag, status, True)]
            row[f"{tag}_agendadas"] = counts[(tag, status, False)]
        out.append(row)
    return out


HOUR_BANDS = {"00-03": range(0, 4), "04-07": range(4, 8), "08-16": range(8, 17), "17-19": range(17, 20), "20-23": range(20, 24)}


def hour_band_analysis(gold, months: dict[str, tuple[date, date]]) -> list[dict]:
    """Não atendimento por faixa e distância ao motorista livre mais próximo na última foto (≤ 10 min)."""
    free_by_snap: dict[datetime, list[tuple[float, float]]] = defaultdict(list)
    for p in gold.frota_snapshot:
        if p["estado"] == 1 and p["fl_coordenada_valida"]:
            free_by_snap[p["ts_snapshot"]].append((p["lat"], p["lon"]))
    import bisect

    times = sorted(free_by_snap)
    out = []
    for label, (first, last) in months.items():
        groups: dict[tuple[str, bool], list] = defaultdict(list)
        for r in gold.replay_pedidos:
            if not (first <= r["data_local"] <= last):
                continue
            band = next(b for b, hs in HOUR_BANDS.items() if r["hora_local"] in hs)
            i = bisect.bisect_right(times, r["ts_pedido"]) - 1
            dist = None
            if i >= 0 and (r["ts_pedido"] - times[i]).total_seconds() <= 600:
                cands = free_by_snap[times[i]]
                if cands:
                    dist = min(reta_km(r["lat_origem"], r["lon_origem"], la, lo) for la, lo in cands)
            groups[(band, r["fl_aceito"])].append(dist)
        for band in HOUR_BANDS:
            acc, non = groups[(band, True)], groups[(band, False)]
            total = len(acc) + len(non)
            row = {"periodo": label, "faixa": band, "pedidos": total,
                   "nao_aceitos_pct": 100 * len(non) / total if total else float("nan")}
            for name, values in (("aceitos", acc), ("nao_aceitos", non)):
                known = [v for v in values if v is not None]
                row[f"{name}_dist_livre_mediana_km"] = median(known) if known else float("nan")
                row[f"{name}_livre_ate_2km_pct"] = 100 * sum(v <= 2 for v in known) / len(known) if known else float("nan")
                row[f"{name}_sem_livre_na_foto_pct"] = 100 * sum(v is None for v in values) / len(values) if values else float("nan")
            out.append(row)
    return out


def demand_by_hour(gold, months) -> list[dict]:
    out = []
    for label, (first, last) in months.items():
        c: Counter = Counter()
        a: Counter = Counter()
        days = {r["data_local"] for r in gold.replay_pedidos if first <= r["data_local"] <= last}
        for r in gold.replay_pedidos:
            if first <= r["data_local"] <= last:
                c[r["hora_local"]] += 1
                a[r["hora_local"]] += r["fl_aceito"]
        for h in range(24):
            out.append({"periodo": label, "hora": h, "pedidos_por_dia": c[h] / max(1, len(days)),
                        "aceitos_por_dia": a[h] / max(1, len(days)), "aceite_pct": 100 * a[h] / c[h] if c[h] else float("nan")})
    return out


def fleet_descriptives(gold, silver, months) -> list[dict]:
    out = []
    for label, (first, last) in months.items():
        per_day: dict[date, set] = defaultdict(set)
        per_hour: dict[tuple[date, int], set] = defaultdict(set)
        for p in gold.frota_snapshot:
            d = p["ts_snapshot"].date()
            if first <= d <= last and p["estado"] in rules.WORKING_STATES:
                per_day[d].add(p["motorista_pseud"])
                per_hour[(d, p["ts_snapshot"].hour)].add(p["motorista_pseud"])
        starts = Counter()
        for s in gold.frota_sessoes:
            d = s["ts_inicio"].date()
            if first <= d <= last:
                starts[s["ts_inicio"].hour] += 1
        n_days = max(1, len(per_day))
        drivers_month = set().union(*per_day.values()) if per_day else set()
        dorm = [x["km_reta_dormida"] for x in silver.dormida if x["km_reta_dormida"] is not None and first <= x["data_local"] <= last]
        out.append({"periodo": label, "medida": "motoristas_distintos_por_dia_media", "valor": mean(len(v) for v in per_day.values())})
        out.append({"periodo": label, "medida": "motoristas_distintos_no_mes", "valor": len(drivers_month)})
        for h in range(24):
            vals = [len(per_hour.get((d, h), ())) for d in per_day]
            out.append({"periodo": label, "medida": f"motoristas_trabalhando_hora_{h:02d}_media", "valor": mean(vals) if vals else 0})
            out.append({"periodo": label, "medida": f"sessoes_iniciadas_hora_{h:02d}_por_dia", "valor": starts[h] / n_days})
        if dorm:
            dorm.sort()
            out.append({"periodo": label, "medida": "dormida_km_reta_n", "valor": len(dorm)})
            out.append({"periodo": label, "medida": "dormida_km_reta_mediana", "valor": median(dorm)})
            out.append({"periodo": label, "medida": "dormida_km_reta_p90", "valor": dorm[int(0.9 * (len(dorm) - 1))]})
    return out


# ---------------------------------------------------------------- previsão
def forecast_evaluation(study, echo) -> tuple[list[dict], list[dict], str]:
    rows = []
    days = {"mar2026": [date(2026, 3, d) for d in range(2, 32)], "set2026": [date(2026, 9, d) for d in range(2, 31)]}
    configs = {"padrao_56d_sem_carnaval": fc.ForecastConfig()}
    for model in fc.MODELS:
        for period, targets in days.items():
            for wkey, window in ex.WINDOWS.items():
                for t in targets:
                    pred = fc.predict(model, t, study.history, range(*window), configs["padrao_56d_sem_carnaval"])
                    if not pred:
                        continue
                    e = fc.errors(pred, t, study.history, range(*window))
                    stage = "calibracao" if t in ex.PERIODS[period].calibration else "teste"
                    rows.append({"modelo": model, "config": "padrao_56d_sem_carnaval", "periodo": period, "janela": wkey,
                                 "data": t.isoformat(), "etapa": stage, **e})
    # escolha: só calibração de março, janela principal, WAPE por zona-hora
    def wape(model, stage, period="mar2026", window=ex.MAIN_WINDOW):
        sel = [r for r in rows if r["modelo"] == model and r["etapa"] == stage and r["periodo"] == period and r["janela"] == window]
        return mean(r["wape_zona_hora"] for r in sel) if sel else float("inf")
    scores = {m: wape(m, "calibracao") for m in fc.MODELS}
    best = min(scores.values())
    order = ["media_dia_semana", "naive_sazonal", "poisson"]   # do mais simples ao mais complexo
    chosen = next(m for m in order if scores[m] <= best * (1 + ex.FORECAST_MARGIN))
    echo(f"previsão: WAPE calibração {scores}; escolhido {chosen}")
    summary = []
    for model in fc.MODELS:
        for period in days:
            for wkey in ex.WINDOWS:
                for stage in ("calibracao", "teste"):
                    sel = [r for r in rows if r["modelo"] == model and r["periodo"] == period and r["janela"] == wkey and r["etapa"] == stage]
                    if not sel:
                        continue
                    obs = sum(r["observado_janela"] for r in sel)
                    summary.append({"modelo": model, "periodo": period, "janela": wkey, "etapa": stage, "dias": len(sel),
                                    "wape_zona_hora_medio": mean(r["wape_zona_hora"] for r in sel),
                                    "mae_zona_hora_medio": mean(r["mae_zona_hora"] for r in sel),
                                    "desvio_poisson_medio": mean(r["desvio_poisson_medio"] for r in sel),
                                    "wape_total_janela": sum(r["erro_abs_total_janela"] for r in sel) / obs if obs else float("nan"),
                                    "observado_medio_dia": obs / len(sel),
                                    "previsto_medio_dia": sum(r["previsto_janela"] for r in sel) / len(sel),
                                    "escolhido": model == chosen})
    # sensibilidade da janela de treino e do Carnaval para o modelo escolhido
    variants = {"28d": fc.ForecastConfig(lookback_days=28), "84d_limitado_ao_disponivel": fc.ForecastConfig(lookback_days=84),
                "56d_com_carnaval": fc.ForecastConfig(excluded_dates=())}
    for name, cfg in variants.items():
        for period, targets in days.items():
            sel = []
            for t in targets:
                if t not in ex.PERIODS[period].test:
                    continue
                pred = fc.predict(chosen, t, study.history, range(*ex.WINDOWS[ex.MAIN_WINDOW]), cfg)
                if pred:
                    sel.append(fc.errors(pred, t, study.history, range(*ex.WINDOWS[ex.MAIN_WINDOW])))
            if sel:
                obs = sum(e["observado_janela"] for e in sel)
                summary.append({"modelo": chosen, "periodo": period, "janela": ex.MAIN_WINDOW, "etapa": f"teste_{name}",
                                "dias": len(sel), "wape_zona_hora_medio": mean(e["wape_zona_hora"] for e in sel),
                                "mae_zona_hora_medio": mean(e["mae_zona_hora"] for e in sel),
                                "desvio_poisson_medio": mean(e["desvio_poisson_medio"] for e in sel),
                                "wape_total_janela": sum(e["erro_abs_total_janela"] for e in sel) / obs if obs else float("nan"),
                                "observado_medio_dia": obs / len(sel),
                                "previsto_medio_dia": sum(e["previsto_janela"] for e in sel) / len(sel), "escolhido": False})
    return rows, summary, chosen


# ---------------------------------------------------------------- seleção de parâmetros
def select_policies(study, sim, model, echo) -> tuple[dict, list[dict]]:
    period = ex.PERIODS[ex.SELECTION_PERIOD]
    specs = []
    for rho in ex.RHO_GRID:
        for dmax in ex.DMAX_GRID:
            for alpha in ex.ALPHA_GRID:
                specs.append((f"g|{rho}|{dmax}|{alpha}", "guloso_marginal", {"alpha": alpha, "rho_km": rho, "max_km": dmax}))
    for theta in ex.THETA_GRID:
        for dmax in ex.THRESHOLD_DMAX:
            specs.append((f"t|{theta}|{dmax}", "regra_limiar", {"theta": theta, "rho_km": 1.5, "max_km": dmax}))
    for dmax in ex.PROP_DMAX:
        specs.append((f"p|{dmax}", "proporcional", {"max_km": dmax}))
    rows = []
    for day in period.calibration:
        rows += ex.run_day(study, period.name, day, ex.MAIN_WINDOW, ex.MAIN_REGIME, sim, specs, model, fc.ForecastConfig())
    table = []
    for name, algorithm, params in specs:
        days = ex.pair_days(rows, name)
        score, dr, dk = ex.efficiency(days)
        table.append({"cenario": name, "algoritmo": algorithm, **params, "delta_corridas": dr, "delta_km_vazio": dk,
                      "corridas_por_km_extra": score if score < 1e8 else float("inf"),
                      "movimentos_executados": sum(d["p"]["moves_executed"] for d in days),
                      "movimentos_planejados": sum(d["p"]["moves_planned"] for d in days)})
    # guloso: (ρ, dmax) com maior eficiência média sobre a grade de α
    best_g = None
    for rho in ex.RHO_GRID:
        for dmax in ex.DMAX_GRID:
            sel = [t for t in table if t["algoritmo"] == "guloso_marginal" and t["rho_km"] == rho and t["max_km"] == dmax]
            vals = [min(t["corridas_por_km_extra"], 1e3) if t["delta_corridas"] > 0 else min(0.0, t["delta_corridas"]) for t in sel]
            key = (mean(vals), -rho, -dmax)
            if best_g is None or key > best_g[0]:
                best_g = (key, {"rho_km": rho, "max_km": dmax})
    def best_of(alg):
        sel = [t for t in table if t["algoritmo"] == alg]
        return max(sel, key=lambda t: ((min(t["corridas_por_km_extra"], 1e3) if t["delta_corridas"] > 0 else min(0.0, t["delta_corridas"])),
                                       -t.get("max_km", 0)))
    bt, bp = best_of("regra_limiar"), best_of("proporcional")
    selection = {"guloso_marginal": best_g[1],
                 "regra_limiar": {"theta": bt["theta"], "rho_km": bt["rho_km"], "max_km": bt["max_km"]},
                 "proporcional": {"max_km": bp["max_km"]}}
    for t in table:
        t["selecionado"] = (
            (t["algoritmo"] == "guloso_marginal" and t["rho_km"] == selection["guloso_marginal"]["rho_km"]
             and t["max_km"] == selection["guloso_marginal"]["max_km"])
            or (t["algoritmo"] == "regra_limiar" and t["theta"] == bt["theta"] and t["max_km"] == bt["max_km"])
            or (t["algoritmo"] == "proporcional" and t["max_km"] == bp["max_km"]))
    echo(f"seleção (calibração de março): {selection}")
    return selection, table


# ---------------------------------------------------------------- execução completa
def final_run(raw: Path, out: Path, *, publish: Path | None = None, echo=print) -> dict:
    rules_salt = rules.load_salt()
    started = time.time()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    batches = prepare_raw(raw, echo=echo)
    hashes = input_hashes(batches)
    echo("construindo Silver e Gold locais...")
    silver = build_silver(batches, rules_salt)
    gold = build_gold(silver)
    study = ex.Study(silver, gold)
    months = {"mar2026": (date(2026, 3, 1), date(2026, 3, 31)), "set2026": (date(2026, 9, 1), date(2026, 9, 30))}

    tables: dict[str, list[dict]] = {}
    tables["tab01_desfechos_tratamento"] = outcome_table(silver)
    tables["tab02_qualidade"] = gold.qualidade
    tables["tab03_demanda_por_hora"] = demand_by_hour(gold, months)
    tables["tab04_faixas_nao_atendimento"] = hour_band_analysis(gold, months)
    tables["tab05_frota_descritivo"] = fleet_descriptives(gold, silver, months)
    tables["tab06_calibracao_gold"] = gold.calibracao

    forecast_rows, forecast_summary, model = forecast_evaluation(study, echo)
    tables["tab07_erros_previsao"] = forecast_summary
    tables["tab18_previsto_observado_diario"] = [
        {"modelo": r["modelo"], "periodo": r["periodo"], "janela": r["janela"], "data": r["data"], "etapa": r["etapa"],
         "observado": r["observado_janela"], "previsto": r["previsto_janela"]} for r in forecast_rows]
    zone_rows: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for row in gold.demanda_zona_hora:
        for label, (first, last) in months.items():
            if first <= row["data_local"] <= last and 4 <= row["hora_local"] < 11 and row["h3_r7"]:
                zone_rows[(label, row["h3_r7"])]["pedidos"] += row["qtd_demanda"]
                zone_rows[(label, row["h3_r7"])]["nao_atendidas"] += row["qtd_demanda"] - row["qtd_aceitas"]
    tables["tab17_nao_atendidas_por_zona"] = [{"periodo": k[0], "h3_r7": k[1], **dict(v)} for k, v in sorted(zone_rows.items())]

    measured, sims, calib_grid = {}, {}, []
    for name, period in ex.PERIODS.items():
        measured[name] = study.measured_parameters(period.calibration)
        study.trip_model[name] = (measured[name]["fator_rua_reta_viagem"], measured[name]["velocidade_viagem_kmh"])
        sims[name], grid = ex.calibrate_simulator(study, period, measured[name], echo)
        calib_grid += grid
    tables["tab08_calibracao_simulador"] = calib_grid
    fit = []
    for name, period in ex.PERIODS.items():
        for stage, days in (("calibracao", period.calibration), ("teste", period.test)):
            for wkey, window in ex.WINDOWS.items():
                obs = study.observed(days, window)
                served = n = 0
                waits = []
                for d in days:
                    reqs, drivers = study.world(name, d, window)
                    r = simulate(reqs, drivers, sims[name], (window[0] * 3600.0, window[1] * 3600.0))
                    served += r.served
                    n += r.n_requests
                    waits += r.wait_s
                fit.append({"periodo": name, "etapa": stage, "janela": wkey, "pedidos": n,
                            "atendimento_sim_pct": 100 * served / max(1, n), "aceite_obs_pct": 100 * obs["taxa_aceite"],
                            "tempo_ate_passageiro_mediano_sim_s": median(waits) if waits else float("nan"),
                            "busca_mediana_obs_s": obs["busca_mediana_s"]})
    tables["tab09_ajuste_baseline"] = fit

    selection, selection_table = select_policies(study, sims[ex.SELECTION_PERIOD], model, echo)
    tables["tab10_selecao_parametros_calibracao"] = selection_table

    echo("avaliando dias de teste...")
    specs = ex.policy_specs(selection)
    daily: list[dict] = []
    for name, period in ex.PERIODS.items():
        for day in period.test:
            for wkey in ex.WINDOWS:
                for regime in ("A", "B", "C"):
                    daily += ex.run_day(study, name, day, wkey, regime, sims[name], specs, model, fc.ForecastConfig())
    main = []
    for name in ex.PERIODS:
        for wkey in ex.WINDOWS:
            for regime in ("A", "B", "C"):
                for scen, alg, params in specs:
                    days = ex.pair_days(daily, scen, periodo=name, janela=wkey, regime=regime)
                    if not days:
                        continue
                    diag = [d["p"].get("diag_frota", {}) for d in days]
                    row = {"periodo": name, "janela": wkey, "regime": regime, "cenario": scen, "algoritmo": alg,
                           "parametros": json.dumps(params), **compare(days, BOOTSTRAP_REPS, SEED),
                           "tempo_plano_medio_s": mean(d["p"]["plan_seconds"] for d in days),
                           "precisao_escala_pct": 100 * sum(x.get("acertos", 0) for x in diag) / max(1, sum(x.get("previstos", 0) for x in diag)),
                           "revocacao_escala_pct": 100 * sum(x.get("acertos", 0) for x in diag) / max(1, sum(x.get("reais", 0) for x in diag)),
                           "ganho_planejado_corridas": sum(d["p"]["planned_gain"] for d in days),
                           "km_planejado": sum(d["p"]["planned_km"] for d in days)}
                    main.append(row)
    tables["tab11_principal"] = main

    # efeito por faixa horária (janela 04-11, regime B, guloso intermediário)
    inter = f"guloso_marginal_a{ex.NAMED_ALPHA['intermediaria']:g}"
    by_hour = []
    for name in ex.PERIODS:
        for scen in ("proporcional", inter, "regra_limiar"):
            days = ex.pair_days(daily, scen, periodo=name, janela=ex.MAIN_WINDOW, regime=ex.MAIN_REGIME)
            for h in range(*ex.WINDOWS[ex.MAIN_WINDOW]):
                b = sum(d["b"]["served_by_hour"].get(h, 0) for d in days)
                p = sum(d["p"]["served_by_hour"].get(h, 0) for d in days)
                n = sum(d["b"]["requests_by_hour"].get(h, 0) for d in days)
                kb = sum(d["b"]["pickup_by_hour"].get(h, 0.0) for d in days)
                kp = sum(d["p"]["pickup_by_hour"].get(h, 0.0) for d in days)
                by_hour.append({"periodo": name, "cenario": scen, "hora": h, "pedidos": n, "atendidas_base": b,
                                "atendidas_prop": p, "corridas_extras": p - b,
                                "km_busca_por_corrida_base": kb / b if b else float("nan"),
                                "km_busca_por_corrida_prop": kp / p if p else float("nan")})
    tables["tab12_por_faixa_horaria"] = by_hour

    # sensibilidades (uma variável por vez): março, teste, 04-11, regime B, guloso intermediário
    sens = []
    base_sim = sims[ex.SELECTION_PERIOD]
    g = selection["guloso_marginal"]
    inter_spec = [(inter, "guloso_marginal", {"alpha": ex.NAMED_ALPHA["intermediaria"], **g})]
    variants = [
        ("fator_rua_reta_1.2", {"sim": replace(base_sim, road_factor=1.2)}),
        ("fator_rua_reta_1.6", {"sim": replace(base_sim, road_factor=1.6)}),
        ("velocidade_-25pct", {"sim": replace(base_sim, speed_kmh=base_sim.speed_kmh * 0.75)}),
        ("velocidade_+25pct", {"sim": replace(base_sim, speed_kmh=base_sim.speed_kmh * 1.25)}),
        ("raio_-1km", {"sim": replace(base_sim, radius_km=max(1.0, base_sim.radius_km - 1))}),
        ("raio_+1km", {"sim": replace(base_sim, radius_km=base_sim.radius_km + 1)}),
        ("paciencia_x0.5", {"sim": replace(base_sim, patience_s=base_sim.patience_s * 0.5)}),
        ("paciencia_x2", {"sim": replace(base_sim, patience_s=base_sim.patience_s * 2)}),
        ("cancelamento_pos_aceite", {"sim": replace(base_sim, post_accept_cancel=True)}),
        ("limite_distancia_3km", {"spec": [(inter, "guloso_marginal", {"alpha": ex.NAMED_ALPHA["intermediaria"], "rho_km": g["rho_km"], "max_km": 3.0})]}),
        ("limite_distancia_10km", {"spec": [(inter, "guloso_marginal", {"alpha": ex.NAMED_ALPHA["intermediaria"], "rho_km": g["rho_km"], "max_km": 10.0})]}),
        ("treino_28d", {"fconfig": fc.ForecastConfig(lookback_days=28)}),
        ("treino_84d_limitado", {"fconfig": fc.ForecastConfig(lookback_days=84)}),
        ("treino_com_carnaval", {"fconfig": fc.ForecastConfig(excluded_dates=())}),
        ("previsao_poisson", {"model": "poisson"}),
        ("regime_A_previsto", {"regime": "A"}),
        ("regime_C_oraculo", {"regime": "C"}),
        ("B_execucao_inicio_turno", {"move_mode": "inicio_turno"}),
        ("B_posicao_20h", {"position_cut_hour": 20}),
    ]
    period = ex.PERIODS[ex.SELECTION_PERIOD]
    for label, v in [("referencia", {})] + variants:
        rows = []
        for day in period.test:
            rows += ex.run_day(study, period.name, day, ex.MAIN_WINDOW, v.get("regime", ex.MAIN_REGIME), v.get("sim", base_sim),
                               v.get("spec", inter_spec), v.get("model", model), v.get("fconfig", fc.ForecastConfig()),
                               move_mode=v.get("move_mode"), position_cut_hour=v.get("position_cut_hour"))
        days = ex.pair_days(rows, inter)
        sens.append({"variacao": label, **compare(days, BOOTSTRAP_REPS, SEED)})
    tables["tab13_sensibilidade"] = sens

    # ponto de equilíbrio: KM vazio incremental por corrida extra (e) → margem mínima = e × custo/km
    breakeven = []
    for r in main:
        if r["janela"] != ex.MAIN_WINDOW:
            continue
        e = r["km_vazio_incremental_por_corrida_extra"]
        breakeven.append({k: r[k] for k in ("periodo", "regime", "cenario")} | {
            "corridas_extras_por_dia": r["corridas_extras_por_dia"],
            "km_vazio_incremental_por_corrida_extra": e,
            "ic_inf": r["km_vazio_incremental_por_corrida_extra_ic_inf"],
            "ic_sup": r["km_vazio_incremental_por_corrida_extra_ic_sup"],
            "regra": "vantajoso se margem por corrida extra > e x custo marginal por km (valores a fornecer)"})
    tables["tab14_ponto_equilibrio"] = breakeven

    ladder = [r for r in main if r["janela"] == ex.MAIN_WINDOW and r["cenario"] in ("proporcional", inter, "regra_limiar")]
    tables["tab15_escada_informacao"] = [{k: r[k] for k in (
        "periodo", "regime", "cenario", "taxa_execucao_pct", "precisao_escala_pct", "revocacao_escala_pct",
        "corridas_atendidas_var_pct", "corridas_atendidas_var_pct_ic_inf", "corridas_atendidas_var_pct_ic_sup",
        "km_vazio_por_corrida_var_pct", "km_vazio_por_corrida_var_pct_ic_inf", "km_vazio_por_corrida_var_pct_ic_sup")}
        for r in ladder]

    pareto = [r for r in main if r["algoritmo"] in ("guloso_marginal", "proporcional", "regra_limiar") and r["janela"] == ex.MAIN_WINDOW]
    tables["tab16_fronteira_pareto"] = [{k: r[k] for k in (
        "periodo", "regime", "cenario", "parametros", "corridas_atendidas_var_pct", "corridas_atendidas_var_pct_ic_inf",
        "corridas_atendidas_var_pct_ic_sup", "km_vazio_por_corrida_var_pct", "km_vazio_por_corrida_var_pct_ic_inf",
        "km_vazio_por_corrida_var_pct_ic_sup", "km_reposicionamento_por_dia", "km_vazio_incremental_por_corrida_extra")}
        for r in pareto]

    for name, rows in tables.items():
        write_csv(run_dir / f"{name}.csv", rows)
    write_csv(run_dir / "individual" / "dias_cenarios.csv",
              [{k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in r.items()} for r in daily])
    write_csv(run_dir / "individual" / "previsao_por_dia.csv", forecast_rows)

    result = {
        "run_id": run_id, "gerado_em": datetime.now(timezone.utc).isoformat(), "duracao_s": round(time.time() - started, 1),
        "versao_codigo": code_version(), "semente_bootstrap": SEED, "reamostragens": BOOTSTRAP_REPS,
        "hashes_entrada_sha256": hashes,
        "contagens_ingeridas": dict(silver.ingested), "filtros_universo": dict(gold.filtros),
        "configuracao": {
            "periodos": {k: {"calibracao": [d.isoformat() for d in p.calibration], "teste": [d.isoformat() for d in p.test]}
                         for k, p in ex.PERIODS.items()},
            "janelas": ex.WINDOWS, "janela_principal": ex.MAIN_WINDOW, "regime_principal": ex.MAIN_REGIME,
            "grades": {"raio": ex.RADIUS_GRID, "paciencia": ex.PATIENCE_GRID, "alpha": ex.ALPHA_GRID, "rho": ex.RHO_GRID,
                       "dmax": ex.DMAX_GRID, "theta": ex.THETA_GRID, "dmax_limiar": ex.THRESHOLD_DMAX,
                       "dmax_proporcional": ex.PROP_DMAX},
            "alpha_nomeados": ex.NAMED_ALPHA, "modelo_previsao": model, "previsao": asdict(fc.ForecastConfig()),
            "parametros_medidos": measured, "simulador": {k: asdict(v) for k, v in sims.items()},
            "selecao": selection,
        },
        "tabelas": {k: f"{k}.csv" for k in tables},
        "principal": main,
        "sensibilidade": sens,
    }
    (run_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    try:
        from tcc_frota.v2.figures import make_figures

        result["figuras"] = make_figures(run_dir, run_dir / "figuras")
    except ImportError as exc:   # matplotlib/h3 são extras opcionais
        result["figuras"] = f"não geradas: {exc}"
    (run_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    if publish is not None:
        publish.mkdir(parents=True, exist_ok=True)
        for name in tables:
            shutil.copy2(run_dir / f"{name}.csv", publish / f"{name}.csv")
        if (run_dir / "figuras").is_dir():
            shutil.copytree(run_dir / "figuras", publish / "figuras", dirs_exist_ok=True)
        (publish / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    echo(f"final-run concluído em {time.time() - started:.0f} s: {run_dir}")
    return result
