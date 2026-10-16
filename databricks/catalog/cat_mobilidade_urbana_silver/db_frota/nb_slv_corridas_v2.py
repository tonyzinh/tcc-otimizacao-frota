# Databricks notebook source
# MAGIC %md
# MAGIC # tb_slv_corridas_v2
# MAGIC
# MAGIC Corridas encerradas com aceite, chegada, início e fim. KM de busca estimado = Haversine entre a última
# MAGIC foto do motorista livre/selecionado até 10 min antes do aceite e a origem, × fator rua/reta
# MAGIC (parâmetro `FATOR_RUA_RETA`, calibrado na Gold). É estimativa, nunca odômetro (RN012).

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,As-of join com a foto anterior ao aceite
FATOR_RUA_RETA = 1.42
sol = spark.table(f"{SILVER}.tb_slv_solicitacoes_v2").where("status = 'CorridaEncerrada'")
pos = (spark.table(f"{SILVER}.tb_slv_posicoes_motoristas_v2").where("fl_coordenada_valida")
       .select("motorista_pseud", "ts_snapshot", "estado", F.col("lat").alias("lat_foto"), F.col("lon").alias("lon_foto")))
cand = (sol.select("codigo", "motorista_pseud", "ts_aceite").join(pos, "motorista_pseud")
        .where((F.col("ts_snapshot") <= F.col("ts_aceite"))
               & (F.col("ts_aceite").cast("double") - F.col("ts_snapshot").cast("double") <= 600)))
ultima = (cand.withColumn("_r", F.row_number().over(W.partitionBy("codigo").orderBy(F.desc("ts_snapshot"))))
          .where("_r = 1 AND estado IN (1, 4)").select("codigo", "lat_foto", "lon_foto"))
c = (sol.join(ultima, "codigo", "left")
     .withColumn("km_busca_reta_foto", haversine_km(F.col("lat_foto"), F.col("lon_foto"), F.col("lat_origem"), F.col("lon_origem")))
     .withColumn("km_busca_estimado", F.col("km_busca_reta_foto") * F.lit(FATOR_RUA_RETA))
     .select("codigo", "motorista_pseud", "fl_imediata", "data_base", "ts_aceite", "ts_chegada", "ts_inicio", "ts_fim",
             "fl_tempos_ordenados", "km_busca_reta_foto", "km_busca_estimado", "dist_percorrida_km", "dur_viagem_s"))
print({"tb_slv_corridas_v2": gravar(c, f"{SILVER}.tb_slv_corridas_v2", "Silver v2: corridas encerradas com KM de busca estimado")})
