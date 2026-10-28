"""Linha de comando da bateria: `python -m tcc_frota.algoritmos.cli <comando>`.

Comandos: `regressao` (referências contra o artigo), `calibrar <família>` (grade pré-registrada nos
dias 2–15/03) e `congelar <família>` (grava o finalista em `resultados/finalistas.json`).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tcc_frota.algoritmos.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    reg = sub.add_parser("regressao", help="referências pela interface Planner contra o final-run do artigo")
    reg.add_argument("--raw", type=Path, default=Path("data/raw"))
    reg.add_argument("--daily", type=Path, default=Path("reports/runs/tcc_final/20261016T013428Z/individual/dias_cenarios.csv"))
    cal = sub.add_parser("calibrar", help="roda a grade de uma família na calibração de março")
    cal.add_argument("familia")
    cal.add_argument("--workers", type=int, default=12)
    cal.add_argument("--raw", type=Path, default=Path("data/raw"))
    cal.add_argument("--sem-registro", action="store_true", help="não grava no registro (conferência)")
    cal.add_argument("--saida", default=None, help="nome alternativo do arquivo de linhas")
    frz = sub.add_parser("congelar", help="congela o finalista de uma família")
    frz.add_argument("familia")
    tst = sub.add_parser("testar", help="avalia finalistas e referências nos dias de teste de um período")
    tst.add_argument("periodo", choices=["mar2026", "set2026"])
    tst.add_argument("--workers", type=int, default=12)
    tst.add_argument("--raw", type=Path, default=Path("data/raw"))
    tst.add_argument("--familias", nargs="*", default=None)
    tx = sub.add_parser("testar-extra", help="5.9 intradiário, 5.11 D+0 e combinação (tabelas próprias)")
    tx.add_argument("periodo", choices=["mar2026", "set2026"])
    tx.add_argument("--workers", type=int, default=12)
    tx.add_argument("--raw", type=Path, default=Path("data/raw"))
    ana = sub.add_parser("analisar", help="estatística pareada, Holm e Bonferroni dos dias de teste")
    ana.add_argument("periodo", choices=["mar2026", "set2026"])
    ng = sub.add_parser("nsga2-busca", help="5.6: busca NSGA-II nos dias de calibração (uma semente por processo)")
    ng.add_argument("--raw", type=Path, default=Path("data/raw"))
    for name in ("seletivo-calibrar", "seletivo-variantes", "seletivo-congelar", "seletivo-relatorio"):
        sp = sub.add_parser(name, help="guloso seletivo (docs/ORCAMENTO_CONFIGURACOES.md §5)")
        sp.add_argument("--workers", type=int, default=10)
        sp.add_argument("--raw", type=Path, default=Path("data/raw"))
    for name in ("seletivo-testar", "seletivo-analisar"):
        sp = sub.add_parser(name, help="guloso seletivo: teste ou estatística de um período")
        sp.add_argument("periodo", choices=["mar2026", "set2026"])
        sp.add_argument("--workers", type=int, default=10)
        sp.add_argument("--raw", type=Path, default=Path("data/raw"))
    args = parser.parse_args(argv)
    if (
        args.command.startswith("seletivo-")
        and args.command not in ("seletivo-congelar", "seletivo-relatorio", "seletivo-analisar")
        and os.environ.get("TCC_REAL_DATA_AUTHORIZED") != "YES"
    ):
        print("defina TCC_REAL_DATA_AUTHORIZED=YES (processamento local autorizado, DT010-v2)", file=sys.stderr)
        return 2
    if args.command.startswith("seletivo-"):
        from tcc_frota.algoritmos import seletivo as sl

        if args.command == "seletivo-calibrar":
            out = sl.calibrate(args.workers, args.raw)
        elif args.command == "seletivo-variantes":
            out = sl.calibrate_variants(args.workers, args.raw)
        elif args.command == "seletivo-congelar":
            out = sl.freeze()
        elif args.command == "seletivo-testar":
            out = str(sl.run_test(args.periodo, args.workers, args.raw))
        elif args.command == "seletivo-analisar":
            out = sl.analyse(args.periodo)
            for r in out:
                print(
                    f"{r['regime']} {r['cenario']:<26} corridas {r['corridas_atendidas_var_pct']:+6.2f}% "
                    f"[{r['corridas_atendidas_var_pct_ic_inf']:+.2f}; {r['corridas_atendidas_var_pct_ic_sup']:+.2f}]  "
                    f"km vazio/corrida {r['km_vazio_por_corrida_var_pct']:+6.2f}% "
                    f"[{r['km_vazio_por_corrida_var_pct_ic_inf']:+.2f}; {r['km_vazio_por_corrida_var_pct_ic_sup']:+.2f}]  "
                    f"p_holm {r['p_km_vazio_por_corrida_holm']:.3f}"
                )
            return 0
        else:
            out = {"motivos": sl.reasons_table(), "pareto": str(sl.pareto())}
        print(json.dumps(out, ensure_ascii=False, default=str)[:3000])
        return 0
    if args.command == "congelar":
        from tcc_frota.algoritmos.protocolo import freeze

        print(json.dumps(freeze(args.familia), ensure_ascii=False, indent=2))
        return 0
    if args.command == "analisar":
        from tcc_frota.algoritmos.protocolo import analyse_test

        for r in analyse_test(args.periodo):
            print(
                f"{r['regime']} {r['cenario']:<28} corridas {r['corridas_atendidas_var_pct']:+6.2f}% "
                f"[{r['corridas_atendidas_var_pct_ic_inf']:+.2f}; {r['corridas_atendidas_var_pct_ic_sup']:+.2f}]  "
                f"km vazio/corrida {r['km_vazio_por_corrida_var_pct']:+6.2f}% "
                f"[{r['km_vazio_por_corrida_var_pct_ic_inf']:+.2f}; {r['km_vazio_por_corrida_var_pct_ic_sup']:+.2f}]  "
                f"p_holm {r['p_km_vazio_por_corrida_holm']:.3f}"
            )
        return 0
    if os.environ.get("TCC_REAL_DATA_AUTHORIZED") != "YES":
        print("defina TCC_REAL_DATA_AUTHORIZED=YES (processamento local autorizado, DT010-v2)", file=sys.stderr)
        return 2
    if args.command == "regressao":
        from tcc_frota.algoritmos import regressao
        from tcc_frota.algoritmos.bateria import build_study, load_frozen
        from tcc_frota.v2 import experiment as ex

        study = build_study(args.raw)
        frozen = load_frozen()
        sims = {}
        for name, period in ex.PERIODS.items():
            sims[name], _ = ex.calibrate_simulator(study, period, study.measured_parameters(period.calibration), echo=lambda *a: None)
        same_sim = all(sims[k] == frozen.sims[k] for k in sims)
        print(f"simulador recalibrado igual ao congelado: {same_sim}")
        out = regressao.run(study, args.daily)
        print(json.dumps({"simulador_igual": same_sim, **out}))
        return 0 if same_sim and out["divergencias"] == 0 else 1
    if args.command == "testar":
        from tcc_frota.algoritmos.protocolo import run_test

        print(run_test(args.periodo, workers=args.workers, raw=args.raw, families=args.familias))
        return 0
    if args.command == "testar-extra":
        from tcc_frota.algoritmos.protocolo import run_test_extra

        print(run_test_extra(args.periodo, workers=args.workers, raw=args.raw))
        return 0
    if args.command == "nsga2-busca":
        from tcc_frota.algoritmos.protocolo import nsga2_search

        print(json.dumps(nsga2_search(args.raw), ensure_ascii=False, default=str)[:2000])
        return 0
    if args.command == "calibrar":
        from tcc_frota.algoritmos.protocolo import calibrate

        best = calibrate(args.familia, workers=args.workers, raw=args.raw, register=not args.sem_registro, out_name=args.saida)
        print(json.dumps(best, ensure_ascii=False, default=str))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
