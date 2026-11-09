# Atribuição conjunta de pedidos a veículos em lotes (algoritmo Húngaro) e km vazio

Trabalho de conclusão de curso. Artigo: **Despacho em lotes com atribuição conjunta pelo algoritmo Húngaro: avaliação por simulação do km vazio em aplicativos de transporte** (`article/`). O repositório avalia, por **simulação**, se atribuir pedidos a veículos de forma **conjunta** (algoritmo Húngaro, lotes de 60 s) reduz o **km vazio** (aproximação do veículo até o passageiro) em relação ao despacho pelo mais próximo livre, sem piorar o atendimento.

## O método e as três políticas

| Id | Política | Papel |
|---|---|---|
| **A** | mais próximo livre, despacho imediato | referência (baseline simplificado calibrado; **não** é a operação manual) |
| **B** | mais próximo livre, lotes de 60 s | controle: isola o efeito do lote |
| **C** | atribuição conjunta pelo Húngaro, lotes de 60 s | método principal |

A cada lote, C maximiza o número de pedidos atendidos e, entre as soluções com esse máximo, minimiza a soma das distâncias de aproximação (Kuhn–Munkres, implementação própria). O ótimo é **do lote**, não do dia. Contraste principal: **C × A**; complementar: C × B.

## Resultados (evidência citável em `reports/`)

* **Histórico** (dados privados da V1 Viagens, simulação, km estimado): setembro, C × A **−5,96%** de km vazio (+16 atendidos); outubro, C × A **−5,04%**, mas **−85 atendidos** (14.466 vs 14.551 de 23.523; −0,36 p.p. do universo elegível, ≈ −0,58% dos atendidos de A) e o critério de serviço E2 **não foi cumprido**. C × B: −2,74% (set.) e −1,40% (out.), com atendimento preservado.
* **Sintético** (rede OpenStreetMap, 22 cenários **não independentes**, sementes finais examinadas antes da decisão): mediana −8,4% contra A. Complementar e exploratório.
* Limites: simulação, não operação real; km estimado; resultado de uma empresa e região.

Detalhes e ressalvas: [`docs/methodology.md`](docs/methodology.md). Resultados congelados: `reports/historical/frozen_evaluation/` e `reports/synthetic/dispatch_evaluation/`. Análises posteriores (recalibração, teste fora da amostra, guloso global, sensibilidades): `reports/diagnostics/`.

## Estrutura

```
src/tcc_frota/   domain · data · assignment · simulation · scenarios · metrics · visualization · cli
configs/         data · policies · scenarios · experiments · private (ignorado pelo Git)
tests/           unit · integration · regression · reproducibility · fixtures
notebook/        01_data_overview · 02_hungarian_example · 03_greater_vitoria_h3 · 04_historical_results · 05_synthetic_results
scripts/         extração local (.sh), geografia, análises posteriores, figuras, equivalência, verificação dos congelados
docs/            architecture · data_dictionary · data_quality · availability · methodology · validation · reproducibility · decisions · repository_migration
data/            raw/ (extrações, privado) · processed/ (cache e saídas individuais) · geographic/ (IBGE/OSM) — nada versionado
reports/         historical/ · synthetic/ · diagnostics/ · data_quality/ · figures/ · manifests/ · examples/
article/         artigo (LaTeX) e PDF
```

## Instalação

Python **3.12**. Com [uv](https://docs.astral.sh/uv/), preservando o `uv.lock`: `uv sync --frozen --extra test --extra quality --extra notebooks`; ou `pip install -e ".[test,quality,notebooks]"` (sem o lock).

| Grupo | Onde está declarado | Conteúdo |
|---|---|---|
| Execução | `dependencies` | numpy, pandas, pyarrow, scipy, h3, matplotlib, tzdata |
| Desenvolvimento | extras `test`, `quality` | pytest, pytest-cov, Ruff (versão fixa) |
| Notebooks e mapa | extra `notebooks` | jupyter_client, ipykernel, nbformat, nbclient, folium |
| Fontes privadas | extra `fontes` | pyodbc (exige driver ODBC; só com o portão de dados reais) |
| Compilação do artigo | **fora do `uv.lock`** | XeLaTeX, BibTeX, `latexmk` e a fonte Arial (MiKTeX ou TeX Live) |

## Testes e qualidade

```bash
python -m pytest
python -m ruff check . && python -m ruff format --check .
```

## Exemplo rápido (sintético, sem dados privados)

Precisa de `data/geographic/` (`python scripts/download_geography.py`, fontes públicas).

```bash
python -m tcc_frota.cli.main run-synthetic --scenarios S1 --seeds 101-103 --out reports/examples/synthetic_quick
python -m tcc_frota.cli.main analyze-synthetic --input reports/examples/synthetic_quick --out reports/examples/synthetic_quick/analise
```

## Reproduzir a análise e as figuras

```bash
python -m tcc_frota.cli.main analyze-historical --out data/processed/historical_analysis   # a partir dos Parquet congelados (locais)
python scripts/check_equivalence.py --synthetic --analysis --out data/processed/equivalence.json
python scripts/verify_frozen_results.py                          # SHA-256 dos congelados pelo mapa de caminhos
```

## Notebooks

`python scripts/run_notebooks.py` executa os cinco cadernos em kernel limpo. Os cadernos de resultados leem só agregados congelados; o 03 desenha o mapa H3 do recorte (dados públicos).

## Artigo

`article/` (XeLaTeX + BibTeX; ver `article/README.md`). PDF: `article/ARTIGO_ATRIBUICAO_HUNGARO.pdf`.

## Dados privados e autorização

Dados reais da empresa: **só processamento local e agregado**; nada de dados brutos, identificadores de motoristas ou coordenadas individuais em logs, commits ou serviços externos. `data/` é ignorado pelo Git. A execução sobre dados reais exige `TCC_REAL_DATA_AUTHORIZED=YES`, liberado só pelo proprietário. Sem os dados, as partes sintética e agregada continuam reproduzíveis.

## Limitações

Simulação com km estimado (reta × 1,3012 na linha histórica; Dijkstra sobre OSM na sintética); baseline simplificado; disponibilidade reconstruída retrospectivamente; parâmetros herdados da calibração de março; ótimo por lote ≠ ótimo diário; sem implantação nem efeito operacional medido.

## Histórico

O estudo anterior (reposicionamento preventivo D+1 e a bateria de 13 algoritmos, sem redução de km vazio) saiu da árvore ativa em 09/11/2026 e está preservado fora dela, com SHA-256 por arquivo; os hashes continuam conferidos por `scripts/verify_frozen_results.py`. Ver [`docs/repository_migration.md`](docs/repository_migration.md).
