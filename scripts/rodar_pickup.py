"""Bloco 2 (exploratório): pickup das corridas extras × comuns, decomposição de e, pickup realizado e não atendimento.

Uso: TCC_REAL_DATA_AUTHORIZED=YES PYTHONPATH=src python scripts/rodar_pickup.py [--workers 10]
Saídas: resultados/pickup/*.csv, resultados/pickup/hist_extras_comuns.png, tabelas/tab_pickup_corridas_extras.tex.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from multiprocessing import get_context
from pathlib import Path

from tcc_frota.algoritmos import bateria
from tcc_frota.algoritmos.base import PlannerSpec
from tcc_frota.algoritmos.protocolo import test_specs
from tcc_frota.analise import pickup as pk
from tcc_frota.v2 import experiment as ex

OUT = Path("resultados/pickup")
MONTH = {"mar2026": "marco", "set2026": "setembro"}


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()})


def specs() -> list[PlannerSpec]:
    out = test_specs()          # referências do artigo + finalistas congelados da bateria
    fin = json.loads(Path("resultados/seletivo/finalistas.json").read_text(encoding="utf-8"))
    out.append(PlannerSpec("guloso_seletivo", "C2_guloso_seletivo", fin["C2"]["parametros"]))
    return out


def _task(args):
    period, day, spec, seed = args
    frozen = bateria.load_frozen()
    return {"periodo": period, **pk.day_rides(bateria._STUDY, period, day, frozen.sims[period], spec, frozen.model, seed)}


def expected_daily() -> dict:
    """Corridas e KM de busca por (período, cenário, dia, semente) nos CSV de teste existentes (regime B)."""
    out = {}
    for f in ("resultados/finalistas_{m}_dias.csv", "resultados/seletivo/finalistas_{m}_dias.csv"):
        for period, m in MONTH.items():
            with open(f.format(m=m), encoding="utf-8") as h:
                for r in csv.DictReader(h):
                    if r["regime"] == "B":
                        out[(period, r["cenario"], r["data"], r["semente"])] = (int(r["served"]), float(r["pickup_km"]))
    return out


def main(workers: int = 10) -> int:
    os.environ.setdefault("TCC_REAL_DATA_AUTHORIZED", "YES")
    tasks = []
    for s in specs():
        planner = bateria.build_planner(s)
        for period in ex.PERIODS:
            for day in ex.PERIODS[period].test:
                for seed in (bateria.SEEDS if planner.stochastic else bateria.SEEDS[:1]):
                    tasks.append((period, day, s, seed))
    with get_context("spawn").Pool(workers, initializer=bateria._init_worker, initargs=("data/raw",)) as pool:
        days = pool.map(_task, tasks)
    # conferência contra os CSV diários existentes
    exp = expected_daily()
    bad = 0
    for d in days:
        key = (d["periodo"], d["cenario"], d["data"], str(d["semente"]))
        base_key = (d["periodo"], "sem_reposicionamento", d["data"], "")
        for k, served, km in ((key, d["served"], d["pickup"]), (base_key, d["served_base"], d["pickup_base"])):
            s, p = exp[k]
            bad += s != served or abs(p - km) > 1e-4
    print(f"conferência com os CSV diários: {len(days)} dias-cenário-semente, divergências: {bad}")
    if bad:
        return 1
    # estatísticas por cenário e mês (sementes e dias reunidos)
    pooled = defaultdict(lambda: defaultdict(list))
    for d in days:
        for k in ("extras", "comuns", "perdidas_base", "baseline"):
            pooled[(d["periodo"], d["cenario"])][k] += d[k]
    finals = {}
    for f in ("resultados/finalistas_{m}.csv", "resultados/seletivo/finalistas_{m}.csv"):
        for period, m in MONTH.items():
            with open(f.format(m=m), encoding="utf-8") as h:
                for r in csv.DictReader(h):
                    if r["regime"] == "B":
                        finals[(period, r["cenario"])] = r
    rows = []
    for (period, scen), g in sorted(pooled.items()):
        r = finals[(period, scen)]
        dn = float(r["soma_prop_served"]) - float(r["soma_base_served"])
        db = float(r["soma_prop_pickup_km"]) - float(r["soma_base_pickup_km"])
        dr = float(r["soma_prop_reposition_km"]) - float(r["soma_base_reposition_km"])
        de = float(r["soma_prop_empty_km"]) - float(r["soma_base_empty_km"])
        row = {"periodo": period, "cenario": scen, "rotulo": "exploratorio",
               "delta_corridas": dn, "delta_busca_km": db, "delta_repos_km": dr, "delta_vazio_km": de,
               "b_mais_r_confere": abs(db + dr - de) < 1e-3,
               "e_km": de / dn if dn > 0 else float("nan"), "e_busca_km": db / dn if dn > 0 else float("nan"),
               "e_repos_km": dr / dn if dn > 0 else float("nan")}
        for k in ("extras", "comuns", "perdidas_base", "baseline"):
            row.update({f"{k}_{s}": v for s, v in pk.summary(g[k]).items()})
        rows.append(row)
    write(OUT / "pickup_corridas_extras.csv", rows)
    # dados reais: pickup realizado × pickup simulado do baseline, nos mesmos dias
    study = bateria.build_study(Path("data/raw"))
    dec, unserved = [], []
    for period in ex.PERIODS:
        real = pk.real_pickup(study, ex.PERIODS[period].test)
        sim_base_unique = pooled[(period, "ref_proporcional")]["baseline"]   # cenário determinístico: 1 baseline por dia
        for name, vals, extra in (("pickup_realizado_distMotorista", real["valores"],
                                   {"aceitas": real["aceitas"], "com_campo": real["com_pickup_realizado"], "cobertura_pct": real["cobertura_pct"]}),
                                  ("pickup_simulado_baseline_C0", sim_base_unique, {"cobertura_pct": 100.0})):
            s = pk.summary(vals)
            dec.append({"periodo": period, "medida": name, **extra, **s,
                        **{f"decil_{q}0": v for q, v in zip(range(1, 10), pk.deciles(vals))}})
        unserved += [{"periodo": period, **r} for r in pk.unserved_by_distance(study, ex.PERIODS[period].test)]
    write(OUT / "pickup_realizado_decis.csv", dec)
    write(OUT / "nao_atendimento_por_distancia.csv", unserved)
    figure(days)
    latex(rows)
    for r in rows:
        print(r["periodo"], r["cenario"], r["extras_n"], round(r["extras_mediana_km"], 2) if r["extras_n"] else "-",
              round(r["comuns_mediana_km"], 2))
    return 0


def figure(days) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, (period, title) in zip(axes, (("mar2026", "Março, teste"), ("set2026", "Setembro"))):
        ext = [v for d in days if d["periodo"] == period for v in d["extras"]]
        com = [v for d in days if d["periodo"] == period for v in d["comuns"]]
        bins = [x * 0.25 for x in range(0, 33)]
        ax.hist(com, bins=bins, density=True, alpha=0.55, color="#0072B2", label=f"comuns (n = {len(com)})")
        ax.hist(ext, bins=bins, density=True, alpha=0.55, color="#E69F00", label=f"extras (n = {len(ext)})")
        ax.set_title(title)
        ax.set_xlabel("Pickup simulado (km)")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Densidade")
    fig.suptitle("Pickup das corridas extras × comuns, todos os cenários (exploratório; simulador com dados reais)", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "hist_extras_comuns.png", dpi=150)
    plt.close(fig)


def latex(rows) -> None:
    f = lambda x, d=2: "---" if x != x else f"{x:.{d}f}".replace(".", "{,}")
    lines = [r"% Gerado por scripts/rodar_pickup.py — exploratório (docs/ESCOPO_FECHADO.md); simulador com dados reais.",
             r"\begin{tabular}{llrrrrrrrr}", r"\hline",
             r"Mês & Cenário & \multicolumn{4}{c}{Extras: pickup (km)} & \multicolumn{2}{c}{Comuns (km)} & $e$ & $e_B$ / $e_R$ \\",
             r" & & n & média & mediana & p90 & média & mediana & (km) & (km) \\", r"\hline"]
    for r in rows:
        name = r["cenario"].replace("_", r"\_")
        mes = "mar" if r["periodo"] == "mar2026" else "set"
        lines.append(f"{mes} & {name} & {r['extras_n']} & {f(r['extras_media_km'])} & {f(r['extras_mediana_km'])} & "
                     f"{f(r['extras_p90_km'])} & {f(r['comuns_media_km'])} & {f(r['comuns_mediana_km'])} & {f(r['e_km'], 1)} & "
                     f"{f(r['e_busca_km'], 1)} / {f(r['e_repos_km'], 1)} \\\\")
    lines += [r"\hline", r"\multicolumn{10}{l}{\footnotesize Regime B, 04--11h, dias de teste; sementes e dias reunidos. "
              r"$e = e_B + e_R$: KM vazio (busca + reposicionamento) por corrida extra; --- em $e$: sem ganho líquido de corridas "
              r"($\Delta$corridas $\le 0$). Nos algoritmos estocásticos, n soma as 5 sementes. Exploratório.} \\",
              r"\end{tabular}"]
    Path("tabelas/tab_pickup_corridas_extras.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 10))
