# Databricks notebook source
# MAGIC %md
# MAGIC # tb_bro_historico_v2
# MAGIC
# MAGIC Páginas `hist_<tag>_pNN.json` (índice `indexsolicitacaohistorico`). `distMotorista` em metros e
# MAGIC `etaMotorista` em segundos, conforme o extrator.

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,Esquema e gravação
SCHEMA_HIST = T.StructType(
    [T.StructField(c, T.LongType()) for c in ("codigo", "etaMotorista", "distMotorista", "idMotorista")]
    + [T.StructField(c, T.StringType()) for c in (
        "dataRegistro", "origemLat", "origemLng", "status", "destinoLat", "destinoLong")])
n = gravar(ler_paginas("hist", SCHEMA_HIST), f"{BRONZE}.tb_bro_historico_v2",
           "Bronze v2: _source de indexsolicitacaohistorico por página")
print({"tabela": "tb_bro_historico_v2", "linhas": n})
