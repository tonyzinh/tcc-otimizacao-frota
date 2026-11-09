# Análises pós-hoc do parecer: resultados (09/11/2026)

Plano escrito antes da execução: [`PLANO.md`](PLANO.md). Script: `scripts/pos_hoc_parecer.py` (subcomandos `base`, `sens`, `disp`,
`contagens`, `janelas`, `componentes`, `simulado_a`, `viario`, `sintetico`). Dados reais lidos localmente com autorização do proprietário
para esta rodada; saídas só agregadas (por dia ou por período). **Nada aqui altera o experimento congelado**; todos os números abaixo são
pós-hoc (definidos depois de vistos os resultados de setembro e outubro).

## 0. Conferência com o congelado

Reexecução de A, B e C sobre os mundos congelados (cache `d5cb1289caea`) com o código atual: 120 de 120 pares (dia, política) de
setembro e outubro idênticos aos Parquet congelados (diferença máxima de km 0,0; atendidos iguais em todos) —
`base_conferencia_congelado.json`. A reconstrução do mundo pelo código atual (cenário J, ponte 1.200 s) reproduziu os totais congelados
dos dois períodos (C×A −5,96%/+16 e −5,04%/−85) — `disp_resumo.csv`, linha `J_ponte1200`.

## 1. Validação de componentes (P1) — `componentes_observados.json`, `componentes_simulado_A.csv`

| Grandeza | Treino | Validação | Setembro | Outubro | Modelo |
|---|---|---|---|---|---|
| Pedidos aceitos observados (encerrada + cancel. pós-aceite) | 56,5% | 59,6% | 45,0% | 41,0% | — |
| Corrida encerrada observada | 47,6% | 49,8% | 37,7% | 34,8% | — |
| Atendidos simulados em A | 67,6% | 73,4% | 65,8% | 61,9% | — |
| Aproximação observada, mediana (km) | 3,08 | 3,12 | 3,84 | 4,10 | — |
| Aproximação observada, média aparada 5% (km) | 3,81 | 3,93 | 4,88 | 5,27 | — |
| Aproximação simulada em A, média por atendido (km) | 2,50 | 2,44 | 2,66 | 2,69 | — |
| Fator rua/reta no registro de ofertas, mediana | 1,363 | 1,372 | 1,363 | 1,369 | 1,3012 |
| Velocidade de aproximação no registro de ofertas, mediana (km/h) | 18,3 | 17,4 | 19,7 | 20,4 | 16,079 |
| Registro → início da corrida observado, mediana (s) | 790 | 839 | 1.029 | 1.052 | — |
| Espera simulada em A, mediana (s) | 521 | 504 | 578 | 588 | — |
| Duração observada da viagem, mediana (s) | 1.017 | 1.031 | 1.233 | 1.216 | entrada observada |

Leitura: as populações diferem (política e conjunto de atendidos diferentes; "aceito" inclui cancelamentos e exclui pagamento
rejeitado e cancelamento antes do aceite), então nenhuma diferença isolada prova erro do simulador. Mas o simulador é sistematicamente
mais generoso que a operação observada (atende 11 a 21 p.p. a mais; aproximação menor; espera menor), e a diferença cresceu em setembro
e outubro, para os quais os parâmetros de março não foram recalibrados. O fator e a velocidade observados no registro de ofertas
(semântica de `distancia_restante` inferida: distância restante até a origem enquanto o passageiro não embarcou) ficam próximos dos
usados (fator 5% maior; velocidade 8–27% maior em mediana, com grande dispersão). **Validação operacional não alcançada.**

## 2. Disponibilidade (P2) — `disp_contagens_todos_periodos.csv`, `disp_resumo.csv`

Médias por dia: pedidos de tempo real 1.207 (treino), 1.261 (validação), 1.128 (setembro), 941 (outubro); motoristas no registro de
ofertas 106,8 / 111,3 / 86,7 / 74,3; motoristas distintos com corrida encerrada 108,4 / 110,1 / 86,7 / 70,4. A queda aparece nas duas
fontes independentes (ofertas e corridas encerradas) e na demanda: indica mudança de operação, não só de cobertura do registro. Jornadas
registradas descartadas por vínculo ambíguo (placa com vários motoristas) 36–47 por dia; isso altera a janela, não a contagem de
motoristas simulados (que é a do registro de ofertas).

| Variante (set / out) | C×A km | C×A ΔN | C×B km | C×B ΔN |
|---|---|---|---|---|
| J, ponte 1.200 s (congelado) | −5,96% / −5,04% | +16 / −85 | −2,74% / −1,40% | +191 / +149 |
| J, ponte 600 s | −5,80% / −5,29% | +40 / −140 | −2,59% / −1,77% | +209 / +96 |
| J, ponte 2.400 s | −5,96% / −4,91% | +16 / −74 | −2,74% / −1,40% | +191 / +127 |
| E (só registro de ofertas) | −6,77% / −4,01% | +28 / +5 | −1,72% / −1,37% | +243 / +186 |
| J, 20% menos motoristas (por hash) | −6,93% / −5,85% | +76 / −28 | −4,29% / −2,42% | +35 / +141 |

Nenhum veículo foi inventado; não houve expansão artificial da oferta.

## 3. Parâmetros e distância (P3) — `sens_resumo.csv`, `viario_resumo.csv`

| Variante (set / out) | C×A km | C×A ΔN | C×B km | C×B ΔN |
|---|---|---|---|---|
| fator 1,2 | −6,65% / −4,70% | −129 / −105 | −2,67% / −1,86% | +187 / +154 |
| fator 1,6 | −4,75% / −4,87% | +82 / −80 | −1,92% / −2,09% | +228 / +90 |
| velocidade −25% | −6,24% / −4,07% | −32 / −75 | −2,36% / −0,81% | +131 / +192 |
| velocidade +25% | −5,62% / −5,06% | −144 / −213 | −2,43% / −1,91% | +105 / +144 |
| raio 3,5 km | −4,56% / −4,55% | +6 / −158 | −1,08% / −2,65% | +196 / −18 |
| raio 5,5 km | −6,24% / −4,60% | +45 / −93 | −2,32% / −0,96% | +129 / +186 |
| paciência 120 s | −3,33% / −4,24% | +34 / −215 | −0,31% / −1,06% | +160 / −4 |
| paciência 300 s | −7,36% / −5,33% | −34 / +35 | −4,57% / −2,54% | +109 / +231 |

Distância viária (rede OSM dos quatro municípios, Dijkstra dirigido, raio por via 5,86 km = 4,5 × 1,3012; dias 01, 08, 15 e 22/10
fixados por calendário; 3–4% dos pontos a mais de 500 m da rede, ligados em linha reta): C×A −6,24% (reta×fator nos mesmos dias:
−6,29%), ΔN −61 (reta×fator: +4); C×B −2,81% (−1,75%), ΔN +20 (+27). Atendimento simulado de A cai de 69,7% para 64,7%.

Leitura: a redução de km de C contra A e B aparece em todas as variantes; o sinal da diferença de atendidos C×A não é estável
(varia de −215 a +82). O E2 de C×A é sensível às hipóteses.

## 4. Sintético (P4) — `sintetico_familias.csv`

Nove das 22 variantes (salto 6/10 km, previsão perfeita, erro de previsão) só mudam parâmetros do planejador D+1, que não participa do
despacho; as entradas de despacho seguem a mesma distribuição do cenário-base, com outro sorteio (o código do cenário entra na semente).
As variantes de zoneamento (resolução 6 e 8) mudam a granularidade espacial do gerador de demanda; as de frota mudam a razão
pedidos/veículo.

| Família principal | C×A, mediana entre sementes (P10; P90) | Sementes com redução | ΔN médio C−A | Sementes em que C atende menos |
|---|---|---|---|---|
| S1 | −2,0% (−4,6; +0,9) | 32/40 | −1,1 | 24/40 |
| S2 | −8,9% (−13,0; −6,2) | 40/40 | +5,2 | 13/40 |
| S3 | −8,2% (−10,5; −4,1) | 40/40 | +8,4 | 7/40 |
| S4 | −7,8% (−10,2; −5,4) | 40/40 | +8,8 | 5/40 |
| S5 | −8,3% (−12,3; −4,3) | 39/40 | +6,9 | 13/40 |

Quantidade média atendida por C menor que a de A: S1 e S2 com frota abundante (tolerância sintética cumprida, quantidade não).

## 5. Variante D e janelas (P5) — `base_resumo.csv`, `janelas_treino_resumo.csv`

D (guloso global pelo menor par) contra C, janela 60 s: setembro −2,66% km e −179 atendidos; outubro −1,88% e −83; treino −2,86% e
−206. D contra A: setembro −8,46% e −163; outubro −6,83% e −168. **D tem menos km que C e atende menos**: a vantagem de C sobre o
guloso global é de cardinalidade (atendidos), não de km.

Grade de janelas só no treino (01/02–15/03):

| Janela | C×A km | C×A ΔN | C×B km | C×B ΔN | D×C km | D×C ΔN |
|---|---|---|---|---|---|---|
| 30 s | −4,02% | +267 | −2,90% | +438 | −0,99% | −126 |
| 60 s | −5,02% | +98 | −2,33% | +319 | −2,86% | −206 |
| 120 s | −8,72% | −416 | −2,18% | +474 | −3,76% | −338 |

Nenhuma janela foi escolhida ou reavaliada em setembro/outubro a partir desta grade.

## 6. Estatística (P6) — `estatistica_diaria_pareada.csv`, `estatistica_sensibilidade_ic.csv`

Bootstrap congelado: blocos móveis circulares de 7 dias, 10.000 reamostragens; com 15 dias (setembro) há ~3 blocos por reamostragem, e o
intervalo fica mais estreito que o intervalo t pareado (C×A km/dia: bloco 7 (−133,0; −102,9); bloco 3 (−158,7; −77,3); t (−160,5;
−75,1)). Em todas as variantes o limite superior para km fica abaixo de zero; para atendidos C×A, todos os intervalos incluem zero nos
dois períodos. Nenhuma margem de não inferioridade foi definida (não há justificativa externa ou operacional documentada).

## 7. Significado prático e justiça (P7) — `base_pratica_e_justica.csv`

| | Set A | Set C | Out A | Out C |
|---|---|---|---|---|
| Km vazio por dia | 1.975,2 | 1.857,4 | 1.568,2 | 1.489,1 |
| Km vazio / (vazio + com passageiro) | 22,6% | 21,3% | 21,6% | 20,8% |
| Viagem média modelada (km) | 9,11 | 9,22 | 9,76 | 9,81 |
| Espera P95 / P99 / máx. (s), só atendidos | 1.267 / 1.365 / 1.480 | 1.266 / 1.340 / 1.474 | 1.265 / 1.365 / 1.482 | 1.268 / 1.344 / 1.459 |
| Pedidos expirados | 5.793 | 5.777 | 8.972 | 9.057 |
| Expirados que tiveram veículo elegível em algum lote | — | 1.370 (B: 1.437; D: 1.463) | — | 1.552 (B: 1.592; D: 1.693) |

Economia simulada C×A: 117,8 km/dia (setembro) e 79,1 km/dia (outubro). Um pedido pode ser preterido em no máximo 3 lotes, limite dado
pela paciência de 180 s; C preteriu menos pedidos que B e D. Percentis de espera são só dos atendidos e não representam os pedidos que
expiraram.
