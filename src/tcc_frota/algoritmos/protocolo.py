"""Protocolo da bateria: grades pré-registradas, calibração, registro, escolha do finalista e congelamento.

Grades: `docs/ORCAMENTO_CONFIGURACOES.md`. A calibração usa só 2–15/03, regime B, janela 04–11h.
Saídas agregadas (sem dado pessoal) em `resultados/`; linhas por dia e semente também em
`reports/runs/bateria/` (ignorado), para reprocessamento.
"""
from __future__ import annotations

import csv
import json
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from tcc_frota.algoritmos.base import PlannerSpec
from tcc_frota.algoritmos.bateria import SEEDS, load_frozen, run_tasks
from tcc_frota.v2 import experiment as ex

RESULTS = Path("resultados")
RUNS = Path("reports/runs/bateria")
FINALISTS = RESULTS / "finalistas.json"
REGISTRY_CSV = RESULTS / "registro_configuracoes.csv"
FLOOR = 0.99   # corridas >= 0,99 x baseline (δ = 1%)
EXTRA_FAMILIES = ("mpc", "despacho")   # fora da tabela principal (intradiário e D+0)
EXTRAS_JSON = RESULTS / "finalistas_extras.json"
CALIB_PERIOD, CALIB_REGIME, CALIB_WINDOW = "mar2026", "B", ex.MAIN_WINDOW

DAY_FIELDS = ("n_requests", "served", "pickup_km", "reposition_km", "empty_km", "wait_sum", "moves_planned",
              "moves_executed", "km_planejado", "plan_seconds")


def git_head() -> str:
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "src"], capture_output=True, text=True).stdout.strip())
        return head + ("+alteracoes" if dirty else "")
    except OSError:
        return "desconhecido"


def load_finalists() -> dict:
    return json.loads(FINALISTS.read_text(encoding="utf-8")) if FINALISTS.exists() else {}


# ------------------------------------------------------------------ grades (pré-registradas)
def grid(family: str) -> list[PlannerSpec]:
    fin = load_finalists()
    specs: list[PlannerSpec] = []
    if family in ("fluxo_custo_minimo", "hungaro"):
        for alvo in ("demanda", "valor_marginal", "teto"):
            for hop in (3.0, 4.0):
                for share in (1.0, 1.3):
                    p = {"alvo": alvo, "share": share, "max_km": hop, "teto": 2 if alvo == "teto" else None}
                    specs.append(PlannerSpec(family, f"{family}|{alvo}|H{hop:g}|s{share:g}", p))
    elif family == "milp":
        for cap in (1.0, 1.5, 3.0):
            for beta in (1.0, 0.99):
                for mu in (0.0, 0.5):
                    specs.append(PlannerSpec(family, f"milp|cap{cap:g}|b{beta:g}|mu{mu:g}",
                                             {"cap": cap, "beta": beta, "mu": mu, "max_km": 4.0, "time_limit": 30.0}))
    elif family == "robusto_cenarios":
        m = fin["milp"]["parametros"]
        for s in (5, 10, 20):
            for obj in ("esperado", "cvar"):
                specs.append(PlannerSpec(family, f"robusto|S{s}|{obj}",
                                         {"n_cenarios": s, "objetivo": obj, "cap": m["cap"], "beta": m["beta"],
                                          "mu": m["mu"], "max_km": 4.0, "time_limit": 60.0}))
    elif family == "busca_local":
        for start in ("guloso", "fluxo"):
            for budget in (100, 300):
                for k in (2, 4):
                    p = {"inicio": start, "avaliacoes": budget, "k": k, "max_km": 4.0}
                    if start == "fluxo":
                        p["fluxo"] = fin["fluxo_custo_minimo"]["parametros"]
                    specs.append(PlannerSpec(family, f"lns|{start}|E{budget}|k{k}", p))
    elif family == "recozimento":
        for t0 in (0.005, 0.02):
            for r in (0.98, 0.995):
                specs.append(PlannerSpec(family, f"sa|T{t0:g}|r{r:g}",
                                         {"t0": t0, "resfriamento": r, "avaliacoes": 300, "max_km": 4.0}))
    elif family == "pso":
        for p_stay in (0.8, 0.95):
            for w in (0.5, 0.8):
                specs.append(PlannerSpec(family, f"pso|p{p_stay:g}|w{w:g}",
                                         {"p_ficar": p_stay, "inercia": w, "particulas": 15, "iteracoes": 20, "max_km": 4.0}))
    elif family == "nsga2":
        busca = json.loads((RESULTS / "calibracao" / "nsga2_busca.json").read_text(encoding="utf-8"))
        specs.append(PlannerSpec(family, "nsga2|pop20|ger15", {"finalistas": busca["finalistas"]}))
    else:
        raise ValueError(f"família sem grade de calibração: {family}")
    return specs


# ------------------------------------------------------------------ agregação
def per_day(rows: list[dict]) -> dict[tuple[str, str], dict]:
    """Média das sementes por (cenário, dia); o baseline é a linha `sem_reposicionamento`."""
    acc: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        acc[(r["cenario"], r["data"])].append(r)
    out = {}
    for key, rs in acc.items():
        out[key] = {f: sum(float(r[f]) for r in rs) / len(rs) for f in DAY_FIELDS}
        out[key]["sementes"] = len(rs)
        out[key]["plan_seconds_max"] = max(float(r["plan_seconds"]) for r in rs)
        out[key]["motoristas_mundo"] = float(rs[0].get("motoristas_mundo") or 0)
        out[key]["parametros"] = rs[0]["parametros"]
        out[key]["familia"] = rs[0]["familia"]
    return out


def paired(days: dict[tuple[str, str], dict], scenario: str) -> list[dict]:
    dates = sorted(d for (c, d) in days if c == scenario)
    return [{"data": d, "b": days[("sem_reposicionamento", d)], "p": days[(scenario, d)]}
            for d in dates if ("sem_reposicionamento", d) in days]


def summarise(rows: list[dict]) -> list[dict]:
    days = per_day(rows)
    out = []
    for scen in sorted({c for c, _ in days if c != "sem_reposicionamento"}):
        pairs = paired(days, scen)
        tot = {k: sum(p["p"][k] for p in pairs) for k in DAY_FIELDS}
        base = {k: sum(p["b"][k] for p in pairs) for k in DAY_FIELDS}
        km_ride = tot["empty_km"] / tot["served"] if tot["served"] else float("inf")
        km_ride_b = base["empty_km"] / base["served"]
        first = pairs[0]["p"]
        out.append({
            "cenario": scen, "familia": first["familia"], "parametros": first["parametros"], "dias": len(pairs),
            "sementes_por_dia": first["sementes"],
            "corridas_base": base["served"], "corridas": tot["served"],
            "var_corridas_pct": 100 * (tot["served"] / base["served"] - 1),
            "km_vazio_por_corrida_base": km_ride_b, "km_vazio_por_corrida": km_ride,
            "var_km_vazio_por_corrida_pct": 100 * (km_ride / km_ride_b - 1),
            "km_busca_por_corrida": tot["pickup_km"] / tot["served"] if tot["served"] else float("nan"),
            "km_repos_por_corrida": tot["reposition_km"] / tot["served"] if tot["served"] else float("nan"),
            "movimentos_executados": tot["moves_executed"], "movimentos_planejados": tot["moves_planned"],
            "km_planejado": tot["km_planejado"], "tempo_plano_medio_s": tot["plan_seconds"] / len(pairs),
            "dias_com_reducao": sum(p["p"]["empty_km"] / max(p["p"]["served"], 1e-9) < p["b"]["empty_km"] / max(p["b"]["served"], 1e-9) - 1e-12 for p in pairs),
            "satisfaz_piso": tot["served"] >= FLOOR * base["served"] - 1e-9,
        })
    return out


def choose(summary: list[dict]) -> dict:
    """Regra pré-registrada: menor KM vazio/corrida com corridas ≥ 0,99 × baseline."""
    viable = [s for s in summary if s["satisfaz_piso"]]
    if viable:
        best = min(viable, key=lambda s: (s["km_vazio_por_corrida"], s["cenario"]))
        return {**best, "regra": "menor km vazio/corrida com piso de atendimento"}
    best = max(summary, key=lambda s: (s["corridas"], -s["km_vazio_por_corrida"]))
    return {**best, "regra": "sem configuração viável: maior razão de corridas"}


REGISTRY_COLS = ("registrado_em", "codigo", "etapa", "familia", "cenario", "parametros", "sementes", "dias",
                 "corridas_base", "corridas", "var_corridas_pct", "km_vazio_por_corrida_base", "km_vazio_por_corrida",
                 "var_km_vazio_por_corrida_pct", "km_busca_por_corrida", "km_repos_por_corrida",
                 "movimentos_planejados", "movimentos_executados", "km_planejado", "tempo_plano_medio_s",
                 "dias_com_reducao", "satisfaz_piso", "selecionado")


def append_registry(summary: list[dict], chosen: str, stage: str, seeds: str) -> None:
    RESULTS.mkdir(exist_ok=True)
    new = not REGISTRY_CSV.exists()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with REGISTRY_CSV.open("a", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=REGISTRY_COLS, extrasaction="ignore")
        if new:
            w.writeheader()
        for s in summary:
            row = {**s, "registrado_em": stamp, "codigo": git_head(), "etapa": stage, "sementes": seeds,
                   "selecionado": s["cenario"] == chosen}
            w.writerow({k: (round(v, 6) if isinstance(v, float) else v) for k, v in row.items()})


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols: list[str] = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    with path.open("w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()})


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def calibrate(family: str, *, workers: int = 12, raw: Path = Path("data/raw"), echo=print,
              register: bool = True, out_name: str | None = None) -> dict:
    """Roda a grade da família nos dias de calibração, registra tudo e grava o finalista candidato."""
    frozen = load_frozen()
    extra = family in EXTRA_FAMILIES
    if extra:
        from tcc_frota.algoritmos.extras import grid_extra

        specs = grid_extra(family)
    else:
        specs = grid(family)
    sim = frozen.sims[CALIB_PERIOD]
    tasks = [(CALIB_PERIOD, day, CALIB_WINDOW, CALIB_REGIME, sim, [s], frozen.model, SEEDS, k == 0) + (("extra",) if extra else ())
             for day in ex.PERIODS[CALIB_PERIOD].calibration for k, s in enumerate(specs)]
    echo(f"[{family}] {len(specs)} configurações × {len(ex.PERIODS[CALIB_PERIOD].calibration)} dias")
    rows = run_tasks(tasks, raw, workers, echo=echo)
    write_rows(RUNS / f"calibracao_{out_name or family}.csv", rows)
    summary = summarise(rows)
    best = choose(summary)
    stochastic = any(r["semente"] not in ("", None) for r in rows)
    if register:
        append_registry(summary, best["cenario"], "calibracao", ",".join(map(str, SEEDS)) if stochastic else "deterministico")
        cand = RESULTS / "calibracao" / f"{family}.json"
        cand.parent.mkdir(parents=True, exist_ok=True)
        cand.write_text(json.dumps({"familia": family, "codigo": git_head(), "finalista": best, "grade": summary},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    for s in sorted(summary, key=lambda s: s["km_vazio_por_corrida"]):
        echo(f"  {s['cenario']:<45} corridas {s['var_corridas_pct']:+6.2f}%  km vazio/corrida "
             f"{s['var_km_vazio_por_corrida_pct']:+6.2f}%  mov {s['movimentos_executados']:.0f}  t {s['tempo_plano_medio_s']:.2f}s"
             f"{'  <- finalista' if s['cenario'] == best['cenario'] else ''}")
    return best


def freeze(family: str) -> dict:
    """Copia o finalista da calibração para `resultados/finalistas.json` (antes de qualquer teste)."""
    cand = json.loads((RESULTS / "calibracao" / f"{family}.json").read_text(encoding="utf-8"))
    best = cand["finalista"]
    target = EXTRAS_JSON if family in EXTRA_FAMILIES else FINALISTS
    fin = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    fin[family] = {"cenario": best["cenario"], "parametros": json.loads(best["parametros"]),
                   "regra": best["regra"], "calibracao": {k: best[k] for k in (
                       "corridas_base", "corridas", "var_corridas_pct", "km_vazio_por_corrida_base",
                       "km_vazio_por_corrida", "var_km_vazio_por_corrida_pct", "tempo_plano_medio_s")},
                   "congelado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "codigo": git_head()}
    target.write_text(json.dumps(fin, ensure_ascii=False, indent=2), encoding="utf-8")
    return fin[family]


def calibration_report(family: str, note: str) -> str:
    """Relatório curto da calibração (tabela gerada do JSON gravado; a nota é o comentário do autor)."""
    cand = json.loads((RESULTS / "calibracao" / f"{family}.json").read_text(encoding="utf-8"))
    best = cand["finalista"]["cenario"]
    lines = [f"## {family}", "", f"Código `{cand['codigo']}`; calibração 2–15/03, regime B, 04–11h; "
             f"baseline {cand['grade'][0]['corridas_base']:.0f} corridas e "
             f"{cand['grade'][0]['km_vazio_por_corrida_base']:.3f} km vazios por corrida.", "",
             "| Configuração | Corridas (%) | KM vazio/corrida (%) | B/corrida | R/corrida | Mov. exec. | Dias com redução | Piso | Tempo (s/dia) |",
             "|---|---:|---:|---:|---:|---:|---:|:---:|---:|"]
    for s in sorted(cand["grade"], key=lambda s: s["km_vazio_por_corrida"]):
        mark = " **(finalista)**" if s["cenario"] == best else ""
        lines.append(f"| `{s['cenario']}`{mark} | {s['var_corridas_pct']:+.2f} | {s['var_km_vazio_por_corrida_pct']:+.2f} | "
                     f"{s['km_busca_por_corrida']:.3f} | {s['km_repos_por_corrida']:.3f} | {s['movimentos_executados']:.0f} | "
                     f"{s['dias_com_reducao']}/{s['dias']} | {'sim' if s['satisfaz_piso'] else 'não'} | {s['tempo_plano_medio_s']:.2f} |")
    lines += ["", note, ""]
    text = "\n".join(lines)
    path = RESULTS / "calibracao" / "RELATORIOS.md"
    head = "" if path.exists() else ("# Relatórios curtos de calibração (por família)\n\nGerados por "
                                     "`protocolo.calibration_report` a partir de `resultados/calibracao/<família>.json`. "
                                     "Estimativas de simulação; não são KM rodado nem economia observada.\n\n")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(head + text + "\n")
    return text


# ------------------------------------------------------------------ teste (parâmetros congelados)
MONTH_LABEL = {"mar2026": "marco", "set2026": "setembro"}
TEST_REGIMES = ("B", "A")


def assert_frozen_committed() -> None:
    """O teste só roda com `resultados/finalistas.json` versionado e igual ao último commit."""
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(FINALISTS)], capture_output=True).returncode == 0
    clean = not subprocess.run(["git", "status", "--porcelain", str(FINALISTS)], capture_output=True, text=True).stdout.strip()
    if not (tracked and clean):
        raise SystemExit("finalistas.json precisa estar commitado e sem alterações antes do teste")


def test_specs(families: list[str] | None = None) -> list[PlannerSpec]:
    from tcc_frota.algoritmos.bateria import reference_specs

    frozen = load_frozen()
    fin = load_finalists()
    specs = reference_specs(frozen.selection)
    specs += [PlannerSpec(f, f"fin_{f}", v["parametros"]) for f, v in fin.items()]
    if families:
        specs = [s for s in specs if s.family in families or s.name in families]
    return specs


def run_test(period: str, *, workers: int = 12, raw: Path = Path("data/raw"), families: list[str] | None = None,
             echo=print) -> Path:
    assert_frozen_committed()
    frozen = load_frozen()
    specs = test_specs(families)
    days_file = RESULTS / f"finalistas_{MONTH_LABEL[period]}_dias.csv"
    old = read_rows(days_file) if days_file.exists() else []
    names = {s.name for s in specs}
    keep = [r for r in old if r["cenario"] not in names]
    has_base = {(r["data"], r["regime"]) for r in keep if r["cenario"] == "sem_reposicionamento"}
    tasks = []
    for day in ex.PERIODS[period].test:
        for regime in TEST_REGIMES:
            for k, s in enumerate(specs):
                tasks.append((period, day, CALIB_WINDOW, regime, frozen.sims[period], [s], frozen.model, SEEDS,
                              k == 0 and (day.isoformat(), regime) not in has_base))
    echo(f"[teste {period}] {len(specs)} algoritmos × {len(ex.PERIODS[period].test)} dias × {len(TEST_REGIMES)} regimes")
    rows = keep + run_tasks(tasks, raw, workers, echo=echo)
    rows.sort(key=lambda r: (r["regime"], r["data"], r["cenario"], str(r["semente"])))
    write_rows(days_file, rows)
    return days_file


def analyse_test(period: str) -> list[dict]:
    from tcc_frota.algoritmos.estatistica import analyse, holm

    rows = read_rows(RESULTS / f"finalistas_{MONTH_LABEL[period]}_dias.csv")
    out = []
    for regime in TEST_REGIMES:
        sel = [r for r in rows if r["regime"] == regime]
        days = per_day(sel)
        scenarios = sorted({c for c, _ in days if c != "sem_reposicionamento"})
        m = len(scenarios)
        res = {}
        for scen in scenarios:
            pairs = paired(days, scen)
            res[scen] = {"periodo": period, "regime": regime, "cenario": scen, "familia": pairs[0]["p"]["familia"],
                         "parametros": pairs[0]["p"]["parametros"], "sementes_por_dia": pairs[0]["p"]["sementes"],
                         "m_comparacoes": m, **analyse(pairs, m)}
        adj = holm({k: v["p_km_vazio_por_corrida"] for k, v in res.items()})
        for k, v in res.items():
            v["p_km_vazio_por_corrida_holm"] = adj[k]
            out.append(v)
    write_rows(RESULTS / f"finalistas_{MONTH_LABEL[period]}.csv", out)
    return out


# ------------------------------------------------------------------ 5.6 busca NSGA-II (uma semente por processo)
def _nsga2_worker(args) -> dict:
    raw, seed = args
    import os

    os.environ.setdefault("TCC_REAL_DATA_AUTHORIZED", "YES")
    from tcc_frota.algoritmos import nsga2
    from tcc_frota.algoritmos.bateria import build_study

    started = datetime.now(timezone.utc)
    out = nsga2.search(build_study(Path(raw)), load_frozen(), seed)
    out["segundos"] = (datetime.now(timezone.utc) - started).total_seconds()
    return out


def nsga2_search(raw: Path = Path("data/raw"), seeds: tuple[int, ...] = SEEDS) -> dict:
    from multiprocessing import get_context

    with get_context("spawn").Pool(len(seeds)) as pool:
        results = pool.map(_nsga2_worker, [(str(raw), s) for s in seeds])
    rows = [r for res in results for r in res["avaliacoes"]]
    write_rows(RESULTS / "nsga2_avaliacoes_calibracao.csv", rows)
    busca = {"codigo": git_head(), "populacao": 20, "geracoes": 15,
             "finalistas": {str(r["semente"]): r["finalista"] for r in results},
             "regras": {str(r["semente"]): r["regra"] for r in results},
             "segundos": {str(r["semente"]): r["segundos"] for r in results}}
    (RESULTS / "calibracao").mkdir(parents=True, exist_ok=True)
    (RESULTS / "calibracao" / "nsga2_busca.json").write_text(json.dumps(busca, ensure_ascii=False, indent=2), encoding="utf-8")
    return busca
