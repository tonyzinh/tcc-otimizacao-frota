# Reprodutibilidade

## Ambiente

Python 3.12; dependências em `pyproject.toml`, travadas em `uv.lock`. Ruff fixado em 0.17.3.

```bash
uv sync --extra test --extra quality --extra notebooks      # ou: pip install -e ".[test,quality,notebooks]"
python -m pytest                                            # 195 testes (alguns pulam sem dados locais)
python -m ruff check src tests scripts && python -m ruff format --check src tests scripts
```

## Sintético (sem dados privados)

Exige `data/geografia/` (IBGE + OSM; `python scripts/baixar_geografia.py` baixa de fontes públicas).

```bash
tcc-frota run-synthetic --scenarios S1,S2 --seeds 101-105 --out reports/final/sintetico_novo
tcc-frota analyze-synthetic --input reports/final/sintetico_novo --out reports/final/sintetico_novo/analise
```

## Histórico (dados privados, só local)

Exige a extração local em `data/extraido/v1_viagens/` (scripts `extrair_v1_*.sh`) e `TCC_REAL_DATA_AUTHORIZED=YES`, que só o proprietário levanta. Nada disso vai para serviço externo.

```bash
tcc-frota analyze-historical --out reports/final/historico    # lê os Parquet congelados (agregado; sem dados brutos)
tcc-frota run-historical --period final --days 2026-10-01 --out reports/final/execucao_nova
```

O CLI **recusa** gravar em `reports/atribuicao_final/`, `reports/sintetico_v2/` e `reports/tcc_final/`.

## Equivalência com os resultados congelados

```bash
python scripts/check_equivalence.py --synthetic --analysis     # grava reports/manifests/equivalencia_reorganizacao.json
```

Ver `docs/repository_migration.md` (§5) para o alcance e as limitações.

**Ainda não executado: `--historical`.**

| Pergunta | Resposta |
|---|---|
| O que lê | Parquet **privados** de `data/extraido/v1_viagens/` (pedidos, jornadas, compromissos, posições) dos dias indicados em `--historical-days` (padrão: 2026-09-16 e 2026-10-01) e os resultados congelados de `reports/atribuicao_final/execucao/`. |
| O que executa | Reconstrói o mundo desses dias e roda A, B e C com o código reorganizado (`simulation/historical.py`); compara o resultado, linha a linha, com o congelado. Não roda os 40 dias. |
| Fontes remotas | Nenhuma: só arquivos locais. |
| Verificação adicional | Dois dias reais (um por período) além do dia de 16/09 já conferido; confirma que o carregamento e a reconstrução dos dados reais continuam idênticos, algo que a amostra sintética e a regeneração das tabelas não cobrem. |
| Bloqueio | Exige `TCC_REAL_DATA_AUTHORIZED=YES` (`data/authorization.py`), portão que só o proprietário levanta. **Não foi levantado nesta rodada.** Para executar: `TCC_REAL_DATA_AUTHORIZED=YES python scripts/check_equivalence.py --historical` (o resultado é gravado em `reports/manifests/equivalencia_reorganizacao.json`, sobrescrevendo o anterior; guarde uma cópia antes). |

## Notebooks

`notebook/01…05_*.ipynb`, em kernel limpo e de cima para baixo: `python scripts/run_notebooks.py` (grava `reports/manifests/notebooks_execucao.json`). Sem credenciais para a parte sintética; sem os dados privados, os cadernos usam só os agregados congelados e imprimem como obtê-los.

## Artigo

`article/`: XeLaTeX → BibTeX → XeLaTeX ×2 (ver `article/README.md`).
