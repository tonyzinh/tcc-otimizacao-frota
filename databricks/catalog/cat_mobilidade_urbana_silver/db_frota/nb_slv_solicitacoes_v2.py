# Databricks notebook source
# MAGIC %md
# MAGIC # tb_slv_solicitacoes_v2 e tb_slv_solicitacoes_status_v2
# MAGIC
# MAGIC Uma linha por `codigo` (RN003), timestamps em America/Sao_Paulo, imediata × agendada, origem na caixa,
# MAGIC desfecho pela tabela de tratamento (RN004), origem/destino com 3 casas e H3 r7/r8 calculados das
# MAGIC coordenadas brutas, durações e `fl_tempos_ordenados`. `base_temporal` = `dT_REGISTRO` (imediatas) ou
# MAGIC `dT_AGENDAMENTO` (agendadas). `nU_DR_REAL` e `tX_H3INDEX_REPOSICIONAMENTO_REAL` ficam marcados como
# MAGIC semântica PENDENTE.

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,Tipagem e regras
sal = sal_pseudonimo()
b = spark.table(f"{BRONZE}.tb_bro_solicitacoes_v2")
lat, lon = F.col("tX_ORIGEM_LAT").cast("double"), F.col("tX_ORIGEM_LNG").cast("double")
dlat, dlon = F.col("tX_DESTINO_LAT").cast("double"), F.col("tX_DESTINO_LNG").cast("double")
final = F.array_max(F.transform(
    F.filter("logStatus", lambda x: x["tX_STATUS"] == F.col("tX_STATUS")),
    lambda x: F.to_timestamp(F.regexp_replace(x["dT_REGISTRO"], r"(\.\d{6})\d+", "$1"))))
s = (b.select(
        F.col("codigo").cast("bigint").alias("codigo"), "tag_lote", "arquivo_origem", "pagina",
        F.col("tX_STATUS").alias("status"),
        F.col("dT_AGENDAMENTO").isNull().alias("fl_imediata"),
        na_caixa(lat, lon).alias("fl_na_caixa"),
        F.col("tX_TP_SOLICITACAO").alias("tipo_solicitacao"), F.col("cD_TIPO_SERVICO").alias("tipo_servico"),
        ts("dT_REGISTRO").alias("ts_registro"), ts("dT_AGENDAMENTO").alias("ts_agendamento"),
        ts("dT_ACEITE_MOTORISTA").alias("ts_aceite"), ts("dT_CHEGADA_MOTORISTA").alias("ts_chegada"),
        ts("dT_INICIO_REALIZADA").alias("ts_inicio"), ts("dT_FIM_REALIZADA").alias("ts_fim"),
        final.alias("ts_status_final"),
        F.round(lat, 3).alias("lat_origem"), F.round(lon, 3).alias("lon_origem"),
        F.expr("h3_longlatash3string(CAST(tX_ORIGEM_LNG AS DOUBLE), CAST(tX_ORIGEM_LAT AS DOUBLE), 7)").alias("h3_r7_origem"),
        F.expr("h3_longlatash3string(CAST(tX_ORIGEM_LNG AS DOUBLE), CAST(tX_ORIGEM_LAT AS DOUBLE), 8)").alias("h3_r8_origem"),
        F.round(dlat, 3).alias("lat_destino"), F.round(dlon, 3).alias("lon_destino"),
        F.expr("h3_longlatash3string(CAST(tX_DESTINO_LNG AS DOUBLE), CAST(tX_DESTINO_LAT AS DOUBLE), 7)").alias("h3_r7_destino"),
        F.round(F.col("tX_DESTINOREAL_LAT").cast("double"), 3).alias("lat_destino_real"),
        F.round(F.col("tX_DESTINOREAL_LNG").cast("double"), 3).alias("lon_destino_real"),
        F.when(F.col("nU_DISTPERCORRIDA") > 0, F.col("nU_DISTPERCORRIDA") / 1000).alias("dist_percorrida_km"),
        F.when(F.col("tX_DURACAO") > 0, F.col("tX_DURACAO") / TICKS_POR_SEGUNDO).alias("dur_viagem_s"),
        pseudonimo("cD_MOTORISTA", sal).alias("motorista_pseud"),
        F.col("nU_DR_REAL").alias("nu_dr_real_pendente"),
        F.col("tX_H3INDEX_REPOSICIONAMENTO_REAL").isNotNull().alias("fl_h3_repos_real_pendente"),
        F.col("indiceViabilidade").isNotNull().alias("fl_indice_viabilidade"))
     .join(F.broadcast(tabela_status()), "status", "left")
     .withColumn("grupo_desfecho", F.coalesce("grupo_desfecho", F.lit("desconhecido")))
     .withColumn("fl_demanda", F.coalesce("fl_demanda", F.lit(False)))
     .withColumn("fl_aceito", F.coalesce("fl_aceito", F.lit(False)))
     .withColumn("base_temporal", F.when(F.col("fl_imediata"), "dT_REGISTRO").otherwise("dT_AGENDAMENTO"))
     .withColumn("ts_base", F.when(F.col("fl_imediata"), F.col("ts_registro")).otherwise(F.col("ts_agendamento")))
     .withColumn("data_base", F.to_date("ts_base")).withColumn("hora_base", F.hour("ts_base")))

marcos = ["ts_registro", "ts_aceite", "ts_chegada", "ts_inicio", "ts_fim"]
presentes = F.filter(F.array(*[F.col(c) for c in marcos]), lambda x: x.isNotNull())
s = (s.withColumn("fl_tempos_ordenados", F.array_sort(presentes) == presentes)
     .withColumn("s_registro_ate_aceite", F.col("ts_aceite").cast("double") - F.col("ts_registro").cast("double"))
     .withColumn("s_registro_ate_chegada", F.col("ts_chegada").cast("double") - F.col("ts_registro").cast("double"))
     .withColumn("s_registro_ate_status_final",
                 F.col("ts_status_final").cast("double") - F.col("ts_registro").cast("double")))

ordem = W.partitionBy("codigo").orderBy(F.coalesce("ts_status_final", "ts_registro").desc())
s = s.withColumn("_rn", F.row_number().over(ordem)).where("_rn = 1").drop("_rn")

# COMMAND ----------

# DBTITLE 1,Gravação e status em formato longo
n = gravar(s, f"{SILVER}.tb_slv_solicitacoes_v2", "Silver v2: uma linha por solicitação, regras RN003/RN004")
status = (b.select(F.col("codigo").cast("bigint").alias("codigo"), F.explode_outer("logStatus").alias("l"))
          .where(F.col("l").isNotNull())
          .select("codigo", F.col("l.tX_STATUS").alias("status"),
                  F.to_timestamp(F.regexp_replace("l.dT_REGISTRO", r"(\.\d{6})\d+", "$1")).alias("ts_status"))
          .dropDuplicates())
m = gravar(status, f"{SILVER}.tb_slv_solicitacoes_status_v2", "Silver v2: logStatus em formato longo")
print({"tb_slv_solicitacoes_v2": n, "tb_slv_solicitacoes_status_v2": m})
