"""Fase D: valor líquido por corrida extra (critério econômico H3/H-S2), calculado por script.

    custo_km_vazio = r_km + r_min · 60 / v
    e*             = margem / custo_km_vazio        (KM vazio máximo por corrida extra que ainda compensa)
    valor líquido  = margem − e · custo_km_vazio    (e = KM vazio adicional por corrida extra do cenário)

Os parâmetros financeiros são sigilosos: vêm de `config/custos_privado.yaml` (ignorado pelo Git), e a tabela
com esses valores vai só para `reports/runs/seletivo/` (ignorado). O que se publica é uma grade paramétrica
definida pelos autores (docs/PREMISSAS_E_LIMITACOES.md, seção 3; valores hipotéticos, não da empresa) e o *e*
de cada cenário, que vem da simulação. Limitação registrada: o custo gravado pelo SQL da empresa difere do recalculado.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

PRIVATE = Path("config/custos_privado.yaml")
PRIVATE_OUT = Path("reports/runs/seletivo/valor_liquido_privado.csv")
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


# Grade hipotética definida pelos autores (docs/PREMISSAS_E_LIMITACOES.md, seção 3). Não são valores da empresa.
GRID_MARGINS = (10.0, 15.0, 20.0, 25.0, 30.0)   # R$ por corrida, antes do km vazio
GRID_R_KM = (0.5, 1.0, 1.5)                      # R$/km
GRID_R_MIN = (0.15, 0.30, 0.45)                  # R$/min
GRID_SPEEDS = (14.0, 17.0, 20.0)                 # km/h do deslocamento vazio
GRID_NOTE = "Valores hipotéticos definidos pelos autores; não são da empresa."
EQ_GRID_TEX = Path("tabelas/tab_equilibrio_grade.tex")
EQ_SCEN_TEX = Path("tabelas/tab_equilibrio_cenarios.tex")
EQ_SCEN_CSV = Path("resultados/equilibrio/equilibrio_cenarios.csv")


def grid_cells() -> list[dict]:
    """135 células: margem × r_km × r_min × v, com c_v = r_km + r_min·60/v e e* = margem / c_v."""
    out = []
    for r_km in GRID_R_KM:
        for r_min in GRID_R_MIN:
            for v in GRID_SPEEDS:
                c = cost_per_km(r_km, r_min, v)
                for m in GRID_MARGINS:
                    out.append({"margem": m, "r_km": r_km, "r_min": r_min, "v_kmh": v, "c_v": c, "e_estrela_km": m / c})
    return out


def _br(x: float, d: int = 2) -> str:
    return f"{x:.{d}f}".replace(".", "{,}")


def grid_tex(path: Path) -> Path:
    """e* (km) por combinação de custo (linhas, em ordem de c_v) e margem (colunas)."""
    combos = sorted({(c["r_km"], c["r_min"], c["v_kmh"], c["c_v"]) for c in grid_cells()}, key=lambda t: (t[3], t))
    lines = [r"% Gerado por tcc_frota.analise.valor_liquido — " + GRID_NOTE,
             r"\begin{tabular}{rrrr" + "r" * len(GRID_MARGINS) + "}", r"\hline",
             r"$r_{km}$ (R\$/km) & $r_{min}$ (R\$/min) & $v$ (km/h) & $c_v$ (R\$/km) & "
             + " & ".join(f"$e^*$, M = {int(m)}" for m in GRID_MARGINS) + r" \\", r"\hline"]
    for r_km, r_min, v, c in combos:
        lines.append(f"{_br(r_km)} & {_br(r_min)} & {int(v)} & {_br(c)} & " + " & ".join(_br(m / c, 1) for m in GRID_MARGINS) + r" \\")
    lines += [r"\hline", r"\multicolumn{" + str(4 + len(GRID_MARGINS)) + r"}{l}{\footnotesize " + GRID_NOTE
              + r" $e^*$ em km; M = margem por corrida (R\$).} \\", r"\end{tabular}"]
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def classify(es: list[dict]) -> list[dict]:
    """Por cenário: células da grade com e < e* (compensa). e indefinido quando não há corridas extras."""
    cells = grid_cells()
    out = []
    for r in es:
        e, hi = r["e_km_vazio_por_corrida_extra"], r["e_ic_sup"]
        if e != e or r["corridas_extras_por_dia"] <= 0:
            n, n_hi, label = None, None, "não se aplica (sem corridas extras)"
        else:
            n = sum(e < c["e_estrela_km"] for c in cells)
            n_hi = sum(hi == hi and hi < c["e_estrela_km"] for c in cells)
            label = ("compensa em toda a grade" if n == len(cells) else "compensa em nenhuma célula" if n == 0
                     else "compensa em parte da grade")
        out.append({**r, "celulas_grade": len(cells), "celulas_e_menor_e_estrela": n,
                    "celulas_ic_sup_menor_e_estrela_exploratorio": n_hi, "classificacao": label})
    return out


def scenarios_tex(rows: list[dict], path: Path) -> Path:
    lines = [r"% Gerado por tcc_frota.analise.valor_liquido — grade: " + GRID_NOTE,
             r"\begin{tabular}{llrrrl}", r"\hline",
             r"Mês & Cenário & $e$ (km) [IC 95\%] & Células com $e < e^*$ & IC sup. $< e^*$ (expl.) & Leitura \\", r"\hline"]
    for r in rows:
        e = r["e_km_vazio_por_corrida_extra"]
        cell_e = "---" if e != e else f"{_br(e, 1)} [{_br(r['e_ic_inf'], 1)}; {_br(r['e_ic_sup'], 1)}]"
        n = "---" if r["celulas_e_menor_e_estrela"] is None else f"{r['celulas_e_menor_e_estrela']}/{r['celulas_grade']}"
        nh = "---" if r["celulas_ic_sup_menor_e_estrela_exploratorio"] is None else f"{r['celulas_ic_sup_menor_e_estrela_exploratorio']}/{r['celulas_grade']}"
        name = r["cenario"].replace("_", r"\_")
        lines.append(f"{r['mes']} & {name} & {cell_e} & {n} & {nh} & {r['classificacao']} \\\\")
    lines += [r"\hline", r"\end{tabular}"]
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    es = scenario_e()
    write_csv(PUBLIC_E, es)
    grid_tex(EQ_GRID_TEX)
    rows = classify(es)
    write_csv(EQ_SCEN_CSV, rows)
    scenarios_tex(rows, EQ_SCEN_TEX)
    if not PRIVATE.exists():
        print("config/custos_privado.yaml ausente: só as grades dos autores e o e por cenário foram gerados")
        return 0
    priv = private_table(load_costs(), es)
    write_csv(PRIVATE_OUT, priv)
    print(f"verificação interna (não citar): {PRIVATE_OUT} ({len(priv)} linhas; não versionar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
