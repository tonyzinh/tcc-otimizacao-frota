# Registro da reorganização do repositório (09/11/2026)

Reorganização em torno de **um único método principal**: atribuição conjunta pelo algoritmo Húngaro em lotes de 60 s (política C), comparada com A (mais próximo livre, despacho imediato) e B (mais próximo livre, lotes de 60 s). Este documento é o registro do que foi movido, removido, preservado e verificado. Nada foi commitado nem colocado no stage.

> As seções 1 a 7 e o arquivamento da rodada 4 descrevem as etapas anteriores, com os caminhos da época. A estrutura de pastas vigente é a da **seção 8** (reestruturação de 09/11/2026, à noite). Nela, as pastas que a §2 diz terem mantido o nome antigo foram renomeadas, e o estudo anterior saiu da árvore.

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

## 8. Reestruturação de pastas e nomes (09/11/2026, à noite)

**Objetivo:** ter uma única raiz de resultados, um único padrão de nomes (inglês e `snake_case` para pastas, código e nomes de documentos; conteúdo em português) e dados separados de agregados. Nenhum número científico mudou, e nada foi commitado nem colocado no stage.

### 8.1 Preservação (etapa 0)

A cópia fica em `../tcc-otimizacao-frota_preservacao_2026-11-09/copia_completa_pre_migracao/` e contém:

- `repo/`: cópia completa da árvore, sem `.venv` e caches. São 21.463 arquivos e 1.103.907.287 bytes, iguais aos da árvore original;
- `SHA256_por_arquivo.csv`;
- `estado_antes/`: HEAD, status, `ls-files` e diff do Git; o PDF do artigo com o texto e os números extraídos; os hashes dos congelados; a saída do pytest;
- `LEIA-ME.md`, que registra a restauração de amostra (478 de 478 arquivos idênticos).

### 8.2 Mapa de caminhos

O mapa de caminhos está em `reports/manifests/repository_restructure/`:

| Arquivo | Conteúdo |
|---|---|
| `path_map.csv` | 78 entradas de dados e relatórios, com caminho antigo, caminho novo e motivo. Depois da mudança, todos os 21.463 arquivos foram reencontrados no caminho novo com o mesmo SHA-256. |
| `code_rename_map.csv` | 20 módulos, testes e scripts renomeados |
| `frozen_code_equivalence.json` e `frozen_code_diffs/` | Os 4 arquivos de código cobertos pela trava da calibração da rodada 5 que mudaram só em caminhos, imports e docstrings. Os diffs foram revisados. |
| `frozen_check_stage1.csv` | Saída de `scripts/verify_frozen_results.py` |
| `equivalence_stage1.json`, `equivalence_stage2.json` | Equivalência sintética e da análise depois de cada etapa |
| `inventory_after.csv` | Contagem de arquivos e bytes por pasta depois da reestruturação |
| `article_rename_map.csv` | Seções, referências, apêndices, relatórios editoriais e figuras do artigo (etapa 4) |
| `article_comparison_stage4.json` | Comparação do PDF do artigo antes e depois (texto, números, páginas, log) |
| `frozen_check_final.csv`, `equivalence_final.json` | Conferência dos congelados e equivalência na validação final |
| `git_history_audit.csv` | Achados da auditoria do histórico Git, sem valores (§9) |
| `../data_checksums.csv` | SHA-256 e bytes de cada arquivo de `data/` (8.917 arquivos), sem dados |

Principais mudanças (lista completa nos mapas):

| Antes | Depois |
|---|---|
| `data/extraido/` | `data/raw/` (`v1_viagens`, `v1_viagens_schema1_20261108`, `v1_viagens_previous_salt_20261106`) |
| `data/geografia/` | `data/geographic/` |
| `reports/runs/cache_comparacao/`, demais `reports/runs/` | `data/processed/world_cache/`, `data/processed/run_outputs/`, `data/processed/data_quality_samples/` |
| `reports/atribuicao_final/` | `reports/historical/frozen_evaluation/` |
| `reports/comparacao/`, `ab_desenvolvimento*`, `referencia_fatia_*` | `reports/historical/development/…` |
| `reports/sintetico_v2/metodos_avaliacao_D/` | `reports/synthetic/dispatch_evaluation/` |
| demais `reports/sintetico_v2/`, `reports/sintetico/` | `reports/synthetic/…` |
| `reports/pos_hoc_parecer/` (rodadas 4 a 9) | `reports/diagnostics/{statistics,calibration,consistency,batching,availability}/…`, cada pasta com `provenance.json` |
| `reports/extracao_v1_viagens/`, `reports/revisao/` | `reports/data_quality/…`, `reports/manifests/code_formatting_review/` |
| `scripts/pos_hoc_*.py`, `figura_rodada5.py`, `baixar_geografia.py`, `verificar_bases_reais.py`, `extrair_v1_*.sh` | `analyze_*.py`, `plot_recalibration_daily_differences.py`, `download_geography.py`, `validate_historical_data.py`, `extract_v1_*.sh` |
| `data/extraction/{entidades,filtro,qualidade,saida,executor}.py`, `privacy/pseudonimizacao.py`, `data/timeutil.py`, `reading/{es,sqlserver}.py` | `entities`, `filters`, `quality`, `writer`, `runner`, `pseudonymization`, `time_utils`, `elasticsearch`, `sql_server` |
| `docs/` (16 documentos em português maiúsculo) | `docs/{architecture,data_dictionary,data_quality,availability,methodology,validation,reproducibility,decisions,repository_migration}.md`; o conteúdo de origem foi preservado em seções com a linha "Origem" |

### 8.3 O que saiu da árvore (sem exclusão de dados)

O estudo anterior saiu da árvore e foi para `../tcc-otimizacao-frota_preservacao_2026-11-09/estudo_anterior_retirado_da_arvore/`. Isso inclui:

- o reposicionamento D+1, a bateria de 13 algoritmos e o seletivo;
- as pastas `reports/tcc_final/`, `reports/tcc_v2/`, `resultados/`, `reports/thesis_audit/`, `reports/final_release/`, `reports/validation_current/` e os arquivos de 28/10 de `reports/repository_migration/`.

Os 19 hashes do pré-registro desses arquivos continuam conferidos por `scripts/verify_frozen_results.py --archive`.

Diagnósticos desfavoráveis e análises posteriores que sustentam limitações do artigo **ficaram** na árvore:

- `historical/development/repositioning_selection`;
- `synthetic/repositioning_evaluation`;
- `synthetic/repositioning_greedy_study`;
- `diagnostics/`.

### 8.4 Exceções de nome

Os nomes abaixo continuam como estavam porque são contratos gravados ou nomes externos:

- `v1_viagens`, o nome da origem dos dados (R-34);
- o pacote `tcc_frota` e a pasta `notebook/`;
- os identificadores de política, as colunas e as chaves gravadas nos resultados (`extraido_em`, `pseudonimizacao`, `dia=`, `cen=…__sem=…`);
- os nomes de arquivos dentro dos conjuntos movidos (`RELATORIO_*.md`, `PLANO.md`, `analise/`, `execucao/`);
- as tabelas, campos e serviços das fontes.

As entradas antigas de `decisions.md` e os relatórios das rodadas citam os caminhos da época. O mapa resolve esses caminhos.

**Atenção a `data/raw/`:** antes de 09/11/2026, `data/raw/` era outra pasta, o extrato bruto antigo, apagado em 08/11 (ver `data_dictionary.md`). Desde a reestruturação, `data/raw/` é a antiga `data/extraido/`. Menções a `data/raw/` em entradas anteriores a R-35 referem-se à pasta antiga.

### 8.5 Verificações

| Verificação | Resultado |
|---|---|
| Arquivos movidos | 21.463 de 21.463 com o mesmo SHA-256 no caminho novo |
| Congelados (`verify_frozen_results.py`) | 19/19 hashes do pré-registro, 138/138 arquivos versionados iguais aos blobs de 3e65f3b, 40/40 Parquet; 0 falhas |
| Trava da calibração congelada | aceita, pelo registro de equivalência |
| Testes | 203 aprovados, 0 pulados, 0 falhos |
| Ruff | `check` e `format --check` limpos |
| Sintético e análise (`check_equivalence.py --synthetic --analysis`) | equivalentes |
| Exemplo sintético (`run-synthetic --scenarios S1 --seeds 101`) | executado |
| Equivalência histórica com dados reais | **executada depois** (R-36): 40 de 40 dias equivalentes, 0 diferenças (`equivalence_historical_40days.json`) |

**Etapa 4 (artigo):**

- **Arquivos renomeados:** as seções passaram a `00_abstract` … `05_conclusion`, e também foram renomeados `appendices.tex`, `references.bib`, `compliance_report.md`, `reference_audit.md` e `review_response.md`.
- **Figuras:**
  - A origem oficial passou a ser `reports/figures/`, com nomes por conteúdo.
  - As cópias em `article/figures/` são geradas e conferidas por `scripts/sync_article_figures.py`, que também roda no teste `test_article_figures.py`.
  - As cópias antigas do artigo foram para a preservação (`artigo_figuras_substituidas_2026-11-09/`).
- **Apêndice D:** só os caminhos mudaram.
- **Compilação:**
  - 37 páginas, como antes, com o corpo nas p. 2–23 e o mesmo mapa de seções;
  - 0 caixas estouradas e 0 referências ou citações indefinidas, iguais ao antes.
- **Números do PDF:** nenhum valor mudou. Saíram do texto só 9 dígitos de nomes de pastas antigas (`sintetico_v2`, `rodada5`…`rodada8`) (`article_comparison_stage4.json`).

**Validação final (09/11/2026):**

| Verificação | Resultado |
|---|---|
| Testes (`.venv`) | 207 aprovados, 0 pulados, 0 falhos (203 + figuras do artigo + 3 do gancho de dados) |
| Instalação limpa a partir do `uv.lock` em ambiente separado (`uv sync --frozen --extra test`) | 207 aprovados. `tcc-frota --help` e `tcc-frota run-synthetic --scenarios S1 --seeds 101` funcionaram. |
| Ruff | `check` e `format --check` limpos (76 arquivos) |
| Congelados | 19/19, 138/138, 40/40; 0 falhas (`frozen_check_final.csv`) |
| Equivalência sintética e da análise | equivalente (`equivalence_final.json`) |
| Notebooks (`run_notebooks.py`, kernel limpo) | 5/5 ok. As figuras regravadas pelos notebooks 04 e 05 tinham texto e PNG idênticos e só a data de criação diferente no PDF; os bytes originais foram restaurados. |
| Figuras do artigo | 3/3 iguais à origem |
| Dados | `data_checksums.py --check`: 0 ausentes, 0 novos e 0 diferentes. Antes e depois: 8.917 arquivos e 912.619.816 bytes. |
| Contagem da árvore | Sem `.git`, `.venv`, caches e `__pycache__`, eram 19.198 arquivos antes e são 19.033 depois. 18.853 arquivos foram movidos com o mesmo conteúdo. Os 235 que saíram são 188 do estudo anterior (preservados fora), mais documentos e regras consolidados e arquivos alterados só em caminhos (originais na cópia pré-migração). |

### 8.6 Pendências

- O ponto de entrada `tcc-frota.exe` do `.venv` era anterior à reorganização e falhava. **Resolvido:** o pacote do projeto foi reinstalado (`uv pip install -e . --no-deps`), e o `tcc-frota` funciona.
- Os scripts grandes de análise posterior (`analyze_robustness_review.py`, `analyze_recalibration_out_of_sample.py`) ainda têm regras reutilizáveis que não foram movidas para o pacote. Movê-las alteraria arquivos cobertos pela trava da calibração e exigiria uma nova equivalência.
- **Rodada 9:** usou scripts locais da sessão. Ela fez só a anonimização do texto, sem números novos.
- **Rodada 6:** os números do artigo que ela calculou com scripts de sessão (participação do km vazio, km evitado por dia, atendidos por dia no treino, setembro e outubro) agora vêm de `scripts/compute_article_derived_values.py`. O script recalcula os 21 valores a partir dos dados por dia versionados, e todos conferem com o texto e com os resumos (`reports/diagnostics/consistency/article_derived_values/`, teste `tests/regression/test_article_derived_values.py`). A conferência de hashes da rodada foi substituída por `scripts/verify_frozen_results.py`.

## 9. Proteção dos dados e auditoria do histórico Git (09/11/2026)

Nada foi commitado, colocado no stage nem enviado. O histórico não foi reescrito, e nenhum `git rm --cached` foi executado.

### 9.1 Situação do Git

- **Remoto:** `origin` = `https://github.com/tonyzinh/tcc-otimizacao-frota.git`. A visibilidade do repositório (público ou privado) **não foi verificada**: o `gh` não está instalado nesta máquina.
- **Ramos publicados:**
  - `main` (a888227) está em `origin/main`;
  - `v2-extensoes` está publicado até 3e77cb9;
  - o commit local 3e65f3b está um à frente e **não foi enviado**.
- **Histórico:** 234 commits e 1.269 blobs em todas as refs.

### 9.2 Busca em todo o histórico

A busca percorreu todas as refs (`git rev-list --all --objects`) e o conteúdo de cada blob. O resultado completo está em `reports/manifests/repository_restructure/git_history_audit.csv`, só com caminho, blob e tipo do achado, sem valores.

| Busca | Resultado |
|---|---|
| Arquivos de dados (Parquet, pickle, SQLite, planilhas, zip) | **nenhum** em todo o histórico |
| `data/` | nenhum arquivo de dados; só `data/synthetic/README.md` |
| `.env`, chaves, sal, `pseudo_secret`, `configs/private/` | **nenhum**; só `.env.example` e `frontend/.env.example`, com valores vazios ou `mock` e `127.0.0.1` |
| Chave privada, token do GitHub, Databricks ou AWS, sal atribuído | **nenhum** |
| "senha" em código | 4 blobs (`reading/es.py`, `reading/sqlserver.py` e versões antigas em `leitura/`). Todos são **falsos positivos**: `password=valores["PASSWORD"]` lê a variável do `.env` local. |
| Colunas com nomes sensíveis em CSV | 18 blobs, todos **agregados**: `tempo_ate_passageiro_dif_s`, `motoristas_mundo`, `fracao_motoristas_movidos_pct`, `nome` de cenário. Nenhum identificador nem coordenada. |
| Notebooks com saídas | 5 versões de `notebook/0x_*.ipynb`, com saídas só agregadas (tabelas de períodos e cenários, exemplo sintético, contagens). Os 11 notebooks antigos do Databricks não têm saídas. Nenhuma limpeza foi necessária. |
| Caminho local da máquina | 3 blobs de documentos antigos (`docs/DIAGNOSTICO_INICIAL.md`, `docs/PSEUDONIMIZACAO_E_VINCULOS.md`, `docs/REGISTRO_DECISOES.md`) com o caminho `C:\Users\<usuário>\OneDrive\...`, que expõe o nome de usuário da máquina. Não expõe dado da empresa. |

**Segredo de pseudonimização:**

- fica fora do repositório, em `%LOCALAPPDATA%\tcc_frota\segredos`;
- **não aparece no histórico**;
- os manifestos guardam só o `chave_id`, uma impressão de 12 caracteres, que não permite recuperar o segredo.

Portanto, **não há chave a tratar como comprometida** por esta busca. Fica uma ressalva: o arquivo `data/.pseudo_salt` do pipeline antigo esteve em pasta sincronizada pelo OneDrive (R-08, R-28). Essa exposição fica fora do Git e não pôde ser verificada daqui.

### 9.3 Na árvore de trabalho

- **`.gitignore`:** reescrito por pastas e padrões específicos: `/data/`, formatos binários de dados, segredos, `configs/private/`, contexto local dos agentes e saída do LaTeX. CSV e JSON não são ignorados em bloco. Correção feita durante a etapa: o padrão `data/` sem barra inicial também ignoraria `configs/data/` e `src/tcc_frota/data/`, e foi trocado por `/data/`.
- **Simulação de `git add -A --dry-run`** (nada foi colocado no stage):
  - 370 arquivos novos ou modificados e 416 remoções (caminhos antigos);
  - o verificador `scripts/check_data_files.py` não bloqueou nenhum;
  - o maior arquivo é `reports/manifests/data_checksums.csv` (1,3 MB).
- **Manifestos e relatórios em `reports/`:**
  - não há segredos;
  - nenhum CSV ou JSON tem identificador pseudonimizado nem coordenada individual. As coordenadas encontradas são do mapa público de H3 e dos cenários sintéticos;
  - caminho local apareceu em `frozen_check_stage1.csv`, regravado com caminhos relativos pelo próprio `verify_frozen_results.py`;
  - caminho local apareceu também no relatório da rodada 6. O original continua local, congelado e ignorado (`.gitignore`); a cópia versionada é `report_redacted.md`, só com o nome de usuário trocado.
- **Parquet de execução em `reports/`:** têm registros por pedido e continuam locais, ignorados por `*.parquet`. A identidade deles é conferida por `verify_frozen_results.py`.

### 9.4 Comandos propostos (não executados)

1. Ativar o bloqueio antes de qualquer commit:
   ```bash
   pip install pre-commit && pre-commit install
   python scripts/check_data_files.py --staged      # equivalente manual
   ```
2. Quando o proprietário decidir commitar a reestruturação, revise antes o que entra:
   ```bash
   git add -A --dry-run | less
   git add -A && python scripts/check_data_files.py --staged
   git commit -m "refactor: reestruturar pastas, nomes e documentação do repositório"
   ```
   As 416 remoções incluem o estudo anterior (`reports/tcc_final/`, `resultados/`...), que continua no histórico e na cópia de preservação.
3. **Opcional**, só se o nome de usuário nos três documentos antigos for considerado sensível. Isso reescreve o histórico e exige push forçado e coordenação com quem tiver clones. **Não recomendado** sem decisão do proprietário.
   ```bash
   pip install git-filter-repo
   echo 'regex:C:\\Users\\[^\\]+==>C:\\Users\\<usuario>' > ../replacements.txt
   git filter-repo --replace-text ../replacements.txt
   git push --force-with-lease origin main v2-extensoes
   ```
4. Conferir a visibilidade do remoto: `gh repo view tonyzinh/tcc-otimizacao-frota --json visibility` (depois de instalar o `gh`), ou abrir as configurações do repositório no GitHub.

Não há arquivo de dados nem segredo no índice. Por isso **nenhum `git rm --cached` é necessário**.

**Atualização (09/11/2026, à noite):** por pedido do proprietário, a reestruturação foi commitada e o `main` foi avançado até esse commit e publicado. O ramo remoto `origin/v2-extensoes` foi excluído; o ramo local foi mantido. O histórico não foi reescrito, e a opção 3 acima não foi aplicada.

