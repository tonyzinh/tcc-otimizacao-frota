# Reprodutibilidade

Caminhos e comandos válidos desde a reestruturação de 09/11/2026 (`docs/repository_migration.md`). Use o Python do ambiente do projeto (`.venv\Scripts\python.exe` no Windows).

## Ambiente

Python 3.12. As dependências estão em `pyproject.toml` e travadas em `uv.lock`; o Ruff está fixado em 0.17.3.

```bash
uv sync --extra test --extra quality --extra notebooks      # ou: pip install -e ".[test,quality,notebooks]"
python -m pytest                                            # 207 testes em 09/11/2026 (alguns pulam sem dados locais)
python -m ruff check src tests scripts && python -m ruff format --check src tests scripts
```

O comando `tcc-frota` equivale a `python -m tcc_frota.cli.main`. Depois de renomear módulos, reinstale o pacote (`pip install -e .` ou `uv sync`) para atualizar o ponto de entrada.

## Obtenção dos dados

Nada em `data/` é versionado. Uma cópia nova do repositório não traz dados; cada pasta é obtida assim:

| Pasta | Conteúdo | Como obter | Quem pode |
|---|---|---|---|
| `data/geographic/` | Malhas do IBGE, vias do OpenStreetMap e rede viária (públicos) | `python scripts/download_geography.py`. As fontes e as datas ficam em `manifesto_geografia.json`. | qualquer pessoa |
| `data/raw/v1_viagens/` | Extração pseudonimizada (HMAC-SHA256), somente leitura, por fonte, entidade e dia, com `manifest.json` por lote | `scripts/extract_v1_period.sh`, `extract_v1_campaign.sh` e `extract_v1_campaign_es.sh`. Eles usam `python -m tcc_frota.data.extraction`, credenciais de leitura no `.env` local e o segredo de pseudonimização em `%LOCALAPPDATA%\tcc_frota\segredos` (fora do repositório; ver `docs/data_dictionary.md`). | só o proprietário, com acesso às fontes da empresa |
| `data/raw/v1_viagens_schema1_20261108/`, `data/raw/v1_viagens_previous_salt_20261106/` | Extrações substituídas, guardadas como evidência | não são regeneradas; só existem na cópia local do proprietário | — |
| `data/processed/world_cache/` | Cache dos mundos simulados por dia | Regenerado automaticamente por `run-historical` a partir de `data/raw/` | quem tiver `data/raw/` e a autorização |
| `data/processed/run_outputs/`, `data/processed/data_quality_samples/` | Logs e amostras individuais de execuções antigas | não são regenerados; servem de evidência local | — |

A identidade dos arquivos usados nos resultados está versionada sem os dados em `reports/manifests/data_checksums.csv` (caminho, bytes e SHA-256). O manifesto de 09/11/2026 tem 8.917 arquivos e 912.619.816 bytes.

- `python scripts/data_checksums.py --check` confere se uma cópia local é a mesma.
- `python scripts/data_checksums.py` regenera o manifesto. Regenere-o só quando a mudança dos dados for intencional e registrada em `docs/decisions.md`.

O gancho `scripts/check_data_files.py`, ligado em `.pre-commit-config.yaml`, impede commit de arquivos em `data/`, de formatos de dados (Parquet, pickle, SQLite...), de segredos (`.env`, chaves, sal, `configs/private/`) e de arquivos com mais de 5 MB. Para ativá-lo: `pip install pre-commit && pre-commit install`. Sem o pre-commit, rode `python scripts/check_data_files.py --staged`.

## Sintético (sem dados privados)

Exige `data/geographic/` (IBGE e OSM). `python scripts/download_geography.py` baixa esses dados de fontes públicas.

```bash
python -m tcc_frota.cli.main run-synthetic --scenarios S1,S2 --seeds 101-105 --out reports/examples/synthetic_new
python -m tcc_frota.cli.main analyze-synthetic --input reports/examples/synthetic_new --out reports/examples/synthetic_new/analise
```

## Histórico (dados privados, só local)

Exige duas coisas:

- a extração local em `data/raw/v1_viagens/`, feita pelos scripts `scripts/extract_v1_*.sh`;
- `TCC_REAL_DATA_AUTHORIZED=YES`, que só o proprietário levanta.

Nada disso vai para serviço externo.

```bash
python -m tcc_frota.cli.main analyze-historical --out data/processed/historical_analysis   # lê os Parquet congelados (agregado; sem dados brutos)
python -m tcc_frota.cli.main run-historical --period final --days 2026-10-01 --out data/processed/run_outputs/new_run
```

O CLI **recusa** gravar em `reports/historical/`, `reports/synthetic/` e `reports/diagnostics/`. Saídas com registros individuais vão para `data/processed/`. Agregados novos vão para uma pasta nova em `reports/`.

## Conferência dos resultados congelados

```bash
python scripts/verify_frozen_results.py
```

O script confere três conjuntos e grava o resultado em `--out`:

- os 19 hashes do pré-registro (`reports/tcc_final`, hoje fora da árvore);
- os 138 arquivos versionados dos conjuntos congelados, comparados com os blobs do commit 3e65f3b;
- os 40 Parquet da avaliação congelada.

Os caminhos antigos são resolvidos por `reports/manifests/repository_restructure/path_map.csv`. O estudo anterior é lido da cópia de preservação (`--archive`). O script sai com código 1 se qualquer item falhar.

A análise da recalibração (`scripts/analyze_recalibration_out_of_sample.py`) tem uma trava que confere o SHA-256 dos arquivos de código congelados. Depois da reestruturação, essa trava aceita os arquivos alterados só pelo registro revisado `reports/manifests/repository_restructure/frozen_code_equivalence.json`, cujos diffs estão em `frozen_code_diffs/`.

## Equivalência com os resultados congelados

```bash
python scripts/check_equivalence.py --synthetic --analysis --out data/processed/equivalence.json
```

Ver `docs/repository_migration.md` para o alcance e as limitações.

**`--historical` executado em 09/11/2026**, com autorização do proprietário para essa execução. Rodaram os 40 dias da avaliação congelada (15 de setembro e 25 de outubro) e todos deram equivalentes: 0 diferenças em todas as colunas e nas esperas (`reports/manifests/repository_restructure/equivalence_historical_40days.json`; os 2 dias padrão estão em `equivalence_historical_2days.json`). Os arquivos contêm só nomes de colunas divergentes e tempos, sem registros.

| Pergunta | Resposta |
|---|---|
| O que lê | Parquet **privados** de `data/raw/v1_viagens/` (pedidos, jornadas, compromissos, posições) dos dias indicados em `--historical-days` (padrão: 2026-09-16 e 2026-10-01). Lê também os resultados congelados de `reports/historical/frozen_evaluation/execucao/`. |
| O que executa | Reconstrói o mundo desses dias e roda A, B e C com o código atual (`simulation/historical.py`). Compara o resultado, linha a linha, com o congelado. Não roda os 40 dias. |
| Fontes remotas | Nenhuma: só arquivos locais. |
| Bloqueio | Exige `TCC_REAL_DATA_AUTHORIZED=YES` (`src/tcc_frota/data/authorization.py`), portão que só o proprietário levanta. Para executar: `TCC_REAL_DATA_AUTHORIZED=YES python scripts/check_equivalence.py --historical --out data/processed/equivalence_historical.json`. |

## Notebooks

Os notebooks são `notebook/01…05_*.ipynb`. Rode em kernel limpo, de cima para baixo, com `python scripts/run_notebooks.py`, que grava `reports/manifests/notebooks_execucao.json`.

A parte sintética não precisa de credenciais. Sem os dados privados, os notebooks usam só os agregados congelados e explicam como obtê-los.

## Artigo

Em `article/`, rode XeLaTeX, depois BibTeX, depois XeLaTeX duas vezes (ver `article/README.md`).
