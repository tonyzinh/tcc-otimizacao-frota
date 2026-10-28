"""Conferências do guloso seletivo: (1) recalibração do zero de uma configuração (a que mais moveu) e comparação
com o registro; (2) C2 nos dias de teste (regime B) com 5 sementes novas. Saída: resultados/seletivo/conferencia.json."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from tcc_frota.algoritmos import seletivo as sl
from tcc_frota.algoritmos.bateria import load_frozen, run_tasks
from tcc_frota.algoritmos.estatistica import analyse
from tcc_frota.algoritmos.protocolo import paired, per_day
from tcc_frota.v2 import experiment as ex

if __name__ == "__main__":
    os.environ.setdefault("TCC_REAL_DATA_AUTHORIZED", "YES")
    spec = next(s for s in sl.grid() if s.name == "C2|H4|K8|tau1")
    _, summary = sl._calibrate([spec], "reexecucao_C2_H4_K8_tau1", 10, Path("data/raw"), print)
    old = next(r for r in csv.DictReader(open("resultados/registro_configuracoes.csv", encoding="utf-8")) if r["cenario"] == spec.name)
    new = summary[0]
    recal = {
        "configuracao": spec.name,
        "corridas_registro": float(old["corridas"]),
        "corridas_reexecucao": new["corridas"],
        "km_vazio_por_corrida_registro": float(old["km_vazio_por_corrida"]),
        "km_vazio_por_corrida_reexecucao": new["km_vazio_por_corrida"],
        "movimentos_registro": float(old["movimentos_executados"]),
        "movimentos_reexecucao": new["movimentos_executados"],
    }
    print(recal)
    frozen = load_frozen()
    fin = json.loads(sl.FINALISTS.read_text(encoding="utf-8"))
    from tcc_frota.algoritmos.base import PlannerSpec

    c2 = PlannerSpec("guloso_seletivo", "C2_guloso_seletivo", fin["C2"]["parametros"])
    seeds = []
    for period in ex.PERIODS:
        tasks = [
            (period, d, "04-11", "B", frozen.sims[period], [c2], frozen.model, (61, 67, 71, 73, 79), True) for d in ex.PERIODS[period].test
        ]
        days = per_day(run_tasks(tasks, Path("data/raw"), 10))
        r = analyse(paired(days, c2.name), 1)
        seeds.append(
            {
                "periodo": period,
                "sementes": "61,67,71,73,79",
                "movimentos_executados": r["soma_prop_moves_executed"],
                **{
                    k: r[k]
                    for k in (
                        "corridas_atendidas_var_pct",
                        "km_vazio_por_corrida_var_pct",
                        "km_vazio_por_corrida_var_pct_ic_inf",
                        "km_vazio_por_corrida_var_pct_ic_sup",
                    )
                },
            }
        )
        print(seeds[-1])
    Path("resultados/seletivo/conferencia.json").write_text(
        json.dumps({"recalibracao": recal, "novas_sementes": seeds}, indent=2, default=str), encoding="utf-8"
    )
