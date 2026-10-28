"""Fase 3: oráculo de demanda e escada de ruído (viola o corte D+1; limite superior do que a previsão poderia dar).

Execução local e somente agregada (autorização do proponente, pré-registro D3). Linhas por semente ficam em
`reports/runs/tcc_v2/` (ignorado); versionam-se apenas agregados por dia ou mais.
"""

from __future__ import annotations

import time
from pathlib import Path

from . import analise
from . import avaliacao as av
from .fase1 import write_csv

LADDER_TARGETS = (0.1, 0.3, 0.5, 0.7, 0.9)
WINDOW = "04-11"
_STUDY = None


def _init(raw: str) -> None:
    global _STUDY
    from tcc_frota.algoritmos.bateria import build_study

    _STUDY = build_study(Path(raw))


def _task(args) -> list[dict]:
    from tcc_frota.algoritmos.bateria import load_frozen

    period, day, group, mode, mix_w, names = args
    frozen = load_frozen()
    specs = [s for s in av.phase3_specs() if s.name in names]
    rows = av.evaluate_day3(
        _STUDY,
        period,
        day,
        WINDOW,
        frozen.sims[period],
        specs,
        frozen.model,
        demand_mode=mode,
        mix_w=mix_w,
        label=group,
        include_baseline=(group == "base"),
    )
    return rows


def mixing_weights(study, sims_model) -> tuple[dict, list[dict]]:
    """w por (período, nível) e tabela de WAPE realizado (calibrado com a verdade de D+1: parte do desenho oráculo, D5)."""

    from tcc_frota.v2 import experiment as ex
    from tcc_frota.v2 import forecast as fc

    weights, table = {}, []
    for period, p in ex.PERIODS.items():
        window = ex.WINDOWS[WINDOW]
        days = []
        for d in p.test:
            reqs, drivers = study.world(period, d, window)
            inputs, _ = study.plan_inputs(
                d, window, av.REGIME, drivers, sims_model[period].road_factor, sims_model["model"], fc.ForecastConfig()
            )
            y, outside = av.real_demand(study, d, window, inputs.zones)
            days.append((y, outside, inputs.demand))
        err_g_in = sum(sum(abs(g.get(k, 0.0) - y.get(k, 0.0)) for k in set(g) | set(y)) for y, _, g in days)
        out_tot = sum(o for _, o, _ in days)
        y_tot = sum(sum(y.values()) for y, _, _ in days) + out_tot
        wape_g = (err_g_in + out_tot) / y_tot
        for target in LADDER_TARGETS:
            w = av.mixing_weight(target, err_g_in, y_tot, out_tot)
            err = sum(av.wape_parts(av.mix_demand(y, g, w), y, o)[0] for y, o, g in days)
            weights[(period, target)] = w
            table.append(
                {
                    "periodo": period,
                    "wape_alvo": target,
                    "w": round(w, 6),
                    "wape_realizado": err / y_tot,
                    "wape_modelo_real": wape_g,
                    "demanda_fora_das_zonas_pct": 100 * out_tot / y_tot,
                    "observacao": "nível igual ao modelo real (w=1)"
                    if w >= 1
                    else ("limite inferior pela demanda fora das zonas" if w <= 0 else ""),
                }
            )
        table.append(
            {
                "periodo": period,
                "wape_alvo": 0.0,
                "w": 0.0,
                "wape_realizado": out_tot / y_tot,
                "wape_modelo_real": wape_g,
                "demanda_fora_das_zonas_pct": 100 * out_tot / y_tot,
                "observacao": "oráculo (erro só pela demanda fora das zonas)",
            }
        )
    return weights, table


def run(raw: Path, out: Path, runs: Path, workers: int = 3, reps: int = 10000, echo=print) -> dict:
    from multiprocessing import get_context

    from tcc_frota.algoritmos.bateria import build_study, load_frozen
    from tcc_frota.v2 import experiment as ex

    frozen = load_frozen()
    study = build_study(raw)
    weights, wape_table = mixing_weights(study, {**{k: v for k, v in frozen.sims.items()}, "model": frozen.model})
    write_csv(out / "fase3_wape_escada.csv", wape_table)
    all_names = [s.name for s in av.phase3_specs()]
    tasks = []
    for period, p in ex.PERIODS.items():
        for d in p.test:
            tasks.append((period, d, "base", "previsto", None, []))
            tasks.append((period, d, "previsto", "previsto", None, all_names))
            tasks.append((period, d, "oraculo", "oraculo", None, all_names))
            for target in LADDER_TARGETS:
                w = weights[(period, target)]
                if 0.0 < w < 1.0:  # w=1 repete o modelo real; w=0 repete o oráculo
                    tasks.append((period, d, f"mistura_wape{target:g}", "mistura", w, list(av.DEMAND_DRIVEN)))
    echo(f"{len(tasks)} tarefas, {workers} processos")
    started = time.time()
    rows: list[dict] = []
    with get_context("spawn").Pool(workers, initializer=_init, initargs=(str(raw),)) as pool:
        for i, part in enumerate(pool.imap_unordered(_task, tasks), 1):
            rows += part
            if i % 10 == 0 or i == len(tasks):
                echo(f"  {i}/{len(tasks)} ({time.time() - started:.0f} s)")
    runs.mkdir(parents=True, exist_ok=True)
    write_csv(runs / "fase3_linhas_por_semente.csv", rows)
    return finish(rows, out, reps, echo)


def finish(rows: list[dict], out: Path, reps: int = 10000, echo=print) -> dict:
    days = analise.average_seeds(rows)
    write_csv(out / "fase3_dias.csv", [{k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()} for r in days])
    groups = sorted({r["grupo"] for r in days} - {"base"})
    summary = {}
    for field, tag in (("empty_km", "v1"), ("empty_km_sim", "corrigida")):
        for fam, label in (("oraculo", "F3"), ("previsto", "F3_ref_previsto")):
            pairs = {k: v for k, v in analise.build_pairs(days, field, "base").items() if k[2] == fam}
            res = analise.analyze(pairs, reps, label)
            write_csv(out / f"fase3_{fam}_{tag}_linhas.csv", res["linhas"])
            write_csv(out / f"fase3_{fam}_{tag}_nb.csv", res["nb"])
            write_csv(out / f"fase3_{fam}_{tag}_mde.csv", res["mde"])
            summary[f"{fam}_{tag}"] = {
                d: sum(1 for x in res["linhas"] if x["decisao"] == d) for d in ("reducao", "aumento", "inconclusivo")
            }
        # escada: cada nível é uma família exploratória própria
        ladder = [g for g in groups if g.startswith("mistura")]
        lad_lines, lad_nb = [], []
        for g in ladder:
            pairs = {k: v for k, v in analise.build_pairs(days, field, "base").items() if k[2] == g}
            res = analise.analyze(pairs, reps, f"escada_{g}")
            lad_lines += res["linhas"]
            lad_nb += res["nb"]
        write_csv(out / f"fase3_escada_{tag}_linhas.csv", lad_lines)
        write_csv(out / f"fase3_escada_{tag}_nb.csv", lad_nb)
        # oráculo contra a previsão (mesmo algoritmo): diferença direta
        by = {(r["periodo"], r["data"], r["cenario"]): r for r in days if r["grupo"] == "previsto"}
        synth = []
        for r in days:
            if r["grupo"] != "oraculo":
                continue
            ref = by.get((r["periodo"], r["data"], r["cenario"]))
            if ref:
                tag_alg = f"{r['janela']}|{r['cenario']}"  # um baseline (a previsão) por algoritmo
                synth.append({**ref, "cenario": analise.BASE, "grupo": "ref", "familia": "nenhum", "janela": tag_alg})
                synth.append({**r, "grupo": "oraculo_vs_previsto", "janela": tag_alg})
        res = analise.analyze(analise.build_pairs(synth, field), reps, "exploratoria_oraculo_vs_previsto")
        write_csv(out / f"fase3_oraculo_vs_previsto_{tag}_linhas.csv", res["linhas"])
    return summary
