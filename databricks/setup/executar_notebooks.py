"""Executa notebooks do medalhão no serverless do Databricks via Databricks Connect.

Uso (na raiz do repositório, com o ambiente `.venv` do Databricks Connect):

    python databricks/setup/executar_notebooks.py bronze silver gold        # v2 (padrão)
    python databricks/setup/executar_notebooks.py silver_legado gold_legado  # notebooks legados (.ipynb)
    python databricks/setup/executar_notebooks.py databricks/catalog/.../nb_slv_corridas_v2.py

O perfil vem de DATABRICKS_CONFIG_PROFILE (padrão do `.databrickscfg`). Aceita `.ipynb` e notebooks
fonte `.py` (`# COMMAND ----------`, `# DBTITLE`, `# MAGIC %run <caminho relativo>`). As células rodam
em ordem num namespace por notebook; a sessão Spark é compartilhada. Nenhum dado é baixado para a
máquina local: as escritas acontecem nas tabelas Delta do workspace.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2] / "databricks" / "catalog"
BRO = "cat_mobilidade_urbana_bronze/db_frota/"
SLV = "cat_mobilidade_urbana_silver/db_frota/"
GLD = "cat_mobilidade_urbana_gold/db_frota/"
ORDEM = {
    "bronze": [BRO + n for n in ("nb_bro_solicitacoes_v2.py", "nb_bro_historico_v2.py",
                                 "nb_bro_ofertas_snapshot_v2.py", "nb_bro_sumarios_v2.py",
                                 "nb_bro_conferencia_v2.py")],
    "silver": [SLV + n for n in ("nb_slv_solicitacoes_v2.py", "nb_slv_historico_v2.py",
                                 "nb_slv_posicoes_motoristas_v2.py", "nb_slv_sumarios_v2.py",
                                 "nb_slv_dormida_v2.py", "nb_slv_corridas_v2.py")],
    "gold": [GLD + n for n in ("nb_gld_replay_pedidos_v2.py", "nb_gld_frota_v2.py", "nb_gld_calibracao_v2.py",
                               "nb_gld_km_vazio_v2.py", "nb_gld_qualidade_v2.py")],
    "silver_legado": [SLV + n for n in ("nb_slv_solicitacoes.ipynb", "nb_slv_posicoes_motoristas.ipynb",
                                        "nb_slv_sumarios.ipynb", "nb_slv_corridas.ipynb")],
    "gold_legado": [GLD + n for n in ("nb_gld_demanda.ipynb", "nb_gld_frota.ipynb", "nb_gld_km_vazio.ipynb",
                                      "nb_gld_qualidade.ipynb")],
}


def notebooks(argumentos: list[str]) -> list[Path]:
    caminhos: list[Path] = []
    for arg in argumentos:
        caminhos += [RAIZ / p for p in ORDEM[arg]] if arg in ORDEM else [Path(arg).resolve()]
    return caminhos


def celulas(caminho: Path) -> list[tuple[str, str]]:
    """(título, código) de cada célula de código; `%run` vira a pseudo-célula ('%run', caminho)."""
    if caminho.suffix == ".ipynb":
        nb = json.loads(caminho.read_text(encoding="utf-8"))
        out = []
        for i, celula in enumerate(nb["cells"]):
            if celula["cell_type"] == "code":
                titulo = celula["metadata"].get("application/vnd.databricks.v1+cell", {}).get("title") or f"célula {i}"
                out.append((titulo, "".join(celula["source"])))
        return out
    texto = caminho.read_text(encoding="utf-8").replace("# Databricks notebook source\n", "", 1)
    out = []
    for i, bloco in enumerate(texto.split("\n# COMMAND ----------\n")):
        linhas = [l for l in bloco.strip("\n").splitlines()]
        magicas = [l for l in linhas if l.startswith("# MAGIC")]
        run = next((m.group(1) for l in magicas if (m := re.match(r"^# MAGIC %run (\S+)\s*$", l))), None)
        if run:
            out.append(("%run", str((caminho.parent / run).resolve()) + ".py"))
            continue
        if linhas and len(magicas) == len([l for l in linhas if l.strip()]):
            continue  # célula markdown
        titulo = next((l.split(",", 1)[1] for l in linhas if l.startswith("# DBTITLE")), f"célula {i}")
        out.append((titulo, "\n".join(linhas)))
    return out


def executar(caminho: Path, spark, escopo: dict | None = None) -> None:
    escopo = escopo if escopo is not None else {"spark": spark, "__name__": "__main__"}
    print(f"\n=== {caminho.name}", flush=True)
    for titulo, codigo in celulas(caminho):
        if titulo == "%run":
            executar(Path(codigo), spark, escopo)
            continue
        inicio = time.time()
        print(f"--- {titulo}", flush=True)
        exec(compile(codigo, f"{caminho.name}[{titulo}]", "exec"), escopo)
        print(f"    ({time.time() - inicio:.0f} s)", flush=True)


def main() -> None:
    alvos = notebooks(sys.argv[1:] or ["bronze", "silver", "gold"])
    from databricks.connect import DatabricksSession

    spark = DatabricksSession.builder.serverless(True).getOrCreate()
    for caminho in alvos:
        executar(caminho, spark)


if __name__ == "__main__":
    main()
