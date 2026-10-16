"""Protocolo do guloso seletivo (C0–C3): calibração, variantes 4.4, congelamento, teste, motivos e Pareto.

Pré-registro: `docs/ORCAMENTO_CONFIGURACOES.md` §5. Reaproveita a agregação, a regra de escolha, o registro
e a estatística da bateria (`protocolo.py`, `estatistica.py`). Saídas agregadas em `resultados/seletivo/`.
"""
from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from tcc_frota.algoritmos.base import PlannerSpec
from tcc_frota.algoritmos.bateria import SEEDS, load_frozen, run_tasks
from tcc_frota.algoritmos import protocolo as pr
from tcc_frota.v2 import experiment as ex

OUT = pr.RESULTS / "seletivo"
RUNS = pr.RUNS / "seletivo"
FINALISTS = OUT / "finalistas.json"
C1 = PlannerSpec("guloso_marginal", "C1_guloso_marginal_a0.2", {"alpha": 0.2, "rho_km": 2.5, "max_km": 3.0})


def grid() -> list[PlannerSpec]:
    return [PlannerSpec("guloso_seletivo", f"C2|H{h:g}|K{k}|tau{t:g}",
                        {"max_km": h, "k": k, "tau": t, "lam": 0.0, "m": 30, "previsao": "padrao"})
            for h in (2.0, 3.0, 4.0) for k in (8, 16) for t in (1.0, 2.0)]


def variants(finalist: dict) -> list[PlannerSpec]:
    return [PlannerSpec("guloso_seletivo", f"C3|{v}", {**finalist, "previsao": v}) for v in ("blocos3h", "h3r6", "deficit")]


def _calibrate(specs: list[PlannerSpec], name: str, workers: int, raw: Path, echo) -> tuple[list[dict], dict]:
    frozen = load_frozen()
    sim = frozen.sims[pr.CALIB_PERIOD]
    tasks = [(pr.CALIB_PERIOD, day, pr.CALIB_WINDOW, pr.CALIB_REGIME, sim, [s], frozen.model, SEEDS, k == 0)
             for day in ex.PERIODS[pr.CALIB_PERIOD].calibration for k, s in enumerate(specs)]
    echo(f"[{name}] {len(specs)} configurações × {len(ex.PERIODS[pr.CALIB_PERIOD].calibration)} dias")
    rows = run_tasks(tasks, raw, workers, echo=echo)
    pr.write_rows(RUNS / f"calibracao_{name}.csv", rows)
    summary = pr.summarise(rows)
    for s in summary:
        s["familia"] = name
    return rows, summary


def _show(summary, chosen, echo):
    for s in sorted(summary, key=lambda s: s["km_vazio_por_corrida"]):
        echo(f"  {s['cenario']:<28} corridas {s['var_corridas_pct']:+6.2f}%  km vazio/corrida "
             f"{s['var_km_vazio_por_corrida_pct']:+6.2f}%  mov {s['movimentos_executados']:.1f}  "
             f"t {s['tempo_plano_medio_s']:.1f}s{'  <- escolhido' if s['cenario'] == chosen else ''}")


def calibrate(workers: int = 10, raw: Path = Path("data/raw"), echo=print, register: bool = True, name: str = "guloso_seletivo") -> dict:
    rows, summary = _calibrate(grid(), name, workers, raw, echo)
    best = pr.choose(summary)
    _show(summary, best["cenario"], echo)
    if register:
        pr.append_registry(summary, best["cenario"], "calibracao", ",".join(map(str, SEEDS)))
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "calibracao_C2.json").write_text(json.dumps({"codigo": pr.git_head(), "finalista": best, "grade": summary},
                                                          ensure_ascii=False, indent=2), encoding="utf-8")
    return best


def calibrate_variants(workers: int = 10, raw: Path = Path("data/raw"), echo=print) -> dict:
    c2 = json.loads((OUT / "calibracao_C2.json").read_text(encoding="utf-8"))["finalista"]
    rows, summary = _calibrate(variants(json.loads(c2["parametros"])), "guloso_seletivo_previsao", workers, raw, echo)
    viable = [s for s in summary if s["satisfaz_piso"] and s["km_vazio_por_corrida"] < c2["km_vazio_por_corrida"] - 1e-12]
    best = min(viable, key=lambda s: s["km_vazio_por_corrida"]) if viable else None
    _show(summary, best["cenario"] if best else "", echo)
    pr.append_registry(summary, best["cenario"] if best else "", "calibracao_variantes_4.4", ",".join(map(str, SEEDS)))
    (OUT / "calibracao_C3.json").write_text(json.dumps({"codigo": pr.git_head(), "c2": c2, "escolhida": best, "grade": summary},
                                                      ensure_ascii=False, indent=2), encoding="utf-8")
    return {"escolhida": best["cenario"] if best else None}


def freeze() -> dict:
    c2 = json.loads((OUT / "calibracao_C2.json").read_text(encoding="utf-8"))["finalista"]
    c3 = json.loads((OUT / "calibracao_C3.json").read_text(encoding="utf-8"))["escolhida"] if (OUT / "calibracao_C3.json").exists() else None
    fin = {"C2": {"cenario": c2["cenario"], "parametros": json.loads(c2["parametros"]), "regra": c2["regra"]},
           "C3": ({"cenario": c3["cenario"], "parametros": json.loads(c3["parametros"])} if c3 else None),
           "congelado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "codigo": pr.git_head()}
    FINALISTS.write_text(json.dumps(fin, ensure_ascii=False, indent=2), encoding="utf-8")
    return fin


def test_specs() -> list[PlannerSpec]:
    fin = json.loads(FINALISTS.read_text(encoding="utf-8"))
    specs = [C1, PlannerSpec("guloso_seletivo", "C2_guloso_seletivo", fin["C2"]["parametros"])]
    if fin.get("C3"):
        specs.append(PlannerSpec("guloso_seletivo", "C3_seletivo_previsao", fin["C3"]["parametros"]))
    return specs


def run_test(period: str, workers: int = 10, raw: Path = Path("data/raw"), echo=print) -> Path:
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(FINALISTS)], capture_output=True).returncode == 0
    clean = not subprocess.run(["git", "status", "--porcelain", str(FINALISTS)], capture_output=True, text=True).stdout.strip()
    if not (tracked and clean):
        raise SystemExit("resultados/seletivo/finalistas.json precisa estar commitado antes do teste")
    frozen = load_frozen()
    specs = test_specs()
    tasks = [(period, day, pr.CALIB_WINDOW, regime, frozen.sims[period], [s], frozen.model, SEEDS, k == 0)
             for day in ex.PERIODS[period].test for regime in pr.TEST_REGIMES for k, s in enumerate(specs)]
    echo(f"[seletivo teste {period}] {len(specs)} cenários × {len(ex.PERIODS[period].test)} dias × 2 regimes")
    rows = run_tasks(tasks, raw, workers, echo=echo)
    path = OUT / f"finalistas_{pr.MONTH_LABEL[period]}_dias.csv"
    pr.write_rows(path, rows)
    return path


def analyse(period: str) -> list[dict]:
    from tcc_frota.algoritmos.estatistica import analyse as an, holm

    rows = pr.read_rows(OUT / f"finalistas_{pr.MONTH_LABEL[period]}_dias.csv")
    out = []
    for regime in pr.TEST_REGIMES:
        days = pr.per_day([r for r in rows if r["regime"] == regime])
        scen = sorted({c for c, _ in days if c != "sem_reposicionamento"})
        res = {c: {"periodo": period, "regime": regime, "cenario": c, "m_comparacoes": len(scen),
                   **an(pr.paired(days, c), len(scen))} for c in scen}
        adj = holm({c: v["p_km_vazio_por_corrida"] for c, v in res.items()})
        for c, v in res.items():
            v["p_km_vazio_por_corrida_holm"] = adj[c]
            out.append(v)
    pr.write_rows(OUT / f"finalistas_{pr.MONTH_LABEL[period]}.csv", out)
    return out


def reasons_table() -> list[dict]:
    """Contagens de motivos por mês, regime e cenário (sem identificadores)."""
    from tcc_frota.algoritmos.guloso_seletivo import REASONS

    out = []
    for period, lab in pr.MONTH_LABEL.items():
        path = OUT / f"finalistas_{lab}_dias.csv"
        if not path.exists():
            continue
        acc: dict[tuple, dict] = defaultdict(lambda: defaultdict(float))
        for r in pr.read_rows(path):
            if r["familia"] != "guloso_seletivo":
                continue
            info = json.loads(r["info"])
            a = acc[(period, r["regime"], r["cenario"])]
            a["planos"] += 1
            for k in REASONS:
                a[k] += info.get(k, 0)
        for (p, reg, c), a in sorted(acc.items()):
            tot = sum(a[k] for k in REASONS)
            out.append({"periodo": p, "regime": reg, "cenario": c, "planos_dia_semente": int(a["planos"]),
                        **{k: a[k] / a["planos"] for k in REASONS},
                        **{f"{k}_pct": 100 * a[k] / tot if tot else 0.0 for k in REASONS}})
    pr.write_rows(OUT / "motivos_decisao.csv", out)
    return out


def pareto() -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    colors = {"C1": "#E69F00", "C2": "#0072B2", "C3": "#009E73"}
    rows = []
    for ax, (period, lab) in zip(axes, pr.MONTH_LABEL.items()):
        path = OUT / f"finalistas_{lab}.csv"
        if not path.exists():
            continue
        ax.scatter([0], [0], marker="*", s=200, color="black", label="C0 (baseline)", zorder=5)
        for r in pr.read_rows(path):
            if r["regime"] != "B":
                continue
            x, y = float(r["km_vazio_por_corrida_var_pct"]), float(r["corridas_atendidas_var_pct"])
            key = r["cenario"][:2]
            ax.errorbar(x, y, xerr=[[x - float(r["km_vazio_por_corrida_var_pct_ic_inf"])], [float(r["km_vazio_por_corrida_var_pct_ic_sup"]) - x]],
                        yerr=[[y - float(r["corridas_atendidas_var_pct_ic_inf"])], [float(r["corridas_atendidas_var_pct_ic_sup"]) - y]],
                        fmt="o", color=colors.get(key, "grey"), label=r["cenario"], capsize=3)
            rows.append({"periodo": period, "cenario": r["cenario"], "var_corridas_pct": y, "var_km_vazio_por_corrida_pct": x})
        ax.axvline(0, color="grey", lw=0.8, ls="--")
        ax.axhline(-1, color="grey", lw=0.8, ls=":")
        ax.set_title(f"{lab} (teste, regime B)")
        ax.set_xlabel("KM vazio total por corrida (%)")
    axes[0].set_ylabel("Corridas atendidas (%)")
    axes[1].legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    out = OUT / "pareto_C0_C3.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    pr.write_rows(OUT / "pareto_C0_C3.csv", [{"periodo": p, "cenario": "C0_sem_reposicionamento", "var_corridas_pct": 0.0,
                                               "var_km_vazio_por_corrida_pct": 0.0} for p in pr.MONTH_LABEL] + rows)
    return out
