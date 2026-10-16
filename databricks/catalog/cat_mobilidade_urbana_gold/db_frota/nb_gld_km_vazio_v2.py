# Databricks notebook source
# MAGIC %md
# MAGIC # tb_gld_km_vazio_v2
# MAGIC
# MAGIC Descritivo diário das imediatas encerradas: KM de busca estimado (reta da foto × fator) e KM com
# MAGIC passageiro registrado, em colunas separadas (DT003 aberta; RN010–RN012). Não é KPI corporativo.

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,Agregação diária
c = spark.table(f"{SILVER}.tb_slv_corridas_v2").where("fl_imediata AND data_base IS NOT NULL")
k = (c.groupBy(F.col("data_base").alias("data_local"))
     .agg(F.count("*").alias("corridas_encerradas"),
          F.count("km_busca_estimado").alias("corridas_com_km_busca"),
          F.sum("km_busca_estimado").alias("km_busca_estimado"),
          F.sum("dist_percorrida_km").alias("km_com_passageiro_registrado"))
     .withColumn("parcela_busca", F.lit("estimada: reta da foto x fator")))
print({"tb_gld_km_vazio_v2": gravar(k, f"{GOLD}.tb_gld_km_vazio_v2", "Gold v2: parcelas de KM por dia, descritivo")})
