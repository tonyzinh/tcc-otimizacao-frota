# Databricks notebook source
# MAGIC %md
# MAGIC # tb_gld_replay_pedidos_v2 e tb_gld_demanda_zona_hora_v2
# MAGIC
# MAGIC Universo do replay e da previsão: solicitações **imediatas**, de **demanda** (tabela RN004) e com origem
# MAGIC **na caixa**. Inclui não atendidas, que agora têm origem própria. Pedido a pedido com origem/destino de
# MAGIC 3 casas, instante, desfecho observado, duração e distância quando existem. A demanda por zona-hora conta
# MAGIC atendidas e não atendidas separadamente (H3 r7 e r8).

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,Universo do replay
s = spark.table(f"{SILVER}.tb_slv_solicitacoes_v2")
u = s.where("fl_imediata AND fl_demanda AND fl_na_caixa AND ts_base IS NOT NULL")
replay = u.select(
    "codigo", "tag_lote", F.col("ts_base").alias("ts_pedido"), F.col("data_base").alias("data_local"),
    F.col("hora_base").alias("hora_local"), "tipo_servico", "lat_origem", "lon_origem", "h3_r7_origem", "h3_r8_origem",
    "lat_destino", "lon_destino", "grupo_desfecho", "fl_aceito",
    F.col("grupo_desfecho").startswith("cancelada_pos_aceite").alias("fl_cancelada_pos_aceite"),
    "motorista_pseud", "ts_aceite", "ts_chegada", "ts_fim",
    F.when(F.col("status") == "CorridaEncerrada", F.col("dur_viagem_s")).alias("dur_viagem_obs_s"),
    "dist_percorrida_km",
    F.when(F.col("grupo_desfecho") == "cancelada_solicitante_pre_aceite",
           F.col("s_registro_ate_status_final")).alias("s_espera_ate_desistir"),
    "s_registro_ate_chegada")
n = gravar(replay, f"{GOLD}.tb_gld_replay_pedidos_v2", "Gold v2: universo do replay (imediatas de demanda na caixa)")

# COMMAND ----------

# DBTITLE 1,Demanda por zona e hora
d = (spark.table(f"{GOLD}.tb_gld_replay_pedidos_v2")
     .groupBy("data_local", "hora_local", F.col("h3_r7_origem").alias("h3_r7"), F.col("h3_r8_origem").alias("h3_r8"))
     .agg(F.count("*").alias("qtd_demanda"), F.sum(F.col("fl_aceito").cast("int")).alias("qtd_aceitas"),
          F.sum(F.col("grupo_desfecho").isin("nao_atendida", "nao_atendida_limite_espera").cast("int")).alias("qtd_nao_atendidas"),
          F.sum((F.col("grupo_desfecho") == "cancelada_solicitante_pre_aceite").cast("int")).alias("qtd_canceladas_pre_aceite")))
m = gravar(d, f"{GOLD}.tb_gld_demanda_zona_hora_v2", "Gold v2: demanda imediata por data, hora e zona H3")
print({"tb_gld_replay_pedidos_v2": n, "tb_gld_demanda_zona_hora_v2": m})
