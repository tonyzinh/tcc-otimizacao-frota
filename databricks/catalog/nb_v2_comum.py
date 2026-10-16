# Databricks notebook source
# MAGIC %md
# MAGIC # Medalhão v2: utilitários comuns
# MAGIC
# MAGIC Incluído por `%run` em todos os notebooks `nb_*_v2`. As regras aqui espelham
# MAGIC `src/tcc_frota/v2/rules.py` (tabela de status, caixa, imediata/agendada, ticks de duração,
# MAGIC pseudonimização); mudanças precisam ser feitas nos dois lugares.

# COMMAND ----------

# DBTITLE 1,Sessão Spark e constantes
try:
    spark  # noqa: F821
except NameError:
    from databricks.connect import DatabricksSession
    spark = DatabricksSession.builder.serverless(True).getOrCreate()

from pyspark.sql import Window as W
from pyspark.sql import functions as F
from pyspark.sql import types as T

spark.conf.set("spark.sql.session.timeZone", "America/Sao_Paulo")

BRONZE = "cat_mobilidade_urbana_bronze.db_frota"
SILVER = "cat_mobilidade_urbana_silver.db_frota"
GOLD = "cat_mobilidade_urbana_gold.db_frota"
VOLUME = "/Volumes/cat_mobilidade_urbana_bronze/db_frota/raw_v2"
TAGS = ("mar2026", "historico56", "set2026", "historico56_set")
BOX_LAT, BOX_LON = (-20.6, -20.0), (-40.6, -40.0)
TICKS_POR_SEGUNDO = 10_000_000

# Tabela de tratamento de status (RN004), idêntica a rules.STATUS_TREATMENT.
TRATAMENTO_STATUS = [
    ("CorridaEncerrada", "atendida", True, True),
    ("CorridaCanceladaSolicitantePosAceite", "cancelada_pos_aceite_solicitante", True, True),
    ("CorridaCanceladaMotoristaPosAceite", "cancelada_pos_aceite_motorista", True, True),
    ("NaoAtendida", "nao_atendida", True, False),
    ("LimiteEsperaAtingido", "nao_atendida_limite_espera", True, False),
    ("CorridaCanceladaSolicitante", "cancelada_solicitante_pre_aceite", True, False),
    ("PagamentoRejeitado", "nao_demanda_pagamento", False, False),
    ("CorridaCanceladaOperador", "nao_demanda_operador", False, False),
    ("Retracamento", "nao_demanda_retracamento", False, False),
    ("CorridaCanceladaAgendamento", "nao_demanda_agendamento_cancelado", False, False),
    ("CorridaIniciada", "transitorio_sem_desfecho", False, False),
    ("CondutorACaminho", "transitorio_sem_desfecho", False, False),
    ("CondutorChegou", "transitorio_sem_desfecho", False, False),
    ("AguardandoCondutor", "transitorio_sem_desfecho", False, False),
]


def tabela_status():
    return spark.createDataFrame(TRATAMENTO_STATUS, "status string, grupo_desfecho string, fl_demanda boolean, fl_aceito boolean")


def ts(coluna: str):
    """ISO com até 7 casas e offset; trunca a fração em 6 casas antes de converter."""
    return F.to_timestamp(F.regexp_replace(F.col(coluna), r"(\.\d{6})\d+", "$1"))


def na_caixa(lat, lon):
    return F.coalesce(lat.between(*BOX_LAT) & lon.between(*BOX_LON), F.lit(False))


def sal_pseudonimo() -> str:
    """Sal do segredo `tcc_frota/sal_pseudonimo` (nunca no Git)."""
    try:
        return dbutils.secrets.get("tcc_frota", "sal_pseudonimo")  # noqa: F821
    except NameError:
        import base64

        from databricks.sdk import WorkspaceClient

        valor = WorkspaceClient().secrets.get_secret("tcc_frota", "sal_pseudonimo").value
        return base64.b64decode(valor).decode()


def pseudonimo(coluna: str, sal: str):
    """SHA-256 de `sal:id`, 16 hex; igual a rules.pseudonym. Pseudonimização, não anonimização."""
    return F.when(F.col(coluna).isNull(), F.lit(None)).otherwise(
        F.substring(F.sha2(F.concat(F.lit(sal + ":"), F.col(coluna).cast("string")), 256), 1, 16))


def haversine_km(lat1, lon1, lat2, lon2):
    rad = F.lit(3.141592653589793 / 180)
    dlat, dlon = (lat2 - lat1) * rad, (lon2 - lon1) * rad
    h = F.sin(dlat / 2) ** 2 + F.cos(lat1 * rad) * F.cos(lat2 * rad) * F.sin(dlon / 2) ** 2
    return F.lit(2 * 6371.0088) * F.asin(F.least(F.lit(1.0), F.sqrt(h)))


def ler_paginas(prefixo: str, schema_source: T.StructType):
    """Lê `<VOLUME>/<tag>/<prefixo>_<tag>_pNN.json` e explode `hits.hits` em uma linha por `_source`."""
    pagina = T.StructType([T.StructField("hits", T.StructType([
        T.StructField("hits", T.ArrayType(T.StructType([
            T.StructField("_id", T.StringType()),
            T.StructField("_source", schema_source),
        ]))),
    ]))])
    caminhos = [f"{VOLUME}/{tag}/{prefixo}_{tag}_p*.json" for tag in TAGS
                if prefixo == "req" or not tag.startswith("historico")]
    bruto = (spark.read.option("multiLine", True).schema(pagina).json(caminhos)
             .withColumn("arquivo_origem", F.regexp_extract(F.col("_metadata.file_path"), r"([^/]+)$", 1))
             .withColumn("tag_lote", F.regexp_extract(F.col("_metadata.file_path"), r"raw_v2/([^/]+)/", 1)))
    return (bruto.select("tag_lote", "arquivo_origem", F.explode("hits.hits").alias("hit"))
            .select("tag_lote", "arquivo_origem",
                    F.regexp_extract("arquivo_origem", r"_p(\d+)\.json$", 1).cast("int").alias("pagina"),
                    F.col("hit._id").alias("es_id"), "hit._source.*")
            .withColumn("ingerido_em", F.current_timestamp())
            .withColumn("hash_linha", F.sha2(F.to_json(F.struct(*schema_source.fieldNames())), 256)))


def gravar(df, tabela: str, comentario: str) -> int:
    """Escrita overwrite idempotente; devolve a contagem gravada."""
    df.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(tabela)
    spark.sql(f"COMMENT ON TABLE {tabela} IS '{comentario}'")
    return spark.table(tabela).count()
