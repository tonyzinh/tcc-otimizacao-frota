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
    reg.add_argument("--daily", type=Path,
                     default=Path("reports/runs/tcc_final/20261016T013428Z/individual/dias_cenarios.csv"))
    cal = sub.add_parser("calibrar", help="roda a grade de uma família na calibração de março")
    cal.add_argument("familia")
    cal.add_argument("--workers", type=int, default=12)
    cal.add_argument("--raw", type=Path, default=Path("data/raw"))
    cal.add_argument("--sem-registro", action="store_true", help="não grava no registro (conferência)")
    cal.add_argument("--saida", default=None, help="nome alternativo do arquivo de linhas")
    frz = sub.add_parser("congelar", help="congela o finalista de uma família")
    frz.add_argument("familia")
    args = parser.parse_args(argv)
    if args.command == "congelar":
        from tcc_frota.algoritmos.protocolo import freeze

        print(json.dumps(freeze(args.familia), ensure_ascii=False, indent=2))
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
            sims[name], _ = ex.calibrate_simulator(study, period, study.measured_parameters(period.calibration),
                                                   echo=lambda *a: None)
        same_sim = all(sims[k] == frozen.sims[k] for k in sims)
        print(f"simulador recalibrado igual ao congelado: {same_sim}")
        out = regressao.run(study, args.daily)
        print(json.dumps({"simulador_igual": same_sim, **out}))
        return 0 if same_sim and out["divergencias"] == 0 else 1
    if args.command == "calibrar":
        from tcc_frota.algoritmos.protocolo import calibrate

        best = calibrate(args.familia, workers=args.workers, raw=args.raw, register=not args.sem_registro,
                         out_name=args.saida)
        print(json.dumps(best, ensure_ascii=False, default=str))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
