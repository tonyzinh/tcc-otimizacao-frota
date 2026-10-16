# Inventário Databricks antes do reset v2

**Gerado em 15/10/2026** (somente leitura, perfil `entonysantos`, workspace `dbc-78e70936-8218`). Contagens por `COUNT(*)`; tamanho e data por `DESCRIBE DETAIL`. Nenhuma linha de dado foi lida ou exibida.

| Catálogo.schema.tabela | Tipo | Linhas | Tamanho (MB) | Arquivos | Última alteração (UTC) |
|---|---|---:|---:|---:|---|
| `cat_mobilidade_urbana_bronze.db_frota.tb_ofertas` | MANAGED | 262.708 | 202.3 | 4 | 2026-10-15T00:37:36.000Z |
| `cat_mobilidade_urbana_bronze.db_frota.tb_solicitacoes` | MANAGED | 451.386 | 24.3 | 1 | 2026-10-15T00:37:43.000Z |
| `cat_mobilidade_urbana_bronze.db_frota.tb_sumarios` | MANAGED | 262.708 | 6.8 | 1 | 2026-10-15T00:37:24.000Z |
| `cat_mobilidade_urbana_silver.db_frota.tb_corridas` | MANAGED | 222.359 | 29.4 | 1 | 2026-10-15T00:27:13.000Z |
| `cat_mobilidade_urbana_silver.db_frota.tb_deslocamentos_motoristas` | MANAGED | 10.492.132 | 846.6 | 14 | 2026-10-15T00:26:51.000Z |
| `cat_mobilidade_urbana_silver.db_frota.tb_posicoes_motoristas` | MANAGED | 10.556.363 | 478.1 | 13 | 2026-10-15T00:26:38.000Z |
| `cat_mobilidade_urbana_silver.db_frota.tb_solicitacoes` | MANAGED | 451.386 | 21.0 | 1 | 2026-10-15T00:26:09.000Z |
| `cat_mobilidade_urbana_silver.db_frota.tb_solicitacoes_status` | MANAGED | 1.670.311 | 9.7 | 1 | 2026-10-15T00:26:17.000Z |
| `cat_mobilidade_urbana_silver.db_frota.tb_sumarios` | MANAGED | 262.708 | 8.0 | 2 | 2026-10-15T00:27:00.000Z |
| `cat_mobilidade_urbana_gold.db_frota.tb_corridas_replay` | MANAGED | 221.940 | 18.1 | 1 | 2026-10-15T00:28:12.000Z |
| `cat_mobilidade_urbana_gold.db_frota.tb_demanda_regional_hora` | MANAGED | 53.301 | 0.2 | 1 | 2026-10-15T00:27:33.000Z |
| `cat_mobilidade_urbana_gold.db_frota.tb_demanda_zona_hora` | MANAGED | 149.851 | 0.7 | 1 | 2026-10-15T00:27:27.000Z |
| `cat_mobilidade_urbana_gold.db_frota.tb_dim_zonas_h3` | MANAGED | 5.492 | 0.2 | 1 | 2026-10-15T00:27:21.000Z |
| `cat_mobilidade_urbana_gold.db_frota.tb_frota_motorista_hora` | MANAGED | 379.966 | 6.1 | 6 | 2026-10-15T00:27:48.000Z |
| `cat_mobilidade_urbana_gold.db_frota.tb_frota_sessoes` | MANAGED | 163.955 | 7.0 | 6 | 2026-10-15T00:27:40.000Z |
| `cat_mobilidade_urbana_gold.db_frota.tb_km_vazio_diario` | MANAGED | 365 | 0.0 | 1 | 2026-10-15T00:28:06.000Z |
| `cat_mobilidade_urbana_gold.db_frota.tb_km_vazio_segmentos` | MANAGED | 221.929 | 19.3 | 1 | 2026-10-15T00:27:58.000Z |
| `cat_mobilidade_urbana_gold.db_frota.tb_qualidade_dados` | MANAGED | 29 | 0.0 | 1 | 2026-10-15T00:28:46.000Z |

Views: nenhuma no schema `db_frota` dos três catálogos.

**Volumes:** `cat_mobilidade_urbana_bronze.db_frota.volumes` (MANAGED, JSONL mensais de `solicitacoes`, `ofertas` e `sumarios` de out/2025 a set/2026). Silver e Gold não têm volumes.

## Backup feito antes do apagamento

1. `tcc-frota gold-export` → `reports/runs/gold_cache/` (ignorado pelo Git): 6 tabelas em Parquet, linhas iguais às do workspace (5.492; 149.851; 163.955; 379.966; 221.940; 221.929).
2. `CREATE TABLE ... DEEP CLONE` das 9 tabelas Gold em `cat_mobilidade_urbana_gold.db_frota_legado`; contagens conferidas e idênticas às originais. O Free Edition permitiu o clone.
3. `reports/runs/gold_replay/*/result.json` de setembro **não existe mais nesta máquina** (a pasta `reports/runs/` estava ausente). Os agregados publicados em `docs/experimento_real.md` e `docs/comparacao_algoritmos.md` foram transcritos para `reports/tcc_final/legado_setembro2026/`. Com a Gold em cache e o clone, o replay legado pode ser refeito.

Depois do reset, as camadas legadas de out/2025 a set/2026 só voltam a partir do clone `db_frota_legado` (Gold) ou de nova extração (Bronze/Silver).
