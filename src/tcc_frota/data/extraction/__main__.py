"""CLI: python -m tcc_frota.data.extraction --fonte ods|es --entidade X --inicio AAAA-MM-DD --fim AAAA-MM-DD [--forcar]

Exige TCC_REAL_DATA_AUTHORIZED=YES (portão do proprietário). Somente leitura; saída local em data/raw/v1_viagens/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tcc_frota.data.extraction.entities import entidades_es, entidades_sql
from tcc_frota.data.extraction.filters import FiltroV1
from tcc_frota.data.extraction.runner import extrair_es, extrair_sql, gravar_campanha
from tcc_frota.data.extraction.writer import RAIZ_PADRAO


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tcc_frota.data.extraction", description=__doc__)
    p.add_argument("--fonte", choices=("ods", "es"), required=True)
    p.add_argument("--entidade", required=True)
    p.add_argument("--inicio", required=True)
    p.add_argument("--fim", required=True, help="inclusivo")
    p.add_argument("--saida", default=str(RAIZ_PADRAO))
    p.add_argument("--bloco-dias", type=int, default=1, help="lê N dias por consulta (só entidades com coluna_lote); lotes seguem diários")
    p.add_argument("--forcar", action="store_true", help="regrava lotes já prontos")
    a = p.parse_args(argv)
    f = FiltroV1()
    catalogo = entidades_sql(f) if a.fonte == "ods" else entidades_es()
    if a.entidade not in catalogo:
        print(f"entidade inválida para {a.fonte}: {sorted(catalogo)}", file=sys.stderr)
        return 2
    fn = extrair_sql if a.fonte == "ods" else extrair_es
    kw = {"bloco_dias": a.bloco_dias} if a.fonte == "ods" else {}
    res = fn(a.entidade, a.inicio, a.fim, filtro=f, raiz=Path(a.saida), forcar=a.forcar, **kw)
    gravar_campanha(Path(a.saida), vars(a), {f"{a.fonte}/{a.entidade}": res})
    for r in res:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
