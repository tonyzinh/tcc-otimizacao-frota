# Databricks notebook source
# MAGIC %md
# MAGIC # tb_bro_sumarios_v2
# MAGIC
# MAGIC Sumários da frota a cada 2 min (`sum_<tag>_pNN.json`, índice `indexsumarioofertamotorista`).

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,Esquema e gravação
SCHEMA_SUM = T.StructType(
    [T.StructField("codigo", T.StringType()), T.StructField("dataHora", T.StringType()),
     T.StructField("codigoRegiao", T.IntegerType())]
    + [T.StructField(c, T.IntegerType()) for c in (
        "qtdOnline", "qtdOffline", "qtdACaminho", "qtdComPassageiro", "qtdAproveitamento", "qtdSelecionado",
        "qtdIndisponivel")])
n = gravar(ler_paginas("sum", SCHEMA_SUM), f"{BRONZE}.tb_bro_sumarios_v2",
           "Bronze v2: sumários da frota a cada 2 min")
print({"tabela": "tb_bro_sumarios_v2", "linhas": n})
