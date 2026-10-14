# Otimização da Alocação de Frota em Aplicativos de Transporte Urbano

TCC sobre redução de KM morto por alocação preventiva D+1. O experimento sintético local permanece como validação de software e referência histórica. A entrada escolhida para a próxima etapa é o Parquet autorizado `data/app_solicitacao_hist.parquet`; os notebooks Databricks atuais fazem apenas perfil e auditoria agregada desse arquivo. Não houve execução no workspace nem validação com frota real.

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
- `databricks/notebooks/`: perfil de esquema e auditoria agregada do Parquet autorizado; consulte o [guia](docs/execucao_databricks.md).
- `config/`: parâmetros e contratos do cenário experimental.
- `reports/examples/`: [JSON](reports/examples/synthetic_run.json) e [gráfico SVG](reports/examples/synthetic_comparison.svg) gerados localmente.

## Documentação versionada

- [Arquitetura](docs/arquitetura.md), [metodologia](docs/metodologia.md), [algoritmo](docs/algoritmo.md) e [simulação](docs/simulacao.md).
- [Indicadores](docs/indicadores.md), [resultados sintéticos](docs/resultados.md), [limitações](docs/limitacoes.md) e [segurança dos dados](docs/seguranca_dados.md).
- [Guia de execução no Databricks](docs/execucao_databricks.md).

O levantamento de regras operacionais, as decisões internas e o estado detalhado do projeto são mantidos localmente e ficam fora do Git. Eles precisam ser obtidos por canal autorizado antes de interpretar os dados da empresa ou alterar hipóteses operacionais.

O Parquet real em `data/` e outros extratos locais estão fora do Git. O usuário informou autorização para usar o Parquet no Databricks Free Edition; confira o escopo dessa autorização e transfira o arquivo ao Volume pelo procedimento institucional. A auditoria local pela CLI exige `TCC_REAL_DATA_AUTHORIZED=YES`. Os notebooks Parquet exigem confirmação explícita pelo widget `real_data_authorized`; nenhum faz upload. Consulte [segurança](docs/seguranca_dados.md).
