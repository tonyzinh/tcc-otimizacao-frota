# Databricks notebook source
# MAGIC %md
# MAGIC # tb_slv_sumarios_v2
# MAGIC
# MAGIC Contadores a cada 2 min. `fl_consistente_com_posicoes` compara com a foto de mesmo `codigo` (a cada
# MAGIC 10 min); nulo quando não há foto correspondente.

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,Consistência e gravação
pos = spark.table(f"{SILVER}.tb_slv_posicoes_motoristas_v2")
contagem = pos.groupBy(F.col("snapshot").alias("codigo")).agg(
    F.sum((F.col("estado") == 1).cast("int")).alias("f_online"),
    F.sum(((F.col("estado") == 3) & ~F.col("passageiro_embarcado")).cast("int")).alias("f_acaminho"),
    F.sum(((F.col("estado") == 3) & F.col("passageiro_embarcado")).cast("int")).alias("f_compassageiro"),
    F.sum((F.col("estado") == 4).cast("int")).alias("f_selecionado"),
    F.sum((F.col("estado") == 5).cast("int")).alias("f_indisponivel"))
s = (spark.table(f"{BRONZE}.tb_bro_sumarios_v2")
     .select("tag_lote", "codigo", ts("dataHora").alias("ts"), "qtdOnline", "qtdOffline", "qtdACaminho",
             "qtdComPassageiro", "qtdAproveitamento", "qtdSelecionado", "qtdIndisponivel")
     .join(contagem, "codigo", "left")
     .withColumn("fl_tem_foto", F.col("f_online").isNotNull())
     .withColumn("fl_consistente_com_posicoes", F.when(F.col("fl_tem_foto"),
                 (F.col("qtdOnline") == F.col("f_online")) & (F.col("qtdACaminho") == F.col("f_acaminho"))
                 & (F.col("qtdComPassageiro") == F.col("f_compassageiro"))
                 & (F.col("qtdSelecionado") == F.col("f_selecionado"))
                 & (F.col("qtdIndisponivel") == F.col("f_indisponivel"))))
     .drop("f_online", "f_acaminho", "f_compassageiro", "f_selecionado", "f_indisponivel"))
print({"tb_slv_sumarios_v2": gravar(s, f"{SILVER}.tb_slv_sumarios_v2", "Silver v2: sumários com consistência")})
