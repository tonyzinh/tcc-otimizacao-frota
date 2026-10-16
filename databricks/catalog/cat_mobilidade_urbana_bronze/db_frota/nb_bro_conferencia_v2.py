# Databricks notebook source
# MAGIC %md
# MAGIC # Conferência da Bronze v2 contra os manifestos
# MAGIC
# MAGIC Falha se, em qualquer lote e fase, `lidos != total`, faltar arquivo listado no manifesto ou as linhas
# MAGIC ingeridas diferirem de `lidos`. Imprime só contagens.

# COMMAND ----------

# MAGIC %run ../../nb_v2_comum

# COMMAND ----------

# DBTITLE 1,Manifestos e contagens
import json

TABELAS = {"req": "tb_bro_solicitacoes_v2", "hist": "tb_bro_historico_v2",
           "snap": "tb_bro_ofertas_snapshot_v2", "sum": "tb_bro_sumarios_v2"}
problemas, linhas = [], []
for tag in TAGS:
    texto = spark.read.text(f"{VOLUME}/{tag}/manifest_{tag}.json", wholetext=True).first()[0]
    manifesto = json.loads(texto)
    presentes = {r.arquivo for r in spark.read.format("binaryFile").load(f"{VOLUME}/{tag}/*.json")
                 .select(F.regexp_extract("path", r"([^/]+)$", 1).alias("arquivo")).collect()}
    for fase, info in manifesto["fases"].items():
        faltando = [a for a in info.get("arquivos", []) if a not in presentes]
        if faltando:
            problemas.append(f"{tag}/{fase}: {len(faltando)} arquivo(s) ausente(s)")
        if fase not in TABELAS:
            continue
        if info.get("lidos") != info.get("total"):
            problemas.append(f"{tag}/{fase}: lidos {info.get('lidos')} != total {info.get('total')}")
        n = spark.table(f"{BRONZE}.{TABELAS[fase]}").where(F.col("tag_lote") == tag).count()
        linhas.append({"lote": tag, "fase": fase, "lidos": info.get("lidos"), "ingeridas": n})
        if n != info.get("lidos"):
            problemas.append(f"{tag}/{fase}: ingeridas {n} != lidos {info.get('lidos')}")
for linha in linhas:
    print(linha)
dup = spark.table(f"{BRONZE}.tb_bro_solicitacoes_v2").groupBy("codigo").count().where("count > 1").count()
print({"codigos_duplicados_bronze": dup})
if problemas:
    raise AssertionError("; ".join(problemas))
print("conferência OK")
