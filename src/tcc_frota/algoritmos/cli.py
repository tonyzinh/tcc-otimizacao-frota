"""Linha de comando da bateria: `python -m tcc_frota.algoritmos.cli <comando>`.

Comandos: `regressao` (referências contra o artigo). Os demais comandos (calibração, congelamento,
teste e relatório) ficam em `protocolo.py`.
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
    args = parser.parse_args(argv)
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
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
