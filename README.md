# Otimização da Alocação de Frota em Aplicativos de Transporte Urbano

TCC sobre redução de KM morto por alocação preventiva D+1. O experimento sintético local permanece como validação de software e referência histórica. A etapa de **disponibilidade operacional** usa os nove CSVs autorizados atualmente presentes em `data/`; também aceita Parquets futuros. Ela executa diagnóstico, linha do tempo conservadora, baseline D+1 de candidatura e região proxy para veículos com Cobli recente e vínculo temporal único. Ainda não produz disponibilidade individual confirmada nem região futura validada.

## Disponibilidade operacional

Consulte [arquitetura, regras e execução](docs/disponibilidade.md) e [dicionário de entrada](docs/disponibilidade_dicionario.md). Os comandos locais `tcc-frota-disponibilidade audit`, `relationships`, `reconstruct` e `forecast-candidates` são descritos no guia. `Online` indica aptidão para receber corrida; uma corrida ou indisponibilidade ativa prevalece. Resultados sem evidência suficiente ficam `DESCONHECIDO`. O corte D+1 é parâmetro explícito; 20h local é hipótese experimental inicial.

## Execução local

Requer Python 3.11+ e pytest. Na raiz do repositório:

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
- `databricks/catalog/`: notebooks Bronze, Silver e Gold dos extratos Elasticsearch no workspace; `databricks/setup/executar_notebooks.py` executa Silver/Gold via Databricks Connect. Consulte o [medalhão](docs/databricks_medalhao.md).
- `databricks/notebooks/`: perfil de esquema e auditoria agregada do Parquet autorizado; consulte o [guia](docs/execucao_databricks.md).
- `config/`: parâmetros e contratos do cenário experimental.
- `reports/examples/`: [JSON](reports/examples/synthetic_run.json) e [gráfico SVG](reports/examples/synthetic_comparison.svg) gerados localmente.

## Documentação versionada

- [Arquitetura](docs/arquitetura.md), [metodologia](docs/metodologia.md), [algoritmo](docs/algoritmo.md) e [simulação](docs/simulacao.md).
- [Indicadores](docs/indicadores.md), [resultados sintéticos](docs/resultados.md), [limitações](docs/limitacoes.md) e [segurança dos dados](docs/seguranca_dados.md).
- [Guia de execução no Databricks](docs/execucao_databricks.md).

O levantamento de regras operacionais, as decisões internas e o estado detalhado do projeto são mantidos localmente e ficam fora do Git. Eles precisam ser obtidos por canal autorizado antes de interpretar os dados da empresa ou alterar hipóteses operacionais.

Os CSVs reais em `data/` e os resultados individuais em `reports/runs/` estão fora do Git. O usuário autorizou o processamento local dos CSVs; nenhum comando de disponibilidade faz upload. Os notebooks Databricks permanecem específicos para Parquet em Volume e **não executam** estes CSVs. Consulte [segurança](docs/seguranca_dados.md).
