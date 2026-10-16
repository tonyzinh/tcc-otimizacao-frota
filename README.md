# Otimização da Alocação de Frota em Aplicativos de Transporte Urbano

TCC sobre redução de KM morto por alocação preventiva D+1. O experimento sintético local permanece como validação de software e referência histórica. A etapa de **disponibilidade operacional** usa os nove CSVs autorizados atualmente presentes em `data/`; também aceita Parquets futuros. Ela executa diagnóstico, linha do tempo conservadora, baseline D+1 de candidatura e região proxy para veículos com Cobli recente e vínculo temporal único. Ainda não produz disponibilidade individual confirmada nem região futura validada.

## Disponibilidade operacional

Consulte [arquitetura, regras e execução](docs/disponibilidade.md) e [dicionário de entrada](docs/disponibilidade_dicionario.md). Os comandos locais `tcc-frota-disponibilidade audit`, `relationships`, `reconstruct` e `forecast-candidates` são descritos no guia. `Online` indica aptidão para receber corrida; uma corrida ou indisponibilidade ativa prevalece. Resultados sem evidência suficiente ficam `DESCONHECIDO`. O corte D+1 é parâmetro explícito; 20h local é hipótese experimental inicial.

## Rodada final (v2): extratos de jan–mar e jul–set/2026

Um único comando reproduz todas as tabelas e figuras do capítulo de resultados a partir dos extratos em `data/raw/` (fora do Git):

```powershell
python -m pip install -e ".[test,v2]"
$env:TCC_REAL_DATA_AUTHORIZED = 'YES'          # autorização de processamento local
tcc-frota prepare-raw --raw data/raw           # confere os quatro lotes contra os manifestos
tcc-frota final-run --raw data/raw --out reports/runs/tcc_final --publish reports/tcc_final
```

O sal da pseudonimização vem de `TCC_PSEUDO_SALT` ou de `data/.pseudo_salt` (≥ 16 caracteres, fora do Git). A saída individual fica em `reports/runs/tcc_final/<run_id>/` (ignorada); só os agregados vão para [`reports/tcc_final/`](reports/tcc_final/). **Resultado:** em março e setembro de 2026, nenhuma configuração reduziu o KM vazio estimado por corrida; o atendimento simulado subiu até cerca de 2–3% com escala conhecida, a um custo de 10 a 138 km vazios por corrida extra. Leia [resultados reais](docs/resultados_reais.md), [perguntas prováveis da banca](docs/perguntas_banca.md), [medalhão v2](docs/databricks_medalhao.md) e [limitações](docs/limitacoes.md).

**Visualização (FleetLab):** `tcc-frota fleetlab-export` e `tcc-frota fleetlab-serve` levam os resultados reais ao frontend em `frontend/`, só na máquina local; veja [frontend/README.md](frontend/README.md).

## Experimento D+1 com dados reais (legado, setembro/2026, DT011–DT012)

A Gold do Databricks alimenta o núcleo Python (`tcc-frota gold-export` e `tcc-frota gold-replay`). Em setembro/2026, nenhuma configuração do plano preventivo reduziu o KM vazio estimado em relação ao baseline sem reposicionamento. Veja o [experimento real](docs/experimento_real.md) e a [comparação de algoritmos](docs/comparacao_algoritmos.md). Para visualizar o plano no mapa: `streamlit run app/plano_d1.py --server.address 127.0.0.1` (extra `ui`).

## Execução local

Requer Python 3.12 e pytest. Na raiz do repositório:

```powershell
python -m pip install -e ".[test,excel]"
python -m pytest
tcc-frota build-synthetic-data --out reports/runs/medallion
tcc-frota run-synthetic --out reports/runs
```

Sem instalação editável, configure `PYTHONPATH=src` e use `python -m tcc_frota.cli`. Os comandos acima só geram ou processam dados sintéticos. O [relatório executado](docs/resultados.md) mediu **0,0% de redução** do KM vazio *estimado* no exemplo padrão; a economia de pickup igualou o reposicionamento. Não é medição da empresa.

## Estrutura

- `src/tcc_frota/`: núcleo local, gerador, ingestão, qualidade, demanda, otimização, simulação e avaliação.
- `tests/`: testes unitários e integração sintética.
- `src/tcc_frota/v2/`: rodada final — lotes e manifestos, regras de limpeza, Silver/Gold locais, previsão, regimes de frota, simulador com fila, algoritmos, estatística, figuras e `final-run`.
- `databricks/catalog/`: notebooks `nb_*_v2` (Bronze, Silver e Gold dos extratos paginados) e os legados `.ipynb`; `databricks/setup/executar_notebooks.py bronze silver gold` executa a v2 via Databricks Connect. Consulte o [medalhão](docs/databricks_medalhao.md).
- `config/`: parâmetros e contratos do cenário experimental.
- `reports/examples/`: [JSON](reports/examples/synthetic_run.json) e [gráfico SVG](reports/examples/synthetic_comparison.svg) gerados localmente.

## Documentação versionada

- [Arquitetura](docs/arquitetura.md), [metodologia](docs/metodologia.md), [algoritmo](docs/algoritmo.md) e [simulação](docs/simulacao.md).
- [Indicadores](docs/indicadores.md), [resultados sintéticos](docs/resultados.md), [limitações](docs/limitacoes.md) e [segurança dos dados](docs/seguranca_dados.md).
- [Guia de execução no Databricks](docs/execucao_databricks.md).

O levantamento de regras operacionais, as decisões internas e o estado detalhado do projeto são mantidos localmente e ficam fora do Git. Eles precisam ser obtidos por canal autorizado antes de interpretar os dados da empresa ou alterar hipóteses operacionais.

Os CSVs reais em `data/` e os resultados individuais em `reports/runs/` estão fora do Git. O usuário autorizou o processamento local dos CSVs; nenhum comando de disponibilidade faz upload. Os notebooks Databricks permanecem específicos para Parquet em Volume e **não executam** estes CSVs. Consulte [segurança](docs/seguranca_dados.md).
