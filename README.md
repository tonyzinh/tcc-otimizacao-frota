# Otimização da Alocação de Frota em Aplicativos de Transporte Urbano

TCC sobre redução de KM morto por alocação preventiva D+1. Há um **MVP sintético local** com ingestão, previsão, algoritmo guloso, simulação retrospectiva, testes e relatórios. Notebooks PySpark/Delta foram preparados, mas ainda não foram executados no Databricks.

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
- `databricks/`: sete notebooks e SQL para Unity Catalog/Delta; consulte o [guia](docs/execucao_databricks.md).
- `config/`: parâmetros e contratos do cenário experimental.
- `reports/examples/`: [JSON](reports/examples/synthetic_run.json) e [gráfico SVG](reports/examples/synthetic_comparison.svg) gerados localmente.

## Documentação versionada

- [Arquitetura](docs/arquitetura.md), [metodologia](docs/metodologia.md), [algoritmo](docs/algoritmo.md) e [simulação](docs/simulacao.md).
- [Indicadores](docs/indicadores.md), [resultados sintéticos](docs/resultados.md), [limitações](docs/limitacoes.md) e [segurança dos dados](docs/seguranca_dados.md).
- [Guia de execução no Databricks](docs/execucao_databricks.md).

O levantamento de regras operacionais, as decisões internas e o estado detalhado do projeto são mantidos localmente e ficam fora do Git. Eles precisam ser obtidos por canal autorizado antes de interpretar os dados da empresa ou alterar hipóteses operacionais.

Os CSVs reais em `data/` são extratos locais não versionados e ainda não auditados. Não os publique nem os envie a serviços externos sem autorização. A auditoria local de dados reais exige autorização formal e `TCC_REAL_DATA_AUTHORIZED=YES`; os notebooks aceitam apenas sintéticos. Consulte [segurança](docs/seguranca_dados.md) antes de usar dados reais.
