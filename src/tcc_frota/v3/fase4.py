"""Fase 4: baselines realistas B0–B4, recuperabilidade ρ e conformidade (local, só agregados; pré-registro D3, D10, D11)."""
from __future__ import annotations

import time
from pathlib import Path

from . import analise
from . import avaliacao as av
from . import avaliacao4 as a4
from .fase1 import write_csv

_STUDY = None


def _init(raw: str) -> None:
    global _STUDY
    from tcc_frota.algoritmos.bateria import build_study
    _STUDY = build_study(Path(raw))


def _task(args) -> list[dict]:
    from tcc_frota.algoritmos.bateria import load_frozen
    world, period, day = args
    frozen = load_frozen()
    specs = av.phase3_specs()
    if world == "origem":
        return a4.evaluate_day4(_STUDY, period, day, frozen.sims[period], specs, frozen.model, world="origem")
    return a4.evaluate_day4(_STUDY, period, day, frozen.sims[period], specs, frozen.model, world="login", rhos=(1.0,), confs=(1.0,))


def run(raw: Path, out: Path, runs: Path, workers: int = 3, reps: int = 10000, echo=print) -> dict:
    from multiprocessing import get_context
    from tcc_frota.v2 import experiment as ex

    tasks = [(w, p, d) for w in ("origem", "login") for p, per in ex.PERIODS.items() for d in per.test]
    echo(f"{len(tasks)} tarefas, {workers} processos")
    started = time.time()
    rows: list[dict] = []
    with get_context("spawn").Pool(workers, initializer=_init, initargs=(str(raw),)) as pool:
        for i, part in enumerate(pool.imap_unordered(_task, tasks), 1):
            rows += part
            if i % 5 == 0 or i == len(tasks):
                echo(f"  {i}/{len(tasks)} ({time.time() - started:.0f} s)")
    runs.mkdir(parents=True, exist_ok=True)
    write_csv(runs / "fase4_linhas_por_semente.csv", rows)
    return finish(rows, out, reps, echo)


PLANS = tuple(av.ORACLE_ALGORITHMS)


def _is_plan(name: str) -> bool:
    return name in PLANS


def finish(rows: list[dict], out: Path, reps: int = 10000, echo=print) -> dict:
    days = analise.average_seeds(rows)
    write_csv(out / "fase4_dias.csv", [{k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()} for r in days])
    summary = {}

    def select(world, rho, conf, label_filter, include_base=True):
        out_rows = []
        for r in days:
            if r["mundo"] != world:
                continue
            par = r["par"]
            if not par.endswith(f"rho{rho:g}"):
                continue
            if r["cenario"] == analise.BASE:
                if include_base:
                    out_rows.append(r)
            elif r["grupo"].endswith(f"|c{conf:g}") and label_filter(r["cenario"]):
                out_rows.append(r)
        return out_rows

    for world, fields in (("origem", (("empty_km", "origem"),)), ("login", (("empty_km", "v1_bruta"), ("empty_km_sim", "pagar_nos_dois")))):
        for field, tag in fields:
            sel = select(world, 1.0, 1.0, _is_plan)
            pairs = analise.build_pairs(sel, field, None, "par")
            res = analise.analyze(pairs, reps, f"F4_{tag}")
            write_csv(out / f"fase4_F4_{tag}_linhas.csv", res["linhas"])
            write_csv(out / f"fase4_F4_{tag}_nb.csv", res["nb"])
            write_csv(out / f"fase4_F4_{tag}_mde.csv", res["mde"])
            summary[f"F4_{tag}"] = {d: sum(1 for x in res["linhas"] if x["decisao"] == d) for d in ("reducao", "aumento", "inconclusivo")}
            # placebo contra o baseline e plano contra o placebo (pareado por dia, mesma semente efetiva)
            plc = select(world, 1.0, 1.0, lambda c: c.startswith("placebo_"))
            res = analise.analyze(analise.build_pairs(plc, field, None, "par"), reps, f"placebo_{tag}")
            write_csv(out / f"fase4_placebo_{tag}_linhas.csv", res["linhas"])
            by_plan = {(r["periodo"], r["data"], r["par"], r["cenario"]): r for r in sel if r["cenario"] != analise.BASE}
            synth = []
            for r in plc:
                name = r["cenario"].removeprefix("placebo_")
                plan = by_plan.get((r["periodo"], r["data"], r["par"], name))
                if plan:
                    key = f"{r['par']}|{name}"
                    synth.append({**r, "cenario": analise.BASE, "grupo": "ref", "par": key, "familia": "nenhum"})
                    synth.append({**plan, "grupo": "plano_vs_placebo", "par": key})
            res = analise.analyze(analise.build_pairs(synth, field, None, "par"), reps, f"plano_vs_placebo_{tag}")
            write_csv(out / f"fase4_plano_vs_placebo_{tag}_linhas.csv", res["linhas"])
            write_csv(out / f"fase4_plano_vs_placebo_{tag}_nb.csv", res["nb"])
            summary[f"plano_vs_placebo_{tag}"] = {d: sum(1 for x in res["linhas"] if x["decisao"] == d) for d in ("reducao", "aumento", "inconclusivo")}
        # B4 como candidato (sem plano) contra cada política Bk; ρ = 1
        cand = [r for r in days if r["mundo"] == world and r["par"].endswith("rho1")
                and r["cenario"] in (analise.BASE, "B4_reativo_candidato")]
        res = analise.analyze(analise.build_pairs(cand, fields[0][0], None, "par"), reps, f"F4c_{world}")
        write_csv(out / f"fase4_candidato_B4_{world}_linhas.csv", res["linhas"])
        write_csv(out / f"fase4_candidato_B4_{world}_nb.csv", res["nb"])
    # grade ρ × conformidade (descritiva, sem p-valores): mundo origem, contabilização primária
    grid_lines, grid_nb = [], []
    for rho in a4.RHOS:
        for conf in a4.CONFS:
            sel = select("origem", rho, conf, _is_plan)
            res = analise.analyze(analise.build_pairs(sel, "empty_km", None, "par"), reps, "grade_descritiva", tests=False)
            for x in res["linhas"]:
                grid_lines.append({"rho": rho, "conformidade": conf, **x})
            for x in res["nb"]:
                grid_nb.append({"rho": rho, "conformidade": conf, **x})
    write_csv(out / "fase4_grade_rho_conformidade.csv", grid_lines)
    write_csv(out / "fase4_grade_rho_conformidade_nb.csv", grid_nb)
    return summary
