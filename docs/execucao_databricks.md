# Execução no Databricks

**Atualizado em 16/10/2026.** O fluxo atual é o medalhão v2, descrito em [databricks_medalhao.md](databricks_medalhao.md). Os notebooks de perfil e auditoria do Parquet (`databricks/notebooks/00_perfil_parquet.py` e `01_auditoria.py`, DT007) foram retirados do repositório; o Parquet de 14/10/2026 não faz parte da rodada final.

1. Instale o Databricks CLI (≥ 1.0) e autentique o perfil: `databricks auth login --profile entonysantos`.
2. Copie os lotes autorizados para o Volume: `databricks fs cp -r data/raw/dados_<tag> dbfs:/Volumes/cat_mobilidade_urbana_bronze/db_frota/raw_v2/<tag>`.
3. Crie o segredo do sal (uma vez): `databricks secrets create-scope tcc_frota` e `databricks secrets put-secret tcc_frota sal_pseudonimo`.
4. Execute `python databricks/setup/executar_notebooks.py bronze silver gold` no ambiente com Databricks Connect. A conferência da Bronze interrompe a execução se algum manifesto divergir.
5. Opcional: `tcc-frota gold-export --v2` copia a Gold v2 para `reports/runs/gold_cache_v2/` (ignorado pelo Git).

Nenhuma linha é exibida nos logs; os notebooks imprimem só contagens. Não envie dados ao workspace sem autorização escrita para o lote (AGENTS.md).
