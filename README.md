# Otimização da Alocação de Frota em Aplicativos de Transporte Urbano

TCC (Ciência da Computação) sobre **reposicionamento preventivo de veículos com horizonte D+1**: reposicionar, na véspera e só com dados históricos, motoristas ociosos reduz o **KM morto** (km sem passageiro)?

## Pergunta, escopo e classificação do problema

- **Pergunta:** a alocação preventiva D+1 reduz o KM vazio por corrida em relação a não reposicionar, nos mesmos pedidos, frota, janela e método de distância? Atendimento e cobertura são controles.
- **Classificação:** problema de **reposicionamento preventivo de veículos**; cada motorista livre recebe no máximo um destino (`Moves = {motorista: (lat, lng, km)}`). **Não é** Problema de Roteamento de Veículos (PRV/VRP): não há rotas de várias paradas. Fundamentação em [`reports/validation_current/16_CLASSIFICACAO_PRV_VRP.md`](reports/validation_current/16_CLASSIFICACAO_PRV_VRP.md).
- **Fora do escopo:** despacho em tempo real, aplicativo completo, política da empresa. Regras `PROPOSTA`/`PENDENTE` são hipóteses.

## Resultado registrado

Em março e setembro de 2026, nenhum dos 13 planejadores avaliados reduziu o KM vazio por corrida; a extensão v2 confirma o nulo e um controle positivo sintético mostra que o simulador e a inferência detectam ganho quando ele existe ([`reports/tcc_v2/RELATORIO_V2.md`](reports/tcc_v2/RELATORIO_V2.md), [`docs_antigos/BATERIA_ALGORITMOS.md`](docs_antigos/BATERIA_ALGORITMOS.md)). Vale para este simulador, estes dados e estas hipóteses; KM estimado não é KM faturado.

## Arquitetura

Pacote `src/tcc_frota/` por domínio: `v2/` (rodada final, simulador, políticas, estatística), `algoritmos/` (bateria), `v3/` (extensão v2 do TCC), `availability/`, `analise/`, `demand/`, `gold/`, `simulation/`, `optimization/`, `spatial/`, `ingestion/`, `quality/`, `synthetic/`. Fluxo: dados → Silver/Gold → previsão no corte D → `Planner` → simulador de eventos → estatística → tabelas e figuras. Detalhes e diagramas: [guia completo](docs_antigos/GUIA_COMPLETO_REPOSITORIO.md), [arquitetura](docs_antigos/ARQUITETURA_REORGANIZADA.md).

Tecnologias: Python 3.12, NumPy, SciPy (HiGHS), H3, scikit-learn, statsmodels/arch, Matplotlib, PyArrow; LaTeX para o artigo.

## Instalação rápida

```powershell
python -m pip install -e ".[test,algoritmos,extensao,qualidade]"
```

Sem instalação editável: `PYTHONPATH=src` e `python -m tcc_frota.cli`. Linux/macOS não foram testados.

## Execução rápida (dados sintéticos)

```powershell
tcc-frota build-synthetic-data --out reports/runs/medallion
tcc-frota run-synthetic --out reports/runs
```

O experimento sintético é validação de software, não medição da empresa.

## Testes e qualidade

```powershell
python -m pytest                          # 283 passed, 1 skipped (28/10/2026)
python scripts/verificar_repositorio.py   # Ruff, formatação, compilação, pytest, hashes, estrutura
```

Testes em `tests/unit`, `tests/integration`, `tests/regression` (valores congelados) e `tests/reproducibility` (hashes da v1, estrutura, dados fora do Git).

## Experimentos e versões

| Campanha | Estado | Resultados |
|---|---|---|
| Rodada final (a “v1” dos documentos; pacote `v2`) | congelada (tag `v1-congelada`, 19 hashes) | `reports/tcc_final/` |
| Bateria de 13 algoritmos e guloso seletivo | congeladas | `resultados/`, `tabelas/` |
| Extensão v2 (pacote `v3`), Fases 1–4 | atual | `reports/tcc_v2/` |

Cuidado com os nomes: o pacote `v3` é a “extensão v2” dos documentos. Mapa completo em [`docs_antigos/VERSOES_E_EXPERIMENTOS.md`](docs_antigos/VERSOES_E_EXPERIMENTOS.md); comandos em [`docs_antigos/GUIA_EXPERIMENTOS.md`](docs_antigos/GUIA_EXPERIMENTOS.md). **Nunca regere resultados no lugar de `reports/tcc_final`, `reports/tcc_v2`, `resultados` ou `tabelas`.**

## Reprodutibilidade

Verificado: testes, hashes dos artefatos versionados, importação dos 103 módulos, métricas sintéticas determinísticas e a decisão F4 antes/depois das mudanças ([`reports/final_release/VALIDACAO_FINAL.md`](reports/final_release/VALIDACAO_FINAL.md)). **Não verificado:** a reexecução completa com dados reais (`data/raw/` não é versionado; `final-run`, bateria e Fases v3 não foram rerodadas). Dados reais e `reports/runs/` ficam fora do Git; o processamento local foi autorizado pelo proponente. Não envie dados reais a serviços externos.

## Limitações científicas

Simulador e distâncias estimadas (Haversine × fator rua/reta); previsão com erro; pré-registro com carimbo do Git local; fases 5 e 6 da extensão não feitas; regras da empresa não confirmadas. Lista completa: [`docs_antigos/limitacoes.md`](docs_antigos/limitacoes.md) e [`docs_antigos/ESTADO_FINAL_REPOSITORIO.md`](docs_antigos/ESTADO_FINAL_REPOSITORIO.md).

## Índice da documentação

- Entrada: [guia completo](docs_antigos/GUIA_COMPLETO_REPOSITORIO.md) · [como executar](docs_antigos/COMO_EXECUTAR.md) · [guia do desenvolvedor](docs_antigos/GUIA_DESENVOLVEDOR.md) · [guia de experimentos](docs_antigos/GUIA_EXPERIMENTOS.md) · [versões e experimentos](docs_antigos/VERSOES_E_EXPERIMENTOS.md) · [mapeamento TCC→código](docs_antigos/MAPEAMENTO_TCC_CODIGO.md) · [estado final](docs_antigos/ESTADO_FINAL_REPOSITORIO.md)
- Método: [metodologia](docs_antigos/metodologia.md) · [simulação](docs_antigos/simulacao.md) · [indicadores](docs_antigos/indicadores.md) · [pré-registro da extensão v2](docs_antigos/V2_PREREGISTRO.md) · [orçamento de configurações](docs_antigos/ORCAMENTO_CONFIGURACOES.md)
- Resultados: [reais](docs_antigos/resultados_reais.md) · [bateria](docs_antigos/BATERIA_ALGORITMOS.md) · [seletivo](docs_antigos/RESULTADO_SELETIVO.md) · [banca](docs_antigos/perguntas_banca.md)
- Dados e segurança: [segurança dos dados](docs_antigos/seguranca_dados.md) · [disponibilidade](docs_antigos/disponibilidade.md)
- Auditorias: [`reports/thesis_audit/`](reports/thesis_audit/) · [`reports/validation_current/`](reports/validation_current/) · [`reports/repository_migration/`](reports/repository_migration/) · [`reports/final_release/`](reports/final_release/)

O manuscrito está em `tcc-artigo-latex/`, repositório Git **independente** (com remoto próprio); faça seus commits lá.
