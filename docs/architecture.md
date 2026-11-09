# Arquitetura

Estrutura lógica do repositório desde a reestruturação de 09/11/2026. O mapa dos caminhos antigos para os novos está em `reports/manifests/repository_restructure/path_map.csv` (dados e relatórios) e em `code_rename_map.csv` (módulos e scripts). O inventário físico (contagem de arquivos por pasta) está em `inventory_after.csv`, na mesma pasta.

## Pastas

| Pasta | Função | Versionada? |
|---|---|---|
| `article/` | Artigo em LaTeX (seções, apêndices, referências, figuras) e relatórios editoriais. `build/` é regenerável. | sim, exceto `build/` |
| `configs/` | Contrato de dados, hipóteses de tempo, políticas, cenários sintéticos e experimentos. `private/` guarda parâmetros sigilosos. | sim, exceto `private/` |
| `data/` | Dados de entrada e derivados locais. Nada aqui é versionado. | não |
| `docs/` | Documentação vigente, em português. | sim |
| `notebook/` | Cadernos de visão geral, exemplo do Húngaro, mapa e resultados. Só leem agregados. | sim |
| `reports/` | Única raiz de resultados: avaliações, diagnósticos, qualidade dos dados, figuras e manifestos. | agregados sim; Parquet não |
| `scripts/` | Pontos de entrada pequenos: extração, geografia, análises posteriores, figuras e verificações. | sim |
| `src/tcc_frota/` | Pacote Python: domínio, despacho, simulador, dados, cenários, métricas, figuras e CLI. | sim |
| `tests/` | Testes unitários, de integração, de regressão (congelados) e de reprodutibilidade. | sim |

### `data/`

| Subpasta | Conteúdo |
|---|---|
| `raw/v1_viagens/` | Extração vigente, somente leitura, pseudonimizada, em Parquet por fonte, entidade e dia, com manifesto por lote. O nome `v1_viagens` é o da origem dos dados e foi mantido (ver `decisions.md`, R-34). Exemplo de partição: `raw/v1_viagens/ods/solicitacao/dt=2026-10-01/part-000.parquet` e `manifest.json`. |
| `raw/v1_viagens_schema1_20261108/`, `raw/v1_viagens_previous_salt_20261106/` | Extrações substituídas (esquema 1 e sal anterior), preservadas como evidência. |
| `processed/world_cache/` | Cache regenerável dos mundos simulados por dia (`mundo_AAAA-MM-DD_<hash>.pkl`). Contém registros individuais. |
| `processed/run_outputs/`, `processed/data_quality_samples/` | Logs e saídas individuais de execuções e amostras de conciliação. |
| `geographic/` | Geografia pública (malhas do IBGE, vias do OpenStreetMap, rede viária) com `manifesto_geografia.json`. |

### `reports/`

| Subpasta | Conteúdo |
|---|---|
| `historical/frozen_evaluation/` | Avaliação congelada com dados reais (setembro e outubro de 2026): execução por dia, análise, manifestos e `CONGELAMENTO.json`. |
| `historical/development/` | Desenvolvimento com dados reais: seleção do despacho (`dispatch_selection/`, antigo grupo B), seleção do reposicionamento (`repositioning_selection/`, antigo grupo A, resultado desfavorável), análises de treino e validação, A×B de desenvolvimento e fatias da referência. |
| `synthetic/dispatch_evaluation/` | Avaliação sintética congelada do despacho (22 cenários × 40 sementes), usada no artigo. Exemplo: `cen=S1__sem=20001.parquet`. |
| `synthetic/` (demais) | Avaliação do reposicionamento, seleção de margem, ablação, auditoria do objetivo, enumeração, fatia de desenvolvimento e o estudo sintético de 08/11 (`repositioning_greedy_study/`). |
| `diagnostics/` | Análises posteriores aos resultados congelados, por finalidade: `statistics/robustness_review/` (rodada 4), `calibration/recalibration_out_of_sample/` (rodada 5), `consistency/` (rodadas 6 e 9), `batching/global_greedy_comparison/` (rodada 7), `availability/test_period_weekday_comparison/` (rodada 8). Cada pasta tem um `provenance.json` com a rodada, a data, o plano e o script. |
| `data_quality/` | Qualidade, conciliação, cobertura e disponibilidade da extração; verificação das bases reais. |
| `figures/` | Origem oficial das figuras (PDF e PNG). As cópias em `article/figures/` são geradas a partir daqui. |
| `manifests/` | Equivalência, execução dos notebooks, reestruturação do repositório (mapas, hashes, diffs) e manifesto de checksums dos dados. |
| `examples/` | Exemplo sintético pequeno. |

O estudo anterior (reposicionamento preventivo D+1, bateria de 13 algoritmos, `reports/tcc_final/`, `reports/tcc_v2/` e `resultados/`) saiu da árvore ativa e está preservado fora dela, com checksums (ver `repository_migration.md`). A conferência dos seus hashes continua por `scripts/verify_frozen_results.py`.

## Pacote `src/tcc_frota/`

Pacotes sem ciclos:

```
cli ──► visualization ──► metrics ──► simulation ──► assignment ──► domain
 │            │                            │
 │            └──► scenarios ──────────────┘          simulation ──► data ──► domain
 └────────────────────────────────────────────────►  (cli importa todos)
```

Dependências permitidas, conferidas por `tests/reproducibility/test_package_layers.py`:
- `domain` não importa ninguém;
- `assignment` e `data` importam só `domain`;
- `simulation` importa `domain`, `assignment` e `data`;
- `scenarios` importa `domain`, `assignment` e `simulation`;
- `metrics` importa `domain`, `simulation` e `assignment`;
- `visualization` importa `scenarios`, `metrics` e `domain`;
- `cli` importa todos.

| Pacote | Responsabilidade | Principais símbolos |
|---|---|---|
| `domain` | Entidades puras (dataclasses), unidades e assinatura de entrada | `SimParams`, `SimRequest`, `SimDriver`, `SimResult`, `reta_km`, `signature` |
| `assignment` | Decisão do lote: o que a política escolhe a cada instante | `nearest_fifo` (A, B), `hungarian` (C), `global_greedy` (D), `kuhn_munkres`, `POLICIES` |
| `simulation` | Simulador de eventos discretos e experimento por dia real | `engine.simulate`, `historical.run_day` |
| `scenarios` | Geografia pública, gerador sintético, catálogo e execução de pares | `geography`, `generator`, `catalog`, `runner.run_pair` |
| `data` | Portão de autorização, montagem do mundo histórico, disponibilidade e tempo | `authorization`, `world`, `availability`, `initial_position`, `time_utils` |
| `data.extraction` | Extração somente leitura por lote diário | `entities`, `filters`, `runner`, `writer`, `quality` |
| `data.reading` | Leitores somente leitura de SQL Server e Elasticsearch, com lista de permissões | `sql_server`, `elasticsearch`, `sql_guard`, `env` |
| `data.privacy` | Pseudonimização HMAC-SHA256 e guarda do segredo | `pseudonymization` |
| `metrics` | Totais, contrastes pareados, bootstrap, Holm e critérios de serviço | `historical`, `synthetic`, `statistics` |
| `visualization` | Figuras (PDF vetorial e PNG) e mapa H3 | `figures`, `maps` |
| `cli` | Comando `tcc-frota` (`python -m tcc_frota.cli.main`) | `run-synthetic`, `run-historical`, `analyze-*`, `figures` |

## Fluxo de dados

1. **Histórico (dados reais, privados):**
   - extração local para `data/raw/v1_viagens/`;
   - `data.world.montar` monta pedidos, jornadas, compromissos e posição inicial;
   - `simulation.engine.simulate` roda cada política e grava um Parquet por dia;
   - `metrics.historical` gera as tabelas e figuras agregadas.
2. **Sintético (público):**
   - `data/geographic/` traz IBGE e OSM;
   - `scenarios.geography` monta rede, pontos H3 e recorte;
   - `scenarios.generator` gera pedidos e frota por semente;
   - `simulation.engine.simulate` grava um Parquet por cenário e semente;
   - `metrics.synthetic` faz a análise.

As entradas das políticas são idênticas, e a assinatura SHA-256 é conferida por par. A política só vê pedidos já chegados e o estado do instante do lote.

## Convenções

- **Nomes:** pastas, módulos e identificadores em inglês, `snake_case`; documentação e artigo em português.
- **Exceções documentadas** (contratos congelados):
  - identificadores gravados nos resultados (`B0_imediato_atual`, `B_lote60s_hungaro`, `D_lote60s_hungaro`, `R0`);
  - nomes de colunas e chaves dos Parquet e manifestos (`extraido_em`, `pseudonimizacao`, `dia=`, `dt=`, `cen=…__sem=…`);
  - nomes de arquivos dentro dos conjuntos de resultados movidos (`RELATORIO_*.md`, `PLANO.md`, `analise/`, `execucao/`, `treino/`, `validacao/`);
  - nomes de tabelas, campos e serviços das fontes externas.
- **Configuração:** fica em `configs/`. O código é a fonte executável, e os testes conferem que as configurações concordam com ele.
- **Pastas protegidas:** o CLI recusa gravar em `reports/historical/`, `reports/synthetic/` e `reports/diagnostics/`. Resultado novo vai para pasta nova.
