# Databricks notebook source
# MAGIC %md
# MAGIC # tb_slv_dormida_v2
# MAGIC
# MAGIC Última posição válida de cada motorista no dia D (estados de trabalho 1/3/4) e primeira de D+1.
# MAGIC Base do regime B (escala conhecida, posição inicial = última posição de D).

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,Última de D e primeira de D+1
pos = (spark.table(f"{SILVER}.tb_slv_posicoes_motoristas_v2")
       .where("fl_coordenada_valida AND estado IN (1, 3, 4) AND motorista_pseud IS NOT NULL")
       .withColumn("data_local", F.to_date("ts_snapshot")))
ult = (pos.withColumn("_r", F.row_number().over(W.partitionBy("motorista_pseud", "data_local").orderBy(F.desc("ts_snapshot"))))
       .where("_r = 1").select("motorista_pseud", "data_local", F.col("ts_snapshot").alias("ts_ultima"),
                               F.col("lat").alias("lat_ultima"), F.col("lon").alias("lon_ultima"),
                               F.col("h3_r7").alias("h3_r7_ultima")))
pri = (pos.withColumn("_r", F.row_number().over(W.partitionBy("motorista_pseud", "data_local").orderBy("ts_snapshot")))
       .where("_r = 1").select("motorista_pseud", F.date_sub("data_local", 1).alias("data_local"),
                               F.col("ts_snapshot").alias("ts_primeira_dia_seguinte"),
                               F.col("lat").alias("lat_primeira_dia_seguinte"),
                               F.col("lon").alias("lon_primeira_dia_seguinte")))
d = (ult.join(pri, ["motorista_pseud", "data_local"], "left")
     .withColumn("km_reta_dormida", haversine_km(F.col("lat_ultima"), F.col("lon_ultima"),
                                                 F.col("lat_primeira_dia_seguinte"), F.col("lon_primeira_dia_seguinte"))))
print({"tb_slv_dormida_v2": gravar(d, f"{SILVER}.tb_slv_dormida_v2", "Silver v2: última posição de D e primeira de D+1")})
