"""Fase D: valor líquido por corrida extra (critério econômico H3/H-S2), calculado por script.

    custo_km_vazio = r_km + r_min · 60 / v
    e*             = margem / custo_km_vazio        (KM vazio máximo por corrida extra que ainda compensa)
    valor líquido  = margem − e · custo_km_vazio    (e = KM vazio adicional por corrida extra do cenário)

Os parâmetros financeiros são sigilosos: vêm de `config/custos_privado.yaml` (ignorado pelo Git), e a tabela
com esses valores vai só para `reports/runs/seletivo/` (ignorado). O que se publica é uma grade paramétrica
genérica (margens e custos por km ilustrativos, não os da empresa) e o *e* de cada cenário, que vem da
simulação. Limitação registrada: o custo gravado pelo SQL da empresa difere do recalculado.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

PRIVATE = Path("config/custos_privado.yaml")
PRIVATE_OUT = Path("reports/runs/seletivo/valor_liquido_privado.csv")
PUBLIC_TEX = Path("tabelas/tab_seletivo_valor_liquido_parametrico.tex")
PUBLIC_E = Path("resultados/seletivo/km_vazio_por_corrida_extra.csv")
SOURCES = {"seletivo": "resultados/seletivo/finalistas_{m}.csv", "bateria": "resultados/finalistas_{m}.csv"}


def load_costs(path: Path = PRIVATE) -> dict:
    """Leitor mínimo do YAML privado (pares chave: valor, um nível de aninhamento e listas [a, b])."""
    out: dict = {}
    parent = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        key, _, value = line.strip().partition(":")
        value = value.strip()
        indented = raw.startswith((" ", "\t"))
        if not value:
            parent = key
            out[key] = {}
            continue
        parsed = [float(v) for v in value.strip("[]").split(",")] if value.startswith("[") else float(value)
        if indented and parent:
            out[parent][key] = parsed
        else:
            parent = None
            out[key] = parsed
    return out


def cost_per_km(r_km: float, r_min: float, speed_kmh: float) -> float:
    return r_km + r_min * 60.0 / speed_kmh


def scenario_e() -> list[dict]:
    rows = []
    for source, pattern in SOURCES.items():
        for m in ("marco", "setembro"):
            path = Path(pattern.format(m=m))
            if not path.exists():
                continue
            for r in csv.DictReader(path.open(encoding="utf-8")):
                if r["regime"] != "B":
                    continue
                e = float(r["km_vazio_incremental_por_corrida_extra"])
                rows.append({"fonte": source, "mes": m, "cenario": r["cenario"], "corridas_extras_por_dia": float(r["corridas_extras_por_dia"]),
                             "e_km_vazio_por_corrida_extra": e, "e_ic_inf": float(r["km_vazio_incremental_por_corrida_extra_ic_inf"]),
                             "e_ic_sup": float(r["km_vazio_incremental_por_corrida_extra_ic_sup"])})
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})


def private_table(costs: dict, es: list[dict]) -> list[dict]:
    out = []
    for base, margin in costs["margens"].items():
        for v in costs["velocidades_vazio_kmh"]:
            c = cost_per_km(costs["r_km"], costs["r_min"], v)
            e_star = margin / c
            for r in es:
                e = r["e_km_vazio_por_corrida_extra"]
                ok = e == e and e < e_star
                out.append({"base_margem": base, "velocidade_kmh": v, "custo_km_vazio": c, "e_estrela_km": e_star, **r,
                            "valor_liquido_por_corrida_extra": (margin - e * c) if e == e else float("nan"),
                            "e_menor_que_e_estrela": ok})
    return out


# Valores SINTÉTICOS fornecidos na resposta simulada da operação (16/10/2026): diferença ticket − repasse
# por faixa horária e grade de custo variável por km vazio. Não são estatísticas observadas da empresa.
SYNTHETIC_MARGINS = {"04-07h": 8.85, "07-10h": 10.44, "10-11h": 8.16}
SYNTHETIC_COSTS = (0.50, 0.75, 1.00, 1.25, 1.50)


def public_grid() -> Path:
    """Grade paramétrica com valores sintéticos (rotulados): e* = margem / custo variável por km vazio."""
    margins = SYNTHETIC_MARGINS
    costs = SYNTHETIC_COSTS
    lines = [r"% Gerado por tcc_frota.analise.valor_liquido — valores SINTÉTICOS (resposta simulada); não são da empresa.",
             r"\begin{tabular}{l" + "r" * len(costs) + "}", r"\hline",
             r"Faixa (margem sintética, R\$) & " + " & ".join(f"c = {c:.2f}".replace(".", "{,}") for c in costs) + r" \\", r"\hline"]
    for label, m in margins.items():
        lines.append(f"{label} ({m:.2f})".replace(".", "{,}") + " & " + " & ".join(f"{m / c:.1f}".replace(".", "{,}") for c in costs) + r" \\")
    lines += [r"\hline", r"\end{tabular}"]
    PUBLIC_TEX.parent.mkdir(exist_ok=True)
    PUBLIC_TEX.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return PUBLIC_TEX


def main() -> int:
    es = scenario_e()
    write_csv(PUBLIC_E, es)
    public_grid()
    if not PRIVATE.exists():
        print("config/custos_privado.yaml ausente: só a grade pública e o e por cenário foram gerados")
        return 0
    rows = private_table(load_costs(), es)
    write_csv(PRIVATE_OUT, rows)
    print(f"tabela privada: {PRIVATE_OUT} ({len(rows)} linhas; não versionar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
