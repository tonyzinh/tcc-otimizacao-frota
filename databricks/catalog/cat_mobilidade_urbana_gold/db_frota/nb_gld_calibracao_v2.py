# Databricks notebook source
# MAGIC %md
# MAGIC # tb_gld_calibracao_v2
# MAGIC
# MAGIC Medidas para calibrar o simulador, com n e quantis (p10, p25, p50, p75, p90): fator rua/reta da viagem
# MAGIC e da busca, velocidade até o passageiro e tempos de busca, de não atendimento e de desistência.
# MAGIC Todas são estimativas; nenhuma é odômetro.

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,Medidas
s = spark.table(f"{SILVER}.tb_slv_solicitacoes_v2")
h = spark.table(f"{SILVER}.tb_slv_historico_v2")
pos = (spark.table(f"{SILVER}.tb_slv_posicoes_motoristas_v2").where("fl_coordenada_valida")
       .select("motorista_pseud", "ts_snapshot", "estado", "lat", "lon"))


def resumo(df, valor: str, medida: str, unidade: str, fonte: str):
    return (df.where(F.col(valor).isNotNull())
            .agg(F.count(valor).alias("n"), F.percentile_approx(valor, [0.1, 0.25, 0.5, 0.75, 0.9], 10000).alias("q"))
            .select(F.lit(medida).alias("medida"), F.lit(unidade).alias("unidade"), F.lit(fonte).alias("fonte"), "n",
                    *[F.col("q")[i].alias(k) for i, k in enumerate(["p10", "p25", "p50", "p75", "p90"])]))


enc = s.where("status = 'CorridaEncerrada'").withColumn(
    "reta", haversine_km(F.col("lat_origem"), F.col("lon_origem"), F.col("lat_destino"), F.col("lon_destino")))
viagem = enc.where("reta >= 0.5").withColumn("r", F.col("dist_percorrida_km") / F.col("reta"))

j = h.where("dist_motorista_m > 0").select("codigo", "dist_motorista_m", F.col("motorista_pseud").alias("m")).join(
    s.select("codigo", "ts_aceite", "ts_chegada", "lat_origem", "lon_origem"), "codigo").where("ts_aceite IS NOT NULL AND ts_chegada IS NOT NULL")
j = j.withColumn("seg", F.col("ts_chegada").cast("double") - F.col("ts_aceite").cast("double"))
vel = j.where("seg >= 60 AND dist_motorista_m > 200").withColumn("v", (F.col("dist_motorista_m") / 1000) / (F.col("seg") / 3600))
cand = (j.join(pos, j.m == pos.motorista_pseud).where((F.col("ts_snapshot") <= F.col("ts_aceite"))
        & (F.col("ts_aceite").cast("double") - F.col("ts_snapshot").cast("double") <= 600)))
ult = (cand.withColumn("_r", F.row_number().over(W.partitionBy("codigo").orderBy(F.desc("ts_snapshot"))))
       .where("_r = 1 AND estado IN (1, 4)")
       .withColumn("reta", haversine_km(F.col("lat"), F.col("lon"), F.col("lat_origem"), F.col("lon_origem")))
       .where("reta >= 0.5").withColumn("r", (F.col("dist_motorista_m") / 1000) / F.col("reta")))
imed = s.where("fl_imediata AND fl_demanda AND fl_na_caixa")
partes = [
    resumo(viagem, "r", "fator_rua_reta_viagem", "razao", "nU_DISTPERCORRIDA / Haversine(origem, destino), reta >= 0,5 km"),
    resumo(ult, "r", "fator_rua_reta_busca", "razao", "distMotorista / Haversine(foto livre anterior ao aceite, origem)"),
    resumo(vel, "v", "velocidade_busca", "km/h (distância por rua)", "distMotorista / (chegada - aceite)"),
    resumo(imed.where("status = 'CorridaEncerrada'"), "s_registro_ate_chegada", "tempo_busca_registro_ate_chegada", "s",
           "imediatas encerradas na caixa"),
]
for g in ("nao_atendida", "nao_atendida_limite_espera", "cancelada_solicitante_pre_aceite"):
    partes.append(resumo(imed.where(F.col("grupo_desfecho") == g), "s_registro_ate_status_final",
                         f"tempo_registro_ate_{g}", "s", "logStatus do status final"))
cal = partes[0]
for p in partes[1:]:
    cal = cal.unionByName(p)
print({"tb_gld_calibracao_v2": gravar(cal, f"{GOLD}.tb_gld_calibracao_v2", "Gold v2: medidas de calibração com quantis")})
