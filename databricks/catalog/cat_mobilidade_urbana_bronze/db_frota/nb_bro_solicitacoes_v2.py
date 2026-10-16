# Databricks notebook source
# MAGIC %md
# MAGIC # tb_bro_solicitacoes_v2
# MAGIC
# MAGIC Páginas `req_<tag>_pNN.json` (índice `indexsolicitacaodetalhe`) dos quatro lotes. Esquema explícito,
# MAGIC sem regra de negócio. Coordenadas brutas ficam apenas nesta camada.

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,Esquema explícito do _source
LOG = T.ArrayType(T.StructType([T.StructField("dT_REGISTRO", T.StringType()),
                                T.StructField("tX_STATUS", T.StringType())]))
IV = T.StructType([T.StructField("nU_IV_VALUE", T.DoubleType()), T.StructField("nU_IV_DP", T.DoubleType()),
                   T.StructField("nU_IV_DR", T.DoubleType()), T.StructField("tX_IV_H3INDEX_DESTINO", T.StringType())])
SCHEMA_REQ = T.StructType(
    [T.StructField(c, T.LongType()) for c in (
        "codigo", "cD_AGENDAMENTO", "cD_REGIAO", "cD_TIPO_SERVICO", "cD_MOTORISTA", "cD_VEICULO",
        "nU_DISTPERCORRIDA", "tX_DURACAO", "nU_DR_REAL")]
    + [T.StructField(c, T.StringType()) for c in (
        "dT_REGISTRO", "dT_AGENDAMENTO", "dT_ACEITE_MOTORISTA", "dT_CHEGADA_MOTORISTA", "dT_INICIO_REALIZADA",
        "dT_FIM_REALIZADA", "tX_STATUS", "tX_TP_SOLICITACAO", "tX_ORIGEM_LAT", "tX_ORIGEM_LNG", "tX_DESTINO_LAT",
        "tX_DESTINO_LNG", "tX_DESTINOREAL_LAT", "tX_DESTINOREAL_LNG", "tX_H3INDEX_REPOSICIONAMENTO_REAL")]
    + [T.StructField("logStatus", LOG), T.StructField("indiceViabilidade", IV)])

# COMMAND ----------

# DBTITLE 1,Gravação
n = gravar(ler_paginas("req", SCHEMA_REQ), f"{BRONZE}.tb_bro_solicitacoes_v2",
           "Bronze v2: _source de indexsolicitacaodetalhe por página, sem regra de negócio")
print({"tabela": "tb_bro_solicitacoes_v2", "linhas": n})
