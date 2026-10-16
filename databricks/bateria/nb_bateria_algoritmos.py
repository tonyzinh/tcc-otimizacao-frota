# Databricks notebook source
# MAGIC %md
# MAGIC # Bateria de algoritmos de reposicionamento D+1
# MAGIC **Não executado no workspace.** A bateria foi executada localmente (`scripts/bateria_algoritmos.ps1`).
# MAGIC Este notebook reproduz os mesmos comandos sobre os extratos já autorizados no Volume `raw_v2`
# MAGIC (DT010-v2). Requer o pacote `tcc_frota` instalado no cluster (wheel do repositório) e o sal em
# MAGIC `tcc_frota/sal_pseudonimo`. Não grava dados individuais fora de `/tmp`; só agregados vão para `resultados/`.

# COMMAND ----------
import os
import subprocess
import sys

RAW = "/Volumes/cat_mobilidade_urbana_bronze/db_frota/raw_v2"
os.environ["TCC_REAL_DATA_AUTHORIZED"] = "YES"
os.environ["TCC_PSEUDO_SALT"] = dbutils.secrets.get("tcc_frota", "sal_pseudonimo")  # noqa: F821


def cli(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "tcc_frota.algoritmos.cli", *args], check=True)

# COMMAND ----------
cli("regressao", "--raw", RAW)

# COMMAND ----------
for family in ("fluxo_custo_minimo", "hungaro", "milp", "busca_local", "recozimento", "pso", "robusto_cenarios"):
    cli("calibrar", family, "--raw", RAW, "--workers", "4")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Guloso seletivo (não executado no workspace)

# COMMAND ----------
cli("seletivo-calibrar", "--raw", RAW, "--workers", "4")
cli("seletivo-variantes", "--raw", RAW, "--workers", "4")
