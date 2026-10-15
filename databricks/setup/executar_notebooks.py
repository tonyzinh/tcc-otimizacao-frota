"""Executa notebooks Silver/Gold no serverless do Databricks via Databricks Connect.

Uso (na raiz do repositório, com o ambiente `.venv` do Databricks Connect):

    python databricks/setup/executar_notebooks.py silver gold
    python databricks/setup/executar_notebooks.py databricks/catalog/.../nb_slv_corridas.ipynb

O perfil vem de DATABRICKS_CONFIG_PROFILE (padrão do `.databrickscfg`). As células
rodam em ordem num namespace por notebook; a sessão Spark é compartilhada. Nenhum dado é
baixado para a máquina local: as escritas acontecem nas tabelas Delta do workspace.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2] / "databricks" / "catalog"
ORDEM = {
    "silver": [
        "cat_mobilidade_urbana_silver/db_frota/nb_slv_solicitacoes.ipynb",
        "cat_mobilidade_urbana_silver/db_frota/nb_slv_posicoes_motoristas.ipynb",
        "cat_mobilidade_urbana_silver/db_frota/nb_slv_sumarios.ipynb",
        "cat_mobilidade_urbana_silver/db_frota/nb_slv_corridas.ipynb",
    ],
    "gold": [
        "cat_mobilidade_urbana_gold/db_frota/nb_gld_demanda.ipynb",
        "cat_mobilidade_urbana_gold/db_frota/nb_gld_frota.ipynb",
        "cat_mobilidade_urbana_gold/db_frota/nb_gld_km_vazio.ipynb",
        "cat_mobilidade_urbana_gold/db_frota/nb_gld_qualidade.ipynb",
    ],
}


def notebooks(argumentos: list[str]) -> list[Path]:
    caminhos: list[Path] = []
    for arg in argumentos:
        caminhos += [RAIZ / p for p in ORDEM[arg]] if arg in ORDEM else [Path(arg).resolve()]
    return caminhos


def executar(caminho: Path, spark) -> None:
    nb = json.loads(caminho.read_text(encoding="utf-8"))
    escopo = {"spark": spark, "__name__": "__main__"}
    print(f"\n=== {caminho.name}", flush=True)
    for i, celula in enumerate(nb["cells"]):
        if celula["cell_type"] != "code":
            continue
        titulo = celula["metadata"].get("application/vnd.databricks.v1+cell", {}).get("title") or f"célula {i}"
        inicio = time.time()
        print(f"--- {titulo}", flush=True)
        exec(compile("".join(celula["source"]), f"{caminho.name}[{i}]", "exec"), escopo)
        print(f"    ({time.time() - inicio:.0f} s)", flush=True)


def main() -> None:
    alvos = notebooks(sys.argv[1:] or ["silver", "gold"])
    from databricks.connect import DatabricksSession

    spark = DatabricksSession.builder.serverless(True).getOrCreate()
    for caminho in alvos:
        executar(caminho, spark)


if __name__ == "__main__":
    main()
