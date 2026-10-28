"""Bloco 1 (exploratório): WAPE da previsão de demanda por célula H3 r7 × hora, com conferência contra o artigo.

Uso: TCC_REAL_DATA_AUTHORIZED=YES PYTHONPATH=src python scripts/rodar_demanda.py
Saídas: resultados/demanda/*.csv, resultados/demanda/previsto_real_por_hora.png, tabelas/tab_demanda_wape.tex.
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from statistics import mean

from tcc_frota.analise import demanda as dm
from tcc_frota.v2 import forecast as fc

OUT = Path("resultados/demanda")
TAB07 = {"calibracao_mar": 0.9668, "teste_mar": 0.9566, "teste_set": 0.8816}
SETS = {"calibracao_mar": dm.dates(2026, 3, 2, 15), "teste_mar": dm.dates(2026, 3, 16, 31), "teste_set": dm.dates(2026, 9, 16, 30)}


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()})


def records(model: str, days, history, cfg, alpha=None) -> list[dict]:
    out = []
    for t in days:
        pred = {
            "M0": lambda: dm.m0(t, history, cfg),
            "M1": lambda: dm.m1(t, history, cfg),
            "M2": lambda: dm.m2(t, history, cfg, alpha),
            "Msim": lambda: dm.msim(t, history, cfg),
        }[model]()
        if not pred:
            continue
        out += [{"data": t.isoformat(), **r} for r in dm.day_errors(pred, t, history, dm.strata(t, history, cfg))]
    return out


def main() -> int:
    os.environ.setdefault("TCC_REAL_DATA_AUTHORIZED", "YES")
    from tcc_frota.algoritmos.bateria import build_study

    study = build_study(Path("data/raw"))
    history, cfg = study.history, fc.ForecastConfig()
    # 1) conferência: WAPE médio diário do modelo do simulador = tab07 do artigo
    check = []
    for name, days in SETS.items():
        vals = [
            fc.errors(fc.predict("media_dia_semana", t, history, range(4, 11), cfg), t, history, range(4, 11))["wape_zona_hora"]
            for t in days
        ]
        got = mean(vals)
        check.append(
            {
                "conjunto": name,
                "wape_medio_diario_reproduzido": got,
                "wape_tab07": TAB07[name],
                "diferenca": got - TAB07[name],
                "confere": abs(got - TAB07[name]) < 5e-5,
            }
        )
    write(OUT / "conferencia_tab07.csv", check)
    print(check)
    if not all(c["confere"] for c in check):
        print("WAPE do modelo do simulador não reproduz a tab07: execução interrompida", file=sys.stderr)
        return 1
    # 2) α do M2 só na calibração de março (WAPE agregado global)
    sel = []
    for a in dm.ALPHAS:
        agg = {
            r["escopo"]: r
            for r in dm.aggregate(records("M2", SETS["calibracao_mar"], history, cfg, a), [d.isoformat() for d in SETS["calibracao_mar"]])
        }
        sel.append({"alpha": a, "wape_global_calibracao": agg["global"]["wape"]})
    alpha = min(sel, key=lambda r: (r["wape_global_calibracao"], -r["alpha"]))["alpha"]
    for r in sel:
        r["escolhido"] = r["alpha"] == alpha
    write(OUT / "selecao_alpha_m2.csv", sel)
    print("M2 alpha =", alpha, sel)
    # 3) teste (março) e setembro, parâmetros congelados; calibração reportada para referência
    rows, hourly = [], []
    for name, days in SETS.items():
        iso = [d.isoformat() for d in days]
        for model in dm.MODELS:
            rec = records(model, days, history, cfg, alpha if model == "M2" else None)
            used = sorted({r["data"] for r in rec})
            for r in dm.aggregate(rec, used):
                rows.append(
                    {
                        "modelo": model,
                        "conjunto": name,
                        "alpha_m2": alpha if model == "M2" else "",
                        "dias_sem_previsao": len(iso) - len(used),
                        "rotulo": "exploratorio",
                        **r,
                    }
                )
            for h in dm.HOURS:
                hourly.append(
                    {
                        "modelo": model,
                        "conjunto": name,
                        "hora": h,
                        "real": sum(r["y"] for r in rec if r["hora"] == h),
                        "previsto": sum(r["yhat"] for r in rec if r["hora"] == h),
                    }
                )
    write(OUT / "wape.csv", rows)
    write(OUT / "previsto_real_por_hora.csv", hourly)
    # 4) cobertura: solicitações do universo, na janela, com célula H3
    cov = []
    for name, days in SETS.items():
        reqs = [r for d in days for r in study.requests_by_date.get(d, []) if 4 <= r["hora_local"] < 11]
        cov.append(
            {
                "conjunto": name,
                "solicitacoes_universo_janela": len(reqs),
                "com_celula_h3": sum(bool(r["h3_r7_origem"]) for r in reqs),
                "cobertura_pct": 100 * sum(bool(r["h3_r7_origem"]) for r in reqs) / len(reqs) if reqs else float("nan"),
            }
        )
    write(OUT / "cobertura.csv", cov)
    figure(hourly)
    latex(rows)
    return 0


def figure(hourly: list[dict]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=False)
    colors = {"M0": "#E69F00", "M1": "#009E73", "M2": "#0072B2", "Msim": "#CC79A7"}
    for ax, (name, title) in zip(axes, (("teste_mar", "Março, teste (16–31)"), ("teste_set", "Setembro (16–30)"))):
        sel = [r for r in hourly if r["conjunto"] == name]
        real = [next(r["real"] for r in sel if r["hora"] == h and r["modelo"] == "M0") for h in dm.HOURS]
        ax.bar(dm.HOURS, real, color="#BBBBBB", label="real")
        for m, c in colors.items():
            ax.plot(
                dm.HOURS,
                [next(r["previsto"] for r in sel if r["hora"] == h and r["modelo"] == m) for h in dm.HOURS],
                marker="o",
                color=c,
                label=m,
            )
        ax.set_title(title)
        ax.set_xlabel("Hora")
    axes[0].set_ylabel("Solicitações (soma dos dias)")
    axes[1].legend(fontsize=8)
    fig.suptitle("Previsto × real por hora (exploratório; dados reais)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "previsto_real_por_hora.png", dpi=150)
    plt.close(fig)


def latex(rows: list[dict]) -> None:
    br = lambda x: f"{x:.3f}".replace(".", "{,}")
    pct = lambda x: f"{100 * x:+.1f}".replace(".", "{,}")
    scopes = ("global", "faixa_04-07", "faixa_07-10", "faixa_10-11", "estrato_alto", "estrato_baixo")
    labels = {
        "global": "Global",
        "faixa_04-07": "04--07",
        "faixa_07-10": "07--10",
        "faixa_10-11": "10--11",
        "estrato_alto": r"Células $\geq$ 1/dia",
        "estrato_baixo": "Demais células",
    }
    lines = [
        r"% Gerado por scripts/rodar_demanda.py — exploratório (docs/ESCOPO_FECHADO.md); dados reais.",
        r"\begin{tabular}{llrrrr}",
        r"\hline",
        r"Mês & Escopo & M0 & M1 & M2 & Msim \\",
        r"\hline",
    ]
    for name, mes in (("teste_mar", "mar"), ("teste_set", "set")):
        for s in scopes:
            cells = []
            for m in dm.MODELS:
                r = next(x for x in rows if x["conjunto"] == name and x["modelo"] == m and x["escopo"] == s)
                cells.append(f"{br(r['wape'])} [{br(r['wape_ic_inf'])}; {br(r['wape_ic_sup'])}]")
            lines.append(f"{mes} & {labels[s]} & " + " & ".join(cells) + r" \\")
        vies = [
            pct(next(x for x in rows if x["conjunto"] == name and x["modelo"] == m and x["escopo"] == "global")["vies"]) for m in dm.MODELS
        ]
        lines.append(f"{mes} & Viés global (\\%) & " + " & ".join(vies) + r" \\")
        lines.append(r"\hline")
    lines += [
        r"\multicolumn{6}{l}{\footnotesize WAPE agregado (soma dos erros absolutos por hora ÷ soma das solicitações); IC 95\% por bootstrap de dias.} \\",
        r"\end{tabular}",
    ]
    Path("tabelas/tab_demanda_wape.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())


def diagnostic_alpha(day=None) -> None:
    """Diagnóstico (não altera o α congelado): viés por estrato do M2 num dia de calibração, α da grade × α≈0."""
    from datetime import date as _date

    from tcc_frota.algoritmos.bateria import build_study

    t = day or _date(2026, 3, 9)
    study = build_study(Path("data/raw"))
    history, cfg = study.history, fc.ForecastConfig()
    strat = dm.strata(t, history, cfg)
    rows = []
    for a in (1e-6, 0.01):
        errs = dm.day_errors(dm.m2(t, history, cfg, a), t, history, strat)
        for s in ("alto", "baixo"):
            rows.append(
                {
                    "dia_calibracao": t.isoformat(),
                    "alpha": a,
                    "estrato": s,
                    "real": sum(r["y"] for r in errs if r["estrato"] == s),
                    "previsto": sum(r["yhat"] for r in errs if r["estrato"] == s),
                    "uso": "diagnostico; alpha congelado = 0,01 (grade pre-registrada)",
                }
            )
    write(OUT / "diagnostico_alpha_m2.csv", rows)
