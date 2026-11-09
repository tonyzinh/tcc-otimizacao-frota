"""Interface de linha de comando: ``tcc-frota <comando>``.

Comandos:
  run-synthetic       roda A, B e C em cenários sintéticos (sem dados privados) e grava Parquet por (cenário, semente);
  run-historical      roda A, B e C nos dias reais elegíveis (exige TCC_REAL_DATA_AUTHORIZED=YES e dados locais);
  analyze-synthetic   contrastes pareados por cenário (semente = unidade) com Holm nos confirmatórios;
  analyze-historical  totais e contrastes pareados por dia (C×A principal), critérios E1–E3 e tabelas Markdown;
  figures             gera as figuras do artigo a partir de resultados já calculados.

Resultados congelados (``reports/atribuicao_final``, ``reports/sintetico_v2``) NUNCA são sobrescritos: use outra pasta de saída.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FROZEN_DIRS = (Path("reports/atribuicao_final"), Path("reports/sintetico_v2"), Path("reports/tcc_final"))


def _refuse_frozen(out: Path) -> None:
    resolved = out.resolve()
    for frozen in FROZEN_DIRS:
        f = frozen.resolve()
        if resolved == f or f in resolved.parents:
            raise SystemExit(f"recusado: {out} está dentro de resultados congelados ({frozen}); use uma pasta nova")


def _parse_seeds(text: str) -> tuple[int, ...]:
    a, _, b = text.partition("-")
    return tuple(range(int(a), int(b) + 1)) if b else (int(a),)


def cmd_run_synthetic(args: argparse.Namespace) -> int:
    import pandas as pd

    from tcc_frota.scenarios import catalog
    from tcc_frota.scenarios import runner as rn

    out = Path(args.out)
    _refuse_frozen(out)
    out.mkdir(parents=True, exist_ok=True)
    ids = args.scenarios.split(",") if args.scenarios else list(catalog.PRINCIPAIS)
    seeds = _parse_seeds(args.seeds) if args.seeds else catalog.DEVELOPMENT_SEEDS[:3]
    world = rn.build_world()
    for sid in ids:
        for seed in seeds:
            target = out / f"cen={sid}__sem={seed}.parquet"
            if target.exists():
                print(f"{sid} {seed}: existente")
                continue
            rows = rn.run_pair(catalog.SCENARIOS_BY_ID[sid], seed, world)
            pd.DataFrame(rows).to_parquet(target, index=False)
            print(f"{sid} {seed}: ok")
    return 0


def cmd_run_historical(args: argparse.Namespace) -> int:
    from tcc_frota.data.authorization import authorize
    from tcc_frota.simulation import historical as hs

    authorize("real")
    out = Path(args.out)
    _refuse_frozen(out)
    days = args.days.split(",")
    folder = out / "grupo_B" / args.period
    for day in days:
        if (folder / f"dia={day}.parquet").exists():
            print(f"{day}: existente")
            continue
        hs.save_day(folder, day, hs.run_day(day))
        print(f"{day}: ok")
    hs.write_manifest(folder, hs.build_manifest(args.period, days, {"observacao": "execucao pelo codigo reorganizado"}))
    return 0


def cmd_analyze_synthetic(args: argparse.Namespace) -> int:
    from tcc_frota.metrics import synthetic as sy

    table = sy.summarize(sy.load_scenarios(args.input))
    out = Path(args.out)
    _refuse_frozen(out)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "resumo_contrastes.csv", index=False)
    print(table[["cenario", "politica", "referencia", "d_pct", "ic95_inf", "ic95_sup", "classe"]].to_string(index=False))
    return 0


def cmd_analyze_historical(args: argparse.Namespace) -> int:
    import pandas as pd

    from tcc_frota.metrics import historical as hi

    out = Path(args.out)
    _refuse_frozen(out)
    out.mkdir(parents=True, exist_ok=True)
    summary: dict = {}
    parts = ["# Resultados históricos por período (gerado por `tcc-frota analyze-historical`)\n"]
    for period, title in hi.PERIODS.items():
        folder = Path(args.input) / "grupo_B" / period
        if not folder.exists():
            continue
        df = hi.load_days(folder)
        totals = hi.absolute_totals(df)
        contrasts = pd.DataFrame([hi.paired_contrast(df, a, b, role) for a, b, role in hi.CONTRASTS])
        totals.to_csv(out / f"{period}_absolutos.csv", index=False)
        df.pivot(index="dia", columns="config", values="km_vazio_total").to_csv(out / f"{period}_km_vazio_por_dia.csv")
        contrasts.to_json(out / f"{period}_contrastes.json", orient="records", force_ascii=False, indent=1)
        summary[period] = {"absolutos": totals.to_dict("records"), "contrastes": contrasts.to_dict("records")}
        parts += [
            f"\n## {title}\n",
            hi.to_markdown(totals),
            "\n",
            hi.to_markdown(contrasts.drop(columns=[c for c in contrasts.columns if c.startswith("km_vazio_")])),
        ]
    (out / "resumo.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    (out / "tabelas.md").write_text("\n".join(parts), encoding="utf-8")
    print("\n".join(parts))
    return 0


def cmd_figures(args: argparse.Namespace) -> int:
    from tcc_frota.visualization import figures

    figures.make_all(Path(args.historical), Path(args.synthetic), Path(args.out))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tcc-frota", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("run-synthetic", help="roda A, B e C em cenários sintéticos")
    s.add_argument("--scenarios", help="ids separados por vírgula (padrão: S1–S5)")
    s.add_argument("--seeds", help="ex.: 101-105 (padrão: três primeiras sementes de desenvolvimento)")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_run_synthetic)

    s = sub.add_parser("run-historical", help="roda A, B e C nos dias reais (exige autorização)")
    s.add_argument("--period", required=True, choices=["replicacao", "final"])
    s.add_argument("--days", required=True, help="datas ISO separadas por vírgula")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_run_historical)

    s = sub.add_parser("analyze-synthetic", help="contrastes pareados do sintético")
    s.add_argument("--input", required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_analyze_synthetic)

    s = sub.add_parser("analyze-historical", help="totais e contrastes pareados dos dias reais")
    s.add_argument("--input", default="reports/atribuicao_final/execucao")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_analyze_historical)

    s = sub.add_parser("figures", help="figuras do artigo")
    s.add_argument("--historical", default="reports/atribuicao_final/analise")
    s.add_argument("--synthetic", default="reports/sintetico_v2/metodos_avaliacao_D/analise")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_figures)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
