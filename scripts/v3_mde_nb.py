"""MDE de NB(e*) para F1 e F4 (tabelas diárias agregadas; sem dados individuais)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if __name__ == "__main__":
    from tcc_frota.v3 import mde_nb

    print(
        json.dumps(
            mde_nb.run(
                ROOT / "reports/runs/tcc_final/20261016T013428Z/individual/dias_cenarios.csv",
                ROOT / "reports/tcc_final/tab11_principal.csv",
                ROOT / "reports/tcc_v2/fase4_dias.csv",
                ROOT / "reports/tcc_v2",
            ),
            indent=1,
        )
    )
