# Inventário Databricks depois do reset v2

**Gerado em 15/10/2026**, após a resposta literal "CONFIRMO APAGAR" do proponente. Foram executados 18 `DROP TABLE IF EXISTS` (todos `SUCCEEDED`), sem `DROP SCHEMA`. Consulta de conferência: `system.information_schema.tables` filtrada por `cat_mobilidade_urbana_%`.

| Catálogo.schema | Tabelas legadas restantes | Observação |
|---|---:|---|
| `cat_mobilidade_urbana_bronze.db_frota` | 0 | Volume `volumes` (JSONL de out/2025 a set/2026) preservado |
| `cat_mobilidade_urbana_silver.db_frota` | 0 | — |
| `cat_mobilidade_urbana_gold.db_frota` | 0 | — |
| `cat_mobilidade_urbana_gold.db_frota_legado` | 9 | DEEP CLONE da Gold legada, contagens idênticas às originais (ver `inventario_databricks_antes.md`) |

Bronze e Silver de out/2025 a set/2026 só voltam por nova ingestão dos JSONL do Volume preservado ou por nova extração. As tabelas v2 desta rodada são criadas no mesmo schema `db_frota`, com sufixo `_v2`.
