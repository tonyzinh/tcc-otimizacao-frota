# Databricks notebook source
# MAGIC %md
# MAGIC # tb_slv_posicoes_motoristas_v2
# MAGIC
# MAGIC Explosão de `ofertaList`: uma linha por motorista online em cada foto de 10 min. Estado decodificado
# MAGIC (1 Online, 3 em corrida, 4 Selecionado, 5 Indisponível; enum inferido em DT010), motorista
# MAGIC pseudonimizado, posição com 4 casas, idade da posição, `fl_coordenada_valida` e H3 r7 (da fonte) e r8.

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,Explosão e gravação
sal = sal_pseudonimo()
snap = spark.table(f"{BRONZE}.tb_bro_ofertas_snapshot_v2")
p = (snap.select("tag_lote", F.col("codigo").alias("snapshot"), ts("dataHora").alias("ts_snapshot"),
                 F.explode("ofertaList").alias("o"))
     .select("tag_lote", "snapshot", "ts_snapshot",
             F.col("o.codigo").alias("_id_motorista"), F.col("o.status").alias("estado"),
             F.coalesce(F.col("o.passageiroEmbarcado"), F.lit(False)).alias("passageiro_embarcado"),
             F.col("o.latitude").alias("_lat"), F.col("o.longitude").alias("_lon"),
             F.col("o.h3Index").alias("h3_r7"),
             F.to_timestamp(F.regexp_replace("o.dataPosicaoGPS", r"(\.\d{6})\d+", "$1")).alias("_ts_gps"))
     .withColumn("motorista_pseud", pseudonimo("_id_motorista", sal))
     .withColumn("estado_label", F.expr("CASE estado WHEN 1 THEN 'ONLINE' WHEN 3 THEN 'EM_CORRIDA' "
                                        "WHEN 4 THEN 'SELECIONADO' WHEN 5 THEN 'INDISPONIVEL' ELSE 'DESCONHECIDO' END"))
     .withColumn("fl_coordenada_valida", na_caixa(F.col("_lat"), F.col("_lon")))
     .withColumn("h3_r8", F.when(F.col("fl_coordenada_valida"), F.expr("h3_longlatash3string(_lon, _lat, 8)")))
     .withColumn("idade_posicao_s", F.col("ts_snapshot").cast("double") - F.col("_ts_gps").cast("double"))
     .withColumn("fl_posicao_atual", F.coalesce(F.col("idade_posicao_s").between(-60, 300), F.lit(False)))
     .withColumn("lat", F.round("_lat", 4)).withColumn("lon", F.round("_lon", 4))
     .drop("_id_motorista", "_lat", "_lon", "_ts_gps"))
print({"tb_slv_posicoes_motoristas_v2": gravar(p, f"{SILVER}.tb_slv_posicoes_motoristas_v2",
                                               "Silver v2: posição e estado por motorista e foto")})
