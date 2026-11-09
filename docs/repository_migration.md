# Registro da reorganização do repositório (09/11/2026)

Reorganização em torno de **um único método principal**: atribuição conjunta pelo algoritmo Húngaro em lotes de 60 s (política C), comparada com A (mais próximo livre, despacho imediato) e B (mais próximo livre, lotes de 60 s). Este documento é o registro do que foi movido, removido, preservado e verificado. Nada foi commitado nem colocado no stage.

## 1. Preservação do estado anterior

Cópias **fora da árvore ativa** (não dependem do Git, porque grande parte do material era não rastreada):

| Item | Local (irmão do repositório) | Conteúdo |
|---|---|---|
| Pasta de preservação | `../tcc-otimizacao-frota_preservacao_2026-11-09/` | tudo abaixo |
| Árvore de trabalho antes | `arvore_de_trabalho_antes_da_reorganizacao.zip` (SHA-256 em `SHA256.txt`) | código, docs, testes, scripts, configs; `data/` e `.venv/` não entram |
| Estado do Git | `git_head.txt`, `git_status_antes.txt`, `git_diff_antes.patch` | HEAD `3e77cb9`, status e diff não commitado |
| Árvore antiga navegável | `arvore_antiga/{src_tcc_frota_antigo,tests,scripts,config}` | 143 módulos, 66 testes, 49 scripts e 6 configs de antes |

Nunca removidos: dados brutos/extraídos (`data/extraido/`, `data/geografia/`), segredo de pseudonimização, `configs/private/custos_privado.yaml` (copiado de `config/`, ignorado pelo Git), manifestos e evidências de congelamento, `reports/atribuicao_final/`, `reports/sintetico_v2/`, `reports/tcc_final/`, `resultados/`, `docs_antigos/`, `tcc-artigo-latex/` (artigo antigo).

## 2. Mapeamento de caminhos (antigo → novo)

| Antigo (`src/tcc_frota/…`) | Novo | Observação |
|---|---|---|
| `v2/sim.py` (entidades) | `domain/entities.py` | `SimParams`, `SimRequest`, `SimDriver`, `SimResult`, `reta_km`, `signature` |
| `v2/sim.py` (motor) | `simulation/engine.py` | `simulate` inalterado |
| `comparacao/experimento.py` | `simulation/historical.py` | `run_day`, `build_world`, manifesto; ids gravados mantidos |
| `comparacao/despacho.py` | `assignment/dispatch.py` | `guloso_fifo→nearest_fifo`, `hungaro→hungarian`; o método `fluxo` saiu |
| `comparacao/analise.py`, `scripts/analisar_atribuicao_final.py` | `metrics/statistics.py`, `metrics/historical.py` | análise por dia, E1–E3 |
| `scripts/analisar_liquido.py` | `metrics/synthetic.py` | Holm; critério sintético |
| `sintetico/{geografia,gerador,matriz}.py` | `scenarios/{geography,generator,catalog}.py` | + `runner.py` (pares A/B/C) |
| `referencia/{mundo,disponibilidade,posicao_inicial}.py`, `analise/tempo.py` | `data/{world,availability,initial_position,timeutil}.py` | mundo do cenário J |
| `extracao/`, `leitura/`, `privacidade/` | `data/extraction/`, `data/reading/`, `data/privacy/` | somente leitura; portão de dados reais |
| `ingestion/files.py` (portão) | `data/authorization.py` | `TCC_REAL_DATA_AUTHORIZED=YES` |
| `cli.py` e entradas `tcc_frota.*` | `cli/main.py` (`tcc-frota`) | `run-*`, `analyze-*`, `figures` |
| scripts de execução/análise | `tcc-frota …` e `scripts/check_equivalence.py` | ver §3 |
| `config/*.yaml` | `configs/{data,policies,scenarios,experiments,private}/` | |
| `tests/…` (66 arquivos) | `tests/{unit,integration,regression,reproducibility,fixtures}` | 10 migrados e renomeados, resto reescrito |

Pastas de dados e resultados **mantidas com o nome antigo** (justificativa: caminhos gravados nos manifestos congelados e em constantes do código; renomear alteraria a rastreabilidade): `data/extraido/` (= *processed*; extrato local privado), `data/geografia/` (= *geographic*; IBGE/OSM públicos), `reports/atribuicao_final/` (= *historical* e *final*), `reports/sintetico_v2/metodos_avaliacao_D/` (= *synthetic*). `data/raw/` não existe neste repositório (dados brutos ficam fora, sob portão do proprietário). Novas saídas: `reports/figures/`, `reports/manifests/`. O artigo novo está em `article/` (ver §6).

## 3. Removido da árvore ativa (com cópia em `arvore_antiga/`)

* **Módulos** (`src/tcc_frota/`): `algoritmos/` (bateria de 13 métodos, seletivo, MILP, NSGA-II, PSO, recozimento, MPC…), `v2/` (planejador D+1, previsão, regimes de frota), `v3/` (extensão), `availability/`, `gold/`, `ingestion/` (Databricks/Delta), `quality/`, `conciliacao/`, `optimization/`, `demand/`, `evaluation/`, `spatial/`, `synthetic/`, `simulation/` legado, `sintetico/{busca_plano,guloso_liquido,experimento*}.py`, `analise/` (demanda, pickup, valor líquido), `comparacao/{tabu,…}`, `referencia/{espera_no_destino,adaptador_guloso,…}`, `models.py`, `distance.py`, `experiment.py`, `cli.py`. Dependências: `scikit-learn`, `statsmodels`, `arch`, `openpyxl` e extras Databricks saíram do `pyproject.toml`.
* **Scripts** (49 → 6 mantidos: `extrair_v1_*.sh`, `baixar_geografia.py`, `verificar_bases_reais.py`, mais os novos `check_equivalence.py`, `run_notebooks.py`): `executar_*`, `analisar_*`, `v3_*`, bateria, seletivo, conciliação COBLI, auditorias e validações do planejador D+1.
* **Testes** exclusivos dos recursos removidos (56 arquivos): bateria, seletivo, v2/v3, availability, gold, ingestão, tabu, valor líquido, etc.
* `pyproject.toml.bak`, `config/` (cópias em `configs/`), caches `__pycache__`.
* **Efeito sobre a reprodutibilidade de resultados antigos:** `scripts/validar_baseline.py` e os testes que liam hashes de `docs_antigos/V2_PREREGISTRO.md` (artefatos v1 em `reports/tcc_final/`) saíram do fluxo ativo; os hashes continuam no documento e os scripts, na cópia de preservação.

Não alterados (material histórico, sem código ativo): `docs_antigos/`, `reports/tcc_final/`, `reports/tcc_v2/`, `resultados/`, `tabelas/`, `regras_de_negocio/`, demais pastas de `reports/` e `tcc-artigo-latex/` (artigo antigo).

## 4. Relação entre o experimento congelado e o código reorganizado

O congelamento de 09/11/2026 registrou o hash do código (SHA-256 `480a98a1…e93f87`, 151 arquivos), o commit-base `3e77cb9`, Python 3.12.14 e 201 hashes de manifestos de dados (`reports/atribuicao_final/CONGELAMENTO.json`). **O código reorganizado tem outro hash** (arquivos e módulos movidos). Os manifestos antigos **não foram atualizados nem reescritos** e não devem ser lidos como produzidos pelo código novo. A identidade experimental preservada: janela de 60 s, elegibilidade, ordem (chegada, id), desempates (custo inteiro em metros × 10⁵ + índice), objetivo lexicográfico, deslocamentos, cancelamentos, jornadas e compromissos, sementes, critérios e métricas. Nenhuma correção de erro foi feita nesta reorganização; qualquer correção futura deve ser registrada à parte.

## 5. Verificações de equivalência (não são novos testes científicos)

| Verificação | Resultado | Evidência |
|---|---|---|
| Sintético: 3 pares (S1/20001, S3/20007, S2_frota_escassa/20040), A, B, C, 7 colunas | **idêntico** | `scripts/check_equivalence.py --synthetic` → `reports/manifests/equivalencia_reorganizacao.json` |
| Histórico: 1 dia real (2026-09-16), A, B, C, todas as colunas e as esperas | **idêntico** (executado durante a reorganização; exige dados locais) | execução manual registrada nesta sessão; `check_equivalence.py --historical` repete com `TCC_REAL_DATA_AUTHORIZED=YES` |
| Análise: totais e contrastes de setembro e outubro regenerados dos Parquet congelados | **idênticos** (km por dia, byte a byte; contrastes e ICs com tolerância 1e-6) | `check_equivalence.py --analysis`; `tests/regression/test_frozen_results.py` |
| Sintético: `resumo_contrastes.csv` | **176 linhas idênticas** (diferença máxima 6e-14; classes iguais). As **88 linhas restantes** são contrastes do método `fluxo` (removido do código ativo; preservadas no arquivo congelado) | `tests/regression/test_frozen_results.py` |
| Suíte de testes | 189 aprovados, 0 pulados, 0 falhos | `python -m pytest` |
| Lint e formatação | `ruff check` sem erros; `ruff format --check` limpo | Ruff 0.17.3 |
| Notebooks (kernel limpo, cima→baixo) | 5/5 executam | `reports/manifests/notebooks_execucao.json` |

Limitação: apenas **1 dia real** e **3 pares sintéticos** foram reexecutados; a equivalência dos demais dias decorre da identidade de código no caminho exercitado, não de reexecução completa.

## 6. Artigo

O artigo novo passou de `tcc-artigo-latex/atribuicao/` para `article/` (cópia de segurança do estado anterior na pasta de preservação). O artigo antigo em `tcc-artigo-latex/` não foi alterado.

## 7. Pendências reais

* Reexecução completa dos 40 dias históricos e das 880 execuções sintéticas pelo código novo **não** foi feita (nem exigida); só amostras de equivalência.
* `uv.lock` foi regenerado (`uv lock`); a verificação de instalação limpa a partir dele não foi feita.
* O teste histórico de equivalência com portão exige que o proprietário libere `TCC_REAL_DATA_AUTHORIZED=YES`.

## Arquivamento da rodada 4 (09/11/2026)

Saíram da árvore ativa, com cópia em `..\tcc-otimizacao-frota_preservacao_2026-11-09\rodada4_arquivamento\` (checksums em `SHA256.txt` e `tcc-artigo-latex.SHA256.txt`): `docs_antigos/`, `regras_de_negocio/`, `tabelas/` (zips; também estão no commit `3e77cb9`), `tcc-artigo-latex/` (repositório aninhado movido inteiro, com o `.git`) e quatro documentos de métodos abandonados (`AUDITORIA_OBJETIVO_GULOSO`, `PLANO_GULOSO_LIQUIDO`, `INVENTARIO_IMPLEMENTACOES`, `PLANO_COMPARACAO_ALGORITMOS`). Menções a esses caminhos em outros documentos são históricas.
