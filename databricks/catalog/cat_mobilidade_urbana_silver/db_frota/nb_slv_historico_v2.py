# Databricks notebook source
# MAGIC %md
# MAGIC # tb_slv_historico_v2
# MAGIC
# MAGIC `distMotorista` em metros e `etaMotorista` em segundos; motorista pseudonimizado; origem com 3 casas.

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,Tipagem e gravação
sal = sal_pseudonimo()
h = spark.table(f"{BRONZE}.tb_bro_historico_v2").select(
    F.col("codigo").cast("bigint").alias("codigo"), "status",
    ts("dataRegistro").alias("ts_registro"),
    F.col("distMotorista").alias("dist_motorista_m"), F.col("etaMotorista").alias("eta_motorista_s"),
    pseudonimo("idMotorista", sal).alias("motorista_pseud"),
    F.round(F.col("origemLat").cast("double"), 3).alias("lat_origem"),
    F.round(F.col("origemLng").cast("double"), 3).alias("lon_origem"))
print({"tb_slv_historico_v2": gravar(h, f"{SILVER}.tb_slv_historico_v2", "Silver v2: histórico de despacho")})
