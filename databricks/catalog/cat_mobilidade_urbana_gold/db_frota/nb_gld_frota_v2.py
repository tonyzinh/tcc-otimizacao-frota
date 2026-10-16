# Databricks notebook source
# MAGIC %md
# MAGIC # tb_gld_frota_snapshot_v2, tb_gld_frota_sessoes_v2 e tb_gld_frota_motorista_hora_v2
# MAGIC
# MAGIC Fotos de 10 min com estado e posição; sessões de trabalho (estados 1/3/4, lacuna máxima de 20 min,
# MAGIC interrompidas por Indisponível); minutos trabalhando e livres por motorista e hora. Base da previsão
# MAGIC da escala (regime A), da escala conhecida (regime B) e do oráculo (regime C).

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,Fotos e sessões
pos = (spark.table(f"{SILVER}.tb_slv_posicoes_motoristas_v2").where("motorista_pseud IS NOT NULL")
       .select("tag_lote", "ts_snapshot", "motorista_pseud", "estado", "passageiro_embarcado", "lat", "lon",
               "h3_r7", "h3_r8", "fl_coordenada_valida", "fl_posicao_atual"))
n_snap = gravar(pos, f"{GOLD}.tb_gld_frota_snapshot_v2", "Gold v2: frota a cada 10 min (estado e posição)")

w = W.partitionBy("motorista_pseud").orderBy("ts_snapshot")
f = (spark.table(f"{GOLD}.tb_gld_frota_snapshot_v2")
     .withColumn("trab", F.col("estado").isin(1, 3, 4))
     .withColumn("prev_ts", F.lag("ts_snapshot").over(w)).withColumn("prev_trab", F.lag("trab").over(w))
     .where("trab")
     .withColumn("novo", (F.col("prev_ts").isNull() | ~F.col("prev_trab")
                          | (F.col("ts_snapshot").cast("double") - F.col("prev_ts").cast("double") > 1200)).cast("int"))
     .withColumn("seq_sessao", F.sum("novo").over(w.rowsBetween(W.unboundedPreceding, 0))))
valida = F.when(F.col("fl_coordenada_valida"), F.struct("ts_snapshot", "lat", "lon", "h3_r7"))
sess = (f.groupBy("motorista_pseud", "seq_sessao")
        .agg(F.min("ts_snapshot").alias("ts_inicio"),
             (F.max("ts_snapshot") + F.expr("INTERVAL 10 MINUTES")).alias("ts_fim"),
             F.min(valida).alias("ini"), F.max(valida).alias("fim"), F.count("*").alias("qtd_fotos"))
        .select("motorista_pseud", "seq_sessao", "ts_inicio", "ts_fim",
                F.col("ini.lat").alias("lat_inicio"), F.col("ini.lon").alias("lon_inicio"), F.col("ini.h3_r7").alias("h3_r7_inicio"),
                F.col("fim.lat").alias("lat_fim"), F.col("fim.lon").alias("lon_fim"), F.col("fim.h3_r7").alias("h3_r7_fim"),
                "qtd_fotos"))
n_sess = gravar(sess, f"{GOLD}.tb_gld_frota_sessoes_v2", "Gold v2: sessões de trabalho por motorista")

# COMMAND ----------

# DBTITLE 1,Presença por motorista e hora
hora = (f.groupBy("motorista_pseud", F.to_date("ts_snapshot").alias("data_local"), F.hour("ts_snapshot").alias("hora_local"))
        .agg((F.count("*") * 10).alias("min_trabalhando"), (F.sum((F.col("estado") == 1).cast("int")) * 10).alias("min_livre")))
n_hora = gravar(hora, f"{GOLD}.tb_gld_frota_motorista_hora_v2", "Gold v2: minutos trabalhando e livres por motorista-hora")
print({"tb_gld_frota_snapshot_v2": n_snap, "tb_gld_frota_sessoes_v2": n_sess, "tb_gld_frota_motorista_hora_v2": n_hora})
