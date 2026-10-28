"""Controle positivo/negativos sintéticos da v2 (D12/D13). Mundo 100% sintético: não usa dados reais."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if __name__ == "__main__":
    from tcc_frota.v3 import fase2_controle

    print(json.dumps(fase2_controle.run(ROOT / "reports/tcc_v2"), indent=2, ensure_ascii=False))
