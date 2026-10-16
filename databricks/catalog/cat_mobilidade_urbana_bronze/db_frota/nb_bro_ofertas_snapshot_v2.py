# Databricks notebook source
# MAGIC %md
# MAGIC # tb_bro_ofertas_snapshot_v2
# MAGIC
# MAGIC Fotos da frota a cada 10 min (`snap_<tag>_pNN.json`): uma linha por foto, com `ofertaList` como array
# MAGIC (um item por motorista online). A explosão por motorista fica na Silver.

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,Esquema e gravação
OFERTA = T.StructType([
    T.StructField("codigo", T.LongType()), T.StructField("status", T.IntegerType()),
    T.StructField("accuracy", T.DoubleType()), T.StructField("latitude", T.DoubleType()),
    T.StructField("longitude", T.DoubleType()), T.StructField("h3Index", T.StringType()),
    T.StructField("dataAtualizacao", T.StringType()), T.StructField("passageiroEmbarcado", T.BooleanType()),
    T.StructField("dataPosicaoGPS", T.StringType()), T.StructField("codigoSolicitacao", T.LongType()),
    T.StructField("distanciaRestante", T.LongType()), T.StructField("tempoSegundosViagemRestante", T.LongType()),
])
SCHEMA_SNAP = T.StructType([
    T.StructField("codigo", T.StringType()), T.StructField("codigoRegiao", T.IntegerType()),
    T.StructField("dataHora", T.StringType()), T.StructField("ofertaList", T.ArrayType(OFERTA)),
])
n = gravar(ler_paginas("snap", SCHEMA_SNAP), f"{BRONZE}.tb_bro_ofertas_snapshot_v2",
           "Bronze v2: fotos da frota (indexofertamotoristaelasticmodel), ofertaList como array")
print({"tabela": "tb_bro_ofertas_snapshot_v2", "linhas": n})
