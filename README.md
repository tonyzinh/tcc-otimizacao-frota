# Despacho em lotes com atribuição conjunta pelo algoritmo Húngaro

**Avaliação por simulação do km vazio em aplicativos de transporte**

Trabalho de Conclusão de Curso. Bacharelado em Ciência da Computação, FAESA, Vitória (ES), 2026.

| | |
|---|---|
| **Alunos** | Entony Jovino dos Santos · Raphael Simões Gomes |
| **Orientador** | Prof. Rober Marcone Rosi |
| **Artigo** | [`article/TCC 2026-2 - Entony Jovino - Raphael Simões - Orientador Rober Marcone Rosi.pdf`](<article/TCC 2026-2 - Entony Jovino - Raphael Simões - Orientador Rober Marcone Rosi.pdf>) (fonte LaTeX em [`article/`](article/)) |

---

## Sumário

1. [O problema](#o-problema)
2. [A proposta](#a-proposta)
3. [Como a proposta é avaliada](#como-a-proposta-é-avaliada)
4. [Resultados](#resultados)
5. [Limitações](#limitações)
6. [Estrutura do repositório](#estrutura-do-repositório)
7. [Como executar](#como-executar)
8. [Dados privados](#dados-privados)
9. [Documentação](#documentação)

---

## O problema

Num aplicativo de transporte, cada pedido de corrida precisa de um veículo livre. O trecho que o veículo percorre até buscar o passageiro (a **aproximação**) não leva ninguém. Neste trabalho, essa distância é o **km vazio**. Ela gasta tempo do motorista e combustível e atrasa o embarque, sem gerar receita.

A regra mais comum é mandar, assim que o pedido chega, o **veículo livre mais próximo**. Ela é simples, mas olha um pedido de cada vez. Quando vários pedidos chegam juntos e há poucos veículos livres, dar o mais próximo ao primeiro pedido pode tirar o veículo de que outro pedido precisaria mais. O resultado pode ser um km vazio total maior, ou menos pedidos atendidos.

**Pergunta de pesquisa:** como a atribuição conjunta de pedidos em lotes de 60 segundos, pelo algoritmo Húngaro, afeta o km vazio e o atendimento, em comparação com o despacho pelo veículo mais próximo?

## A proposta

Em vez de decidir pedido a pedido, o sistema **acumula os pedidos durante 60 segundos** e, ao fim desse lote, **distribui todos de uma vez** entre os veículos livres próximos. A distribuição segue um objetivo em duas etapas:

1. atender **o maior número possível** de pedidos do lote;
2. entre as distribuições com esse número, escolher a de **menor soma de distâncias** de aproximação.

Esse é um **problema de atribuição** (emparelhar pedidos e veículos com custo mínimo). O **algoritmo Húngaro** (Kuhn–Munkres) resolve esse problema de forma exata e em tempo polinomial. A implementação é própria e foi conferida contra a enumeração de todas as combinações.

Exemplo do notebook [`02_hungarian_example`](notebook/02_hungarian_example.ipynb), com três pedidos e três veículos:

| Regra | Pares escolhidos | km vazio total |
|---|---|---|
| Mais próximo, um pedido por vez | P1→V1, P2→V3, P3→V2 | 13,0 km |
| Atribuição conjunta (Húngaro) | P1→V2, P2→V1, P3→V3 | 9,0 km (−30,8%) |

A proposta atua **só sobre pedidos já recebidos**. Ela não prevê demanda nem move veículos ociosos antes dos pedidos. O ganho possível vem de **trocar qual veículo atende qual pedido**, e o custo é que o pedido pode esperar até 60 segundos pelo fim do lote.

## Como a proposta é avaliada

Três políticas são comparadas **com os mesmos pedidos, frota, jornadas e distâncias**:

| Política | Regra | Papel |
|---|---|---|
| **A** | Mais próximo livre, despacho imediato | Referência principal (referência simplificada calibrada; **não** é a operação real) |
| **B** | Mais próximo livre, lotes de 60 s, pedidos em ordem de chegada | Controle: separa o efeito de **esperar** o lote do efeito de **decidir em conjunto** |
| **C** | Atribuição conjunta pelo Húngaro, lotes de 60 s | Método proposto |

Depois dos resultados, também foi comparado um **guloso global** (D), que escolhe primeiro o par pedido–veículo mais curto do lote.

A avaliação tem duas frentes, relatadas em separado e **nunca somadas**:

- **Dados reais (simulação contrafactual).**
  - **Dados:** pedidos, jornadas, compromissos e posições históricas de uma empresa de transporte por aplicativo que opera na Grande Vitória (ES).
  - **Execução:** um simulador de eventos discretos roda cada política sobre o mesmo dia.
  - **Calibração:** os parâmetros (fator rua/reta, velocidade, raio e paciência) foram calibrados em março.
  - **Congelamento:** a configuração foi congelada **antes** de simular setembro (replicação) e outubro (avaliação final).
- **Cenários sintéticos.**
  - **Cenários:** demanda e frota geradas sobre a rede viária da região (IBGE e OpenStreetMap).
  - **Escala:** 22 cenários, com 40 sementes cada.
  - **Papel:** evidência exploratória e complementar.

**Hipótese (H1):** C tem menos km vazio que A (comparação principal) e que B (complementar). A redução só conta como "com atendimento preservado" se C cumprir o **critério de atendimento**:

- não violar compromissos;
- atender pelo menos tantos pedidos quanto a referência;
- não piorar o percentil 90 da espera.

O dia é a unidade de análise. Os intervalos de confiança vêm de bootstrap por dia e por blocos.

## Resultados

Os números abaixo vêm de arquivos em `reports/` e estão no artigo. A redução de km vazio é **simulada**, não medida na operação.

| Comparação | Setembro/2026 | Outubro/2026 |
|---|---|---|
| C × A, km vazio | **−5,96%** | **−5,04%** |
| C × A, atendidos | +16 | **−85** (critério de atendimento **não** cumprido) |
| C × B, km vazio | −2,74% | −1,40% |

O que mais os resultados mostram:

- **Fração do km total:** a redução contra A equivale a cerca de **1,3 e 0,9 ponto percentual do km total modelado**, porque o km vazio é cerca de um quinto do km com e sem passageiro.
- **Vantagem sobre o lote simples (B):** é **pequena e frágil**, de −0,3% a −4,6% nas análises de sensibilidade.
- **Teste posterior fora da amostra** (12 dias, 26/10 a 08/11, parâmetros recalibrados com janeiro a agosto):
  - contra A, a redução caiu para **−2,79%**, com intervalo que inclui zero;
  - contra B, o km ficou **0,87% maior**, com 29 atendimentos a mais e o mesmo km por atendido.
- **Guloso global (D):** teve menos km que o Húngaro em todos os períodos; o Húngaro atendeu mais com os parâmetros de março, por pouco com a calibração nova e menos no teste. **Nenhum dos dois mostrou vantagem clara.**
- **Cenários sintéticos:** redução mediana de 2,0% a 8,9%.

Em resumo: decidir o lote em conjunto reduziu o km vazio simulado em relação ao despacho imediato, mas parte desse ganho vem de esperar o lote. A vantagem específica da atribuição ótima sobre regras mais simples não ficou demonstrada. O trabalho relata o resultado desfavorável junto com o favorável.

Os resultados congelados ficam em `reports/historical/frozen_evaluation/` (dados reais) e `reports/synthetic/dispatch_evaluation/` (sintético). As análises posteriores (sensibilidade, recalibração, teste fora da amostra e guloso global) ficam em `reports/diagnostics/`.

## Limitações

- O resultado vem de **simulação**: o km é estimado (linha reta × fator rua/reta), não medido por odômetro.
- O simulador atende mais pedidos que a operação real: não modela recusa do motorista nem cancelamento depois da atribuição.
- A referência A é simplificada e **não** reproduz o despacho real da empresa.
- A disponibilidade dos motoristas foi reconstruída a partir dos registros históricos.
- Os resultados valem para uma empresa, uma região e o período estudado.
- O ótimo é **de cada lote**, não do dia inteiro.
- O método não foi implantado, e nenhum efeito operacional foi medido.

## Estrutura do repositório

```
article/        artigo (LaTeX), PDF e relatórios editoriais
configs/        contrato de dados, políticas, cenários sintéticos e experimentos
data/           dados locais, não versionados: raw/ (extrações), processed/ (cache), geographic/ (IBGE/OSM)
docs/           documentação técnica em português
notebook/       01 visão geral · 02 exemplo do Húngaro · 03 mapa H3 · 04 resultados reais · 05 resultados sintéticos
reports/        resultados: historical/ · synthetic/ · diagnostics/ · data_quality/ · figures/ · manifests/
scripts/        extração, geografia, análises posteriores, figuras e verificações
src/tcc_frota/  pacote Python (ver tabela abaixo)
tests/          testes unitários, de integração, de regressão e de reprodutibilidade
```

| Pacote (`src/tcc_frota/`) | Responsabilidade |
|---|---|
| `domain` | Entidades (pedido, motorista, parâmetros, resultado) e unidades |
| `assignment` | Políticas: mais próximo (A, B), Húngaro (C), guloso global (D) |
| `simulation` | Simulador de eventos discretos e experimento por dia real |
| `data` | Montagem do mundo histórico, disponibilidade, extração somente leitura e pseudonimização |
| `scenarios` | Geografia pública, gerador sintético e catálogo de cenários |
| `metrics` | Totais, contrastes pareados, bootstrap e correção de Holm |
| `visualization` | Figuras e mapa |
| `cli` | Comando `tcc-frota` |

## Como executar

**Requisitos:** Python 3.12. Para compilar o artigo, é preciso também XeLaTeX, BibTeX e a fonte Arial (MiKTeX ou TeX Live).

```bash
uv sync --frozen --extra test --extra quality --extra notebooks   # ou: pip install -e ".[test,quality,notebooks]"
```

**Testes e qualidade:**

```bash
python -m pytest
python -m ruff check src tests scripts && python -m ruff format --check src tests scripts
```

**Exemplo sintético** (sem dados privados; baixa antes a geografia pública):

```bash
python scripts/download_geography.py
tcc-frota run-synthetic --scenarios S1 --seeds 101-103 --out reports/examples/synthetic_quick
tcc-frota analyze-synthetic --input reports/examples/synthetic_quick --out reports/examples/synthetic_quick/analise
```

**Conferências de reprodutibilidade:**

```bash
python scripts/verify_frozen_results.py               # SHA-256 dos resultados congelados
python scripts/check_equivalence.py --synthetic --analysis --out data/processed/equivalence.json
python scripts/compute_article_derived_values.py --check   # números derivados citados no artigo
python scripts/sync_article_figures.py --check        # figuras do artigo iguais à origem em reports/figures
python scripts/run_notebooks.py                       # executa os cinco notebooks em kernel limpo
```

**Artigo:** em `article/`, rode XeLaTeX, depois BibTeX, depois XeLaTeX duas vezes (ver [`article/README.md`](article/README.md)).

## Dados privados

- **Uso:** os dados reais da empresa são processados **só localmente**, e só agregados são publicados.
- **Fora do repositório:** nenhum dado bruto, identificador de motorista ou coordenada individual. A pasta `data/` é ignorada pelo Git.
- **Gancho de pre-commit:** bloqueia arquivos de dados, segredos e arquivos grandes.
- **Pseudonimização:** os identificadores são pseudonimizados com HMAC-SHA256, e o segredo fica fora do repositório.
- **Autorização:** rodar sobre dados reais exige `TCC_REAL_DATA_AUTHORIZED=YES`, liberado só pelo proprietário dos dados.
- **Sem os dados:** a parte sintética e as análises dos resultados agregados continuam reproduzíveis.

## Documentação

| Documento | Conteúdo |
|---|---|
| [`docs/methodology.md`](docs/methodology.md) | Método, políticas, períodos e critérios |
| [`docs/architecture.md`](docs/architecture.md) | Pastas, pacotes e fluxo de dados |
| [`docs/data_dictionary.md`](docs/data_dictionary.md), [`docs/data_quality.md`](docs/data_quality.md), [`docs/availability.md`](docs/availability.md) | Dados, qualidade e disponibilidade dos motoristas |
| [`docs/validation.md`](docs/validation.md) | Validade das bases e do simulador |
| [`docs/reproducibility.md`](docs/reproducibility.md) | Comandos e obtenção dos dados |
| [`docs/decisions.md`](docs/decisions.md) | Registro datado das decisões (R-01 a R-36) |
| [`docs/repository_migration.md`](docs/repository_migration.md) | Reorganizações do repositório e auditoria do histórico Git |

**Estudo anterior:** antes deste trabalho, os autores estudaram o reposicionamento preventivo de veículos na véspera (D+1), com uma bateria de 13 algoritmos, e o resultado foi **nulo**: nenhum reduziu o km vazio. Esse material saiu da árvore ativa e está preservado fora dela, com checksums, e os hashes continuam conferidos por `scripts/verify_frozen_results.py`.
