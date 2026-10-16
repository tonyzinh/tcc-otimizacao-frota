# Databricks notebook source
# MAGIC %md
# MAGIC # tb_gld_qualidade_v2
# MAGIC
# MAGIC Cobertura por campo e mês, perdas por filtro do universo do replay, status por tratamento, origens fora
# MAGIC da caixa, consistência foto × sumário, lacunas de foto e deslocamento noturno (RN027).

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,Métricas em formato longo (grupo, mes, medida, valor)
s = spark.table(f"{SILVER}.tb_slv_solicitacoes_v2").withColumn("mes", F.date_format("ts_registro", "yyyy-MM"))
enc = s.where("status = 'CorridaEncerrada'")
campos = ["lat_origem", "lat_destino", "ts_aceite", "ts_chegada", "ts_inicio", "ts_fim", "dur_viagem_s",
          "dist_percorrida_km", "motorista_pseud", "lat_destino_real", "nu_dr_real_pendente"]
L = lambda g, m, v: (F.lit(g).alias("grupo"), F.col("mes"), F.lit(m).alias("medida"), v.cast("double").alias("valor"))
partes = [
    s.groupBy("mes").agg(F.count("*").alias("v")).select(*L("volume", "solicitacoes", F.col("v"))),
    s.groupBy("mes").agg(F.sum(F.col("fl_imediata").cast("int")).alias("v")).select(*L("volume", "imediatas", F.col("v"))),
    s.groupBy("mes").agg(F.sum((~F.col("fl_na_caixa")).cast("int")).alias("v")).select(*L("volume", "fora_da_caixa", F.col("v"))),
    enc.groupBy("mes").agg((100 * F.avg(F.col("fl_tempos_ordenados").cast("int"))).alias("v"))
       .select(*L("qualidade", "encerradas_tempos_ordenados_pct", F.col("v"))),
    s.where("status = 'NaoAtendida'").groupBy("mes").agg((100 * F.avg(F.col("lat_origem").isNotNull().cast("int"))).alias("v"))
       .select(*L("qualidade", "nao_atendidas_com_origem_pct", F.col("v"))),
    s.groupBy("mes", "status").count().select(F.lit("status").alias("grupo"), "mes", F.col("status").alias("medida"),
                                              F.col("count").cast("double").alias("valor")),
]
for c in campos:
    partes.append(enc.groupBy("mes").agg((100 * F.avg(F.col(c).isNotNull().cast("int"))).alias("v"))
                  .select(*L("cobertura_encerradas_pct", c, F.col("v"))))
filtro = (s.select(F.when(~F.col("fl_imediata"), "excluido_agendada")
                    .when(~F.col("fl_demanda"), F.concat(F.lit("excluido_nao_demanda:"), F.col("grupo_desfecho")))
                    .when(~F.col("fl_na_caixa"), "excluido_fora_da_caixa")
                    .when(F.col("ts_base").isNull(), "excluido_sem_carimbo")
                    .otherwise("universo_replay").alias("medida"))
          .groupBy("medida").count()
          .select(F.lit("filtro_replay").alias("grupo"), F.lit("todos").alias("mes"), "medida", F.col("count").cast("double").alias("valor")))
partes.append(filtro)
sumarios = (spark.table(f"{SILVER}.tb_slv_sumarios_v2").where("fl_tem_foto").groupBy(F.col("tag_lote").alias("mes"))
            .agg((100 * F.avg(F.col("fl_consistente_com_posicoes").cast("int"))).alias("v"))
            .select(*L("frota", "fotos_consistentes_com_sumario_pct", F.col("v"))))
partes.append(sumarios)
fotos = (spark.table(f"{GOLD}.tb_gld_frota_snapshot_v2").select("tag_lote", "ts_snapshot").distinct()
         .withColumn("gap", (F.col("ts_snapshot").cast("double")
                             - F.lag("ts_snapshot").over(W.partitionBy("tag_lote").orderBy("ts_snapshot")).cast("double")) / 60))
partes.append(fotos.groupBy(F.col("tag_lote").alias("mes")).agg(F.sum((F.col("gap") > 10.5).cast("int")).alias("v"))
              .select(*L("frota", "lacunas_foto_maior_que_10min", F.col("v"))))
partes.append(fotos.groupBy(F.col("tag_lote").alias("mes")).agg(F.max("gap").alias("v"))
              .select(*L("frota", "maior_lacuna_foto_min", F.col("v"))))
q = partes[0]
for p in partes[1:]:
    q = q.unionByName(p)
print({"tb_gld_qualidade_v2": gravar(q, f"{GOLD}.tb_gld_qualidade_v2", "Gold v2: qualidade e cobertura (RN027)")})
