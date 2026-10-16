"""Segunda checagem: reexecuta os finalistas estocásticos em regime B com 5 sementes novas (61, 67, 71, 73, 79)
nos dias de teste dos dois meses e compara com as sementes originais. Saída: resultados/reexecucao_sementes.csv."""
from __future__ import annotations

import os
from pathlib import Path

from tcc_frota.algoritmos.bateria import load_frozen, run_tasks
from tcc_frota.algoritmos.estatistica import analyse
from tcc_frota.algoritmos.protocolo import RESULTS, paired, per_day, test_specs, write_rows
from tcc_frota.v2 import experiment as ex

NEW_SEEDS = (61, 67, 71, 73, 79)
STOCHASTIC = ["busca_local", "recozimento", "pso", "robusto_cenarios", "nsga2"]

if __name__ == "__main__":
    os.environ.setdefault("TCC_REAL_DATA_AUTHORIZED", "YES")
    frozen = load_frozen()
    specs = [s for s in test_specs(STOCHASTIC) if s.family != "nsga2"]   # NSGA-II: finalistas presos às sementes originais
    out = []
    for period in ex.PERIODS:
        tasks = [(period, d, ex.MAIN_WINDOW, "B", frozen.sims[period], [s], frozen.model, NEW_SEEDS, k == 0)
                 for d in ex.PERIODS[period].test for k, s in enumerate(specs)]
        days = per_day(run_tasks(tasks, Path("data/raw"), 10))
        for s in specs:
            r = analyse(paired(days, s.name), 1)
            out.append({"periodo": period, "cenario": s.name, "sementes": ",".join(map(str, NEW_SEEDS)),
                        **{k: r[k] for k in ("corridas_atendidas_var_pct", "corridas_atendidas_var_pct_ic_inf",
                                             "corridas_atendidas_var_pct_ic_sup", "km_vazio_por_corrida_var_pct",
                                             "km_vazio_por_corrida_var_pct_ic_inf", "km_vazio_por_corrida_var_pct_ic_sup",
                                             "dias_com_reducao", "dias")}})
            print(out[-1])
    write_rows(RESULTS / "reexecucao_sementes.csv", out)
