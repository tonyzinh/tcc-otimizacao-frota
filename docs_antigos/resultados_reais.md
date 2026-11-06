# Resultados e Discussão (rascunho)

**Execução de referência:** `final-run` `20261016T013428Z`, código `69b8647` sem alterações pendentes, semente 20261016, 2.000 reamostragens. Tabelas em [`reports/tcc_final/`](../reports/tcc_final/) e figuras em [`reports/tcc_final/figuras/`](../reports/tcc_final/figuras/). Uma segunda execução reproduziu as tabelas principal e de sensibilidade de forma idêntica. **Todos os números são estimativas de simulação retrospectiva**: distâncias geodésicas multiplicadas por um fator rua/reta calibrado e baseline simulado. Não são quilometragem rodada nem economia observada (DT003, RN012, RN021).

## 4.1 Dados, desfechos e qualidade

Foram ingeridas 205.983 solicitações da região 1 (Grande Vitória): 110.139 de 04/01 a 31/03/2026 e 95.844 de 07/07 a 30/09/2026. As contagens são iguais às dos manifestos de extração e não há código duplicado. Também entraram 8.793 fotos da frota a cada 10 min e 43.909 sumários a cada 2 min. Todas as fotos coincidem com o sumário de mesmo código, o que sustenta a leitura do enum de estados (DT010). A Tabela 1 mostra o tratamento de cada status (RN004). O universo do estudo é formado pelas solicitações **imediatas** (sem agendamento), de **demanda** e com origem **na caixa** da Grande Vitória: 117.309 pedidos. Ficaram de fora 79.161 agendadas (34–43% das solicitações, conforme o mês), 8.256 não demanda (pagamento rejeitado, retraçamento, cancelamento do operador, estados transitórios) e 1.257 origens fora da caixa (Tabela 2). Diferentemente da base usada em setembro (DT011), **as não atendidas agora têm origem própria**: 100% das `NaoAtendida` têm coordenada, e a cobertura deixa de ser condicional às corridas realizadas.

> **Tabela 1** – Desfechos e tratamento de status: `tab01_desfechos_tratamento.csv`. **Tabela 2** – Qualidade e perdas por filtro: `tab02_qualidade.csv`.

## 4.2 Onde o atendimento se perde

A perda concentra-se em duas faixas, com mecanismos distintos (Tabela 3, Figuras 1 e 2). Na **rampa matinal (04–07h)**, 70% (março) e 78% (setembro) das imediatas não foram aceitas. Para as não aceitas, o motorista livre mais próximo na foto anterior estava a uma mediana de 5,3 km (março) e 3,6 km (setembro), contra 2,6 e 1,8 km nas aceitas. Só 17% e 34% das não aceitas tinham motorista livre a até 2 km. No **pico das 17–19h**, a perda também é alta (66% e 77%), mas 55% e 53% das não aceitas tinham motorista livre a até 2 km. Ali o problema não parece ser o posicionamento. São associações descritivas, não relações causais.

A oferta explica a rampa. Entre 0h e 5h há de 15 a 30 motoristas trabalhando, e às 6h entram em média 27 sessões em março (16 em setembro); o pico de pedidos vem às 7h. Os motoristas ficam parados à noite: a mediana da distância entre a última posição de um dia e a primeira do dia seguinte é de 0,49 km (p90 de 5,0 km; n = 2.434) em março e 0,46 km (p90 de 4,0 km; n = 1.781) em setembro. Isso sustenta a ideia de reposicionar no fim do dia.

> **Tabela 3** – Não atendimento por faixa: `tab04_faixas_nao_atendimento.csv`. **Figura 1** – `fig01_demanda_aceite_por_hora`. **Figura 2** – `fig02_nao_atendidas_por_zona`. Frota: `tab05_frota_descritivo.csv`.

## 4.3 Previsão D+1 da demanda total

A previsão usa a zona H3 r7 e a hora, com corte às 20h de D e 56 dias de treino sem o Carnaval. Na calibração de março (janela 04–11h), o WAPE médio por zona-hora foi de 0,967 para a média do mesmo dia da semana, 1,010 para a regressão de Poisson e 1,082 para a naïve sazonal. Pela regra pré-especificada (o modelo mais simples dentro de 5% do melhor), foi escolhida a média do dia da semana. No teste, ela também teve o menor erro do total da janela em março (WAPE de 12,9% contra 14,4% da naïve e 16,4% da Poisson). Em setembro, a Poisson ficou ligeiramente à frente no total (20,7% contra 21,3%). A Poisson tem o menor desvio de Poisson em todos os cortes, mas superestima o total em março (233 previstos contra 207 observados por dia). WAPE próximo de 1 por zona-hora reflete contagens esparsas (cerca de 210 pedidos por dia, espalhados em dezenas de zonas e 7 horas). A janela de 28 ou 84 dias e a inclusão do Carnaval mudam pouco o erro (Tabela 4). Um teste automatizado garante que nada de D nem de D+1 entra no treino.

> **Tabela 4** – Erros de previsão: `tab07_erros_previsao.csv`. **Figura 3** – `fig03_previsto_observado`.

## 4.4 Calibração do baseline simulado

O simulador despacha o motorista livre mais próximo dentro de um raio, com fila e paciência; corridas reais fora do universo (agendadas, horas vizinhas) bloqueiam o motorista como compromissos. Os parâmetros medidos diretamente nos dias de calibração foram: fator rua/reta da busca de 1,30 (março, n = 466) e 1,38 (setembro, n = 369); velocidade até o passageiro de 16,1 e 16,6 km/h; e, nas viagens, fator de 1,48–1,50 e velocidade de 22–23 km/h. Na base inteira, a mediana do fator de busca é 1,37 (n = 1.124), próxima do 1,42 exploratório. O raio e a paciência foram ajustados para reproduzir o aceite e o tempo de busca observados: 4,5 km e 180 s em março, 4,0 km e 120 s em setembro. A paciência curta é coerente com o sistema, que declara `NaoAtendida` com mediana de 113 s após o registro.

O ajuste é bom, mas não perfeito (Tabela 5). Na janela 04–11h, o atendimento simulado foi de 58,2% contra 54,2% de aceite observado na calibração de março, e de 60,6% contra 56,0% no teste. Em setembro, 58,5% contra 55,9% e 47,2% contra 45,8%. O tempo mediano até o passageiro (564–576 s) ficou próximo da busca observada (595–604 s). Na faixa 07–10h de março, o simulador atende cerca de 7 p.p. a mais que a operação, o que deixa menos demanda perdida a recuperar nessa faixa.

> **Tabela 5** – Calibração e ajuste: `tab08_calibracao_simulador.csv`, `tab09_ajuste_baseline.csv`, `tab06_calibracao_gold.csv`.

## 4.5 Resultado principal

Os parâmetros dos algoritmos foram escolhidos só nos dias 2–15 de março (regime B, 04–11h), pelo critério de corridas extras por km vazio extra. O resultado foi ρ = 2,5 km e limite de 3 km para o guloso, θ = 0,1 e limite de 3 km para a regra de limiar, e limite de 3 km para o proporcional (`tab10_selecao_parametros_calibracao.csv`). A grade de α é reportada inteira. A Tabela 6 compara cada algoritmo ao cenário sem reposicionamento nos dias de teste (16–31/03 e 16–30/09), com os mesmos pedidos, frota, compromissos e método de distância. A assinatura SHA-256 das entradas é conferida em cada par.

**Tabela 6** – Indicadores primários, janela 04–11h, regime B (escala conhecida, plano no fim de D). Variações em relação ao cenário sem reposicionamento; IC 95% por bootstrap de dias; p do teste de permutação pareado para as corridas atendidas.

| Período | Algoritmo | Corridas atendidas (%) | Corridas extras/dia | KM de busca por corrida (%) | KM de reposicionamento/dia | KM vazio por corrida (%) | KM vazio por corrida extra | Tempo até o passageiro (s) | Execução | p (corridas) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| mar/2026 | Proporcional | +1,09 [+0,30; +2,10] | +1,38 [+0,38; +2,56] | −1,81 [−3,07; −0,62] | 33,5 [27,7; 38,7] | +8,15 [+6,44; +10,11] | 22,6 [12,2; 71,7] | −10,7 [−18,0; −3,5] | 65% | 0,038 |
| mar/2026 | Guloso marginal α=0,05 (agressiva) | +0,40 [−0,46; +1,34] | +0,50 [−0,56; +1,69] | −3,15 [−4,28; −2,13] | 66,5 [56,6; 75,6] | +16,77 [+14,92; +18,99] | 114,7 [34,6; 888,2] | −19,4 [−27,2; −12,4] | 78% | 0,477 |
| mar/2026 | Guloso marginal α=0,2 (intermediária) | +0,40 [−0,37; +1,20] | +0,50 [−0,44; +1,50] | −1,68 [−2,56; −0,82] | 38,6 [30,4; 46,9] | +9,88 [+8,36; +11,48] | 68,7 [24,1; 523,7] | −10,4 [−15,9; −5,2] | 76% | 0,414 |
| mar/2026 | Guloso marginal α=0,5 (conservadora) | +0,20 [+0,00; +0,46] | +0,25 [+0,00; +0,56] | −0,84 [−1,75; −0,13] | 14,7 [11,2; 18,3] | +3,59 [+2,72; +4,35] | 50,5 [24,5; 200,1] | −4,6 [−9,8; −0,4] | 79% | 0,250 |
| mar/2026 | Regra de limiar | +1,09 [+0,36; +1,87] | +1,38 [+0,50; +2,19] | −1,84 [−3,55; −0,28] | 102,2 [86,5; 115,6] | +28,55 [+24,75; +33,44] | 72,5 [44,1; 206,1] | −10,7 [−21,2; −1,1] | 77% | 0,016 |
| set/2026 | Proporcional | +1,97 [+0,39; +4,31] | +1,53 [+0,33; +3,00] | −2,13 [−3,66; −0,58] | 24,6 [20,7; 28,4] | +9,81 [+7,76; +11,77] | 15,8 [8,2; 63,1] | −12,1 [−20,9; −3,3] | 66% | 0,047 |
| set/2026 | Guloso marginal α=0,05 (agressiva) | +2,32 [+0,94; +3,93] | +1,80 [+0,80; +2,87] | −1,53 [−3,49; +0,44] | 39,9 [32,9; 47,5] | +17,80 [+15,01; +20,78] | 23,0 [14,4; 53,3] | −9,3 [−20,5; +1,8] | 80% | 0,008 |
| set/2026 | Guloso marginal α=0,2 (intermediária) | +2,06 [+1,21; +3,10] | +1,60 [+0,93; +2,27] | −1,97 [−3,56; −0,50] | 20,2 [16,0; 24,4] | +7,83 [+5,85; +9,65] | 12,7 [8,8; 20,6] | −11,5 [−20,6; −3,1] | 81% | 0,001 |
| set/2026 | Guloso marginal α=0,5 (conservadora) | +0,86 [+0,34; +1,39] | +0,67 [+0,27; +1,13] | −0,11 [−0,77; +0,69] | 5,5 [3,9; 7,1] | +2,57 [+1,66; +3,51] | 10,4 [7,8; 18,2] | −1,0 [−4,7; +3,6] | 86% | 0,031 |
| set/2026 | Regra de limiar | +2,92 [+1,76; +4,10] | +2,27 [+1,33; +3,13] | −6,08 [−8,68; −3,61] | 86,9 [78,1; 94,9] | +35,75 [+31,00; +42,40] | 35,4 [26,7; 56,0] | −34,5 [−49,2; −20,7] | 83% | 0,001 |

Base (sem reposicionamento): 2.010 corridas atendidas de 3.317 pedidos em 16 dias de março; 1.166 de 2.470 em 15 dias de setembro. A Tabela 7 (`tab11_principal.csv`) traz as três janelas, os três regimes e a grade inteira de α.

**Leitura por hipótese.**

- **H1 (redução do KM vazio por corrida): rejeitada.** Em nenhuma combinação de período, regime, janela e algoritmo com reposicionamento executado a estimativa pontual do KM vazio total por corrida diminuiu. Na Tabela 6, os aumentos vão de +2,6% (guloso conservador, setembro) a +35,8% (regra de limiar, setembro), todos com IC acima de zero. Nas janelas de 3 h ou com 1 a 2 movimentos executados no período, há 15 combinações cujo IC inferior toca ou cruza zero (mínimo de −0,44%); nenhuma tem estimativa pontual negativa. O KM de busca por corrida cai (de −0,1% a −6,1% na Tabela 6), mas o KM de reposicionamento supera essa economia. O resultado repete, agora com demanda total, o sinal negativo de setembro na base legada (DT011–DT012).
- **H2 (mais corridas na rampa e menos tempo de busca): apoio parcial e pequeno.** O reposicionamento aumentou as corridas atendidas em +0,2% a +2,9% (0,25 a 2,3 corridas por dia). Em setembro, todos os algoritmos tiveram ganho com IC acima de zero. Em março, só o proporcional e a regra de limiar; no guloso, o IC cruza zero. O tempo médio até o passageiro caiu de 1 a 35 s (de 0,2% a 6% de cerca de 560 s), e o KM de busca por corrida também caiu. O efeito fica muito abaixo do +8,1% do replay exploratório (ver 4.9).
- **H3 (KM vazio por corrida extra abaixo de um limite):** o melhor caso foi o guloso conservador e o intermediário em setembro, com 10,4 [7,8; 18,2] e 12,7 [8,8; 20,6] km vazios por corrida extra. Em março, nenhuma configuração ficou abaixo de 22 km. Para comparação, uma corrida imediata da janela tem em média 7,1 km (março) e 7,6 km (setembro) com passageiro, com mediana de 4,7–5,0 km. Cada corrida extra custa mais KM vazio do que uma corrida média percorre com passageiro. Se isso é aceitável depende do custo marginal por km e da margem por corrida, que não foram fornecidos (seção 4.8).

> **Figura 4** – Fronteira de Pareto por α (`fig04_fronteira_pareto`, `tab16_fronteira_pareto.csv`). Os pontos de α menor deslocam-se para a direita (mais KM vazio) sem ganho proporcional em corridas. Em março, a curva do regime B é quase horizontal.

## 4.6 Escada de informação

**Tabela 8** – Guloso intermediário (α = 0,2), janela 04–11h.

| Período | Regime | Execução | Precisão da escala | Revocação da escala | Corridas atendidas (%) | KM vazio por corrida (%) |
|---|---|---:|---:|---:|---:|---:|
| mar/2026 | A: D+1 estrito (20h) | 27% | 66% | 60% | −0,25 [−0,70; +0,16] | +3,08 [+2,58; +3,65] |
| mar/2026 | B: escala conhecida (fim de D) | 76% | 100% | 99% | +0,40 [−0,37; +1,20] | +9,88 [+8,36; +11,48] |
| mar/2026 | C: oráculo (diagnóstico) | 64% | 100% | 100% | +0,50 [+0,11; +0,93] | +7,66 [+6,39; +8,99] |
| set/2026 | A: D+1 estrito (20h) | 25% | 61% | 65% | +0,43 [+0,00; +1,08] | +3,27 [+2,38; +4,06] |
| set/2026 | B: escala conhecida (fim de D) | 81% | 100% | 99% | +2,06 [+1,21; +3,10] | +7,83 [+5,85; +9,65] |
| set/2026 | C: oráculo (diagnóstico) | 59% | 100% | 100% | +0,94 [+0,28; +1,89] | +6,60 [+5,14; +8,22] |

No regime estrito A, a escala prevista acerta só 61–66% dos motoristas e apenas um quarto das recomendações é executado; o ganho em corridas desaparece. A escala conhecida (B) eleva a execução para 76–81%. A revocação de 99% em B reflete motoristas sem posição conhecida antes do corte. O oráculo (C) não é um limite superior do ganho: executa menos que B (59–64%), porque o motorista já está trabalhando ou ocupado ao começar a janela, e o ganho é da mesma ordem. O principal gargalo não é a previsão de presença, e sim a relação entre o KM de reposicionamento e as poucas corridas que ele viabiliza.

> **Figura 6** – `fig06_escada_informacao`; dados em `tab15_escada_informacao.csv`.

## 4.7 Faixa horária e sensibilidade

Por janela, o guloso intermediário em B não recupera nenhuma corrida na janela 04–07h, isolada, em nenhum dos períodos (Tabela 7). Na janela 07–10h, o efeito é de −0,1% (março) e +0,8% (setembro). Os ganhos de 04–11h vêm de planos que antecipam a demanda das 7–9h (Figura 5). Na janela 04–07h, demanda e motoristas são tão escassos que o plano raramente muda alguém de lugar com ganho esperado positivo.

**Tabela 9** – Sensibilidade, uma variável por vez (março, teste, 04–11h, B, guloso intermediário; o baseline é recalculado com o mesmo parâmetro).

| Variação | Corridas atendidas (%) | KM vazio por corrida (%) | KM vazio por corrida extra | Tempo (s) | Execução |
|---|---:|---:|---:|---:|---:|
| referência | +0,40 [−0,37; +1,20] | +9,88 [+8,36; +11,48] | 68,7 [24,1; 523,7] | −10,4 [−15,9; −5,2] | 76% |
| fator rua/reta 1,2 | −0,29 [−0,92; +0,29] | +12,31 [+10,08; +14,86] | — [74,1; 676,1] | −5,4 [−12,5; +1,1] | 77% |
| fator rua/reta 1,6 | +0,67 [+0,16; +1,20] | +5,70 [+4,16; +7,19] | 31,1 [17,0; 115,0] | −13,9 [−23,4; −4,8] | 77% |
| velocidade −25% | +0,74 [+0,15; +1,50] | +10,57 [+7,43; +13,88] | 41,2 [22,9; 157,8] | −12,9 [−30,6; +2,7] | 76% |
| velocidade +25% | +0,19 [−0,50; +0,87] | +10,05 [+8,19; +12,25] | 139,0 [30,8; 570,7] | −5,9 [−12,0; +0,4] | 76% |
| raio −1 km | +0,83 [−0,23; +2,00] | +13,64 [+11,11; +16,18] | 37,2 [16,7; 289,7] | −10,6 [−19,1; −3,3] | 76% |
| raio +1 km | +0,52 [+0,00; +1,04] | +7,85 [+6,29; +9,64] | 49,4 [25,6; 253,9] | −11,5 [−22,3; −1,5] | 76% |
| paciência ×0,5 | +0,25 [−0,42; +0,99] | +10,64 [+8,08; +13,29] | 112,1 [32,6; 549,1] | −7,7 [−16,3; −0,3] | 76% |
| paciência ×2 | −0,14 [−0,88; +0,70] | +9,97 [+8,06; +12,18] | — [29,6; 601,6] | −6,2 [−15,6; +4,0] | 76% |
| cancelamento pós-aceite | +1,01 [+0,23; +2,04] | +9,26 [+7,17; +11,50] | 26,0 [13,8; 100,0] | −14,1 [−21,9; −6,1] | 76% |
| limite de distância 10 km | +0,99 [+0,42; +1,60] | +32,04 [+26,71; +37,73] | 88,8 [53,1; 203,3] | −16,9 [−23,8; −10,0] | 85% |
| treino de 28 dias | +0,75 [−0,10; +1,67] | +10,25 [+8,80; +11,86] | 39,3 [17,9; 263,2] | −13,4 [−20,7; −7,2] | 79% |
| treino de 84 dias (limitado ao disponível) | +0,70 [+0,00; +1,42] | +9,18 [+7,90; +10,55] | 37,8 [19,7; 228,6] | −11,9 [−18,9; −5,2] | 76% |
| treino com Carnaval | +0,55 [−0,35; +1,48] | +9,92 [+8,42; +11,55] | 50,9 [19,9; 467,8] | −8,4 [−13,8; −3,3] | 77% |
| previsão de Poisson | +0,55 [−0,44; +1,58] | +11,64 [+10,19; +13,44] | 59,3 [21,6; 584,8] | −10,7 [−16,2; −4,8] | 78% |
| regime A | −0,25 [−0,70; +0,16] | +3,08 [+2,58; +3,65] | — [27,9; 187,9] | −3,6 [−7,2; −0,2] | 27% |
| regime C | +0,50 [+0,11; +0,93] | +7,66 [+6,39; +8,99] | 43,6 [24,2; 149,5] | −3,4 [−9,3; +2,5] | 64% |
| B com execução no início do turno | +0,50 [−0,16; +1,48] | +3,26 [+1,54; +4,75] | 20,1 [5,6; 204,0] | −12,2 [−25,4; −3,2] | 32% |
| B com posição às 20h | +0,10 [−0,64; +0,84] | +7,24 [+5,76; +8,96] | 195,6 [21,5; 411,0] | −7,7 [−13,7; −1,8] | 60% |

Nenhuma variação inverte H1: o KM vazio por corrida aumenta em todas, de +3,1% a +32,0%. O ganho em corridas fica entre −0,3% e +1,0% e é mais favorável com fator rua/reta maior, velocidade menor ou limite de distância maior. Nesses casos a busca do baseline é mais cara ou o plano move mais motoristas, sempre com mais KM vazio por corrida extra. As variantes da primeira implementação de B (posição às 20h; execução no início do turno) dão resultados da mesma ordem (DT015). A conclusão não depende dessa correção.

> **Figura 5** – `fig05_efeito_por_hora`; dados em `tab12_por_faixa_horaria.csv` e `tab13_sensibilidade.csv`.

## 4.8 Ponto de equilíbrio

Sem custos inventados, o reposicionamento só compensa, para uma configuração com *e* km vazios por corrida extra, se a **margem de contribuição de uma corrida extra for maior que *e* × custo marginal por km**. Com *e* = 12,7 km (guloso intermediário, setembro), a margem por corrida extra precisaria superar 12,7 vezes o custo por km. Com *e* = 68,7 km (mesmo algoritmo, março), precisaria superar 68,7 vezes. A Tabela 10 (`tab14_ponto_equilibrio.csv`) lista *e* e seu IC para todas as configurações. A Figura 7 traça a margem mínima em função do custo por km, que fica como parâmetro a ser fornecido pela empresa ou pelo orientador.

> **Figura 7** – `fig07_ponto_equilibrio`.

## 4.9 Discussão

1. **Por que o KM vazio sempre sobe.** Pela desigualdade triangular, deslocar um motorista até uma zona e depois buscar o passageiro nunca percorre menos do que buscá-lo da posição original. O reposicionamento só "economiza" quando cria atendimento que não existiria ou corrige uma escolha míope do despacho. As duas coisas acontecem, mas raramente: a economia de busca (1–6% por corrida) é bem menor que o KM de reposicionamento adicionado.
2. **Por que o ganho em corridas é pequeno.** A rampa matinal é limitada por **oferta**: há poucos motoristas trabalhando antes das 6h, e mover os mesmos motoristas troca quem é atendido mais do que aumenta o total. A paciência efetiva é curta (≈ 2 min até `NaoAtendida`), e corridas agendadas ocupam parte da frota da manhã.
3. **Por que o replay exploratório (+8,1%) não se reproduziu.** O desenho atual é mais estrito em quatro pontos, todos documentados: (a) a recomendação só é executada na primeira disponibilidade do motorista e dentro do mesmo limite de distância (DT014); (b) as posições são as conhecidas no corte, nunca as de D+1, salvo no oráculo; (c) corridas agendadas e fora da janela bloqueiam o motorista; (d) a paciência foi calibrada nos tempos observados de desistência e de `NaoAtendida`. O sinal é o mesmo do exploratório (mais atendimento e menos espera, com mais KM vazio por corrida), mas de magnitude muito menor.
4. **Período.** Setembro responde melhor que março: demanda menor, aceite mais baixo e mais pedidos perdidos a recuperar. Isso sugere que o valor do reposicionamento depende do quanto a frota está descasada da demanda. O sinal de março (IC cruzando zero no guloso) mostra que o efeito não é robusto.
5. **Algoritmos.** O guloso de valor marginal é o único que oferece um controle explícito (α) para trocar KM por corridas. A regra de limiar é dominada: o proporcional (março) e o guloso agressivo (setembro) obtêm ganho semelhante com cerca de metade do KM vazio adicional. O proporcional, uma regra simples, teve desempenho comparável ao guloso intermediário. Otimizar melhor não mudou a conclusão, assim como no setembro legado (DT012).

## 4.10 Ameaças à validade

- **Construto:** KM vazio estimado (Haversine × fator), sem retorno nem odômetro; a definição corporativa segue pendente (DT003).
- **Interna:** baseline simulado que atende de 1,4 a 4,6 p.p. a mais que o aceite observado na janela 04–11h (de −0,9 a +7,5 p.p. nas janelas de 3 h); motoristas ociosos parados; velocidade constante; a correção de B foi feita após a primeira execução (DT015), e as duas versões são reportadas.
- **Estatística:** 15–16 dias pareados por período; IC largos para o KM vazio por corrida extra; muitas comparações sem correção. Os padrões que se repetem entre períodos e regimes (H1 rejeitada; H2 pequena) são os que sustentam a conclusão.
- **Externa:** uma região, dois meses, uma empresa; escala conhecida (B) ainda não confirmada como prática; adesão dos motoristas suposta pela regra de execução.

## 5 Conclusões

Com os dados de março e setembro de 2026 e um baseline simulado calibrado, a alocação preventiva D+1 **não reduziu o KM vazio por corrida** em nenhuma configuração (H1 rejeitada). Ela aumentou de forma modesta as corridas atendidas (até +2–3% em setembro; não significativo para o guloso em março) e reduziu o tempo e a distância de busca (H2 parcialmente apoiada). Cada corrida extra custou de 10 a 138 km vazios estimados (janela 04–11h), mais que a distância média com passageiro de uma corrida (≈ 7 km). Se isso compensa depende de custos que não foram fornecidos (H3 em aberto, como função do custo por km). Planejar às 20h com escala prevista (regime A) praticamente anula o efeito; o mecanismo só aparece com a escala de D+1 conhecida e o reposicionamento feito no fim do dia (regime B).

### O que posso afirmar / o que não posso afirmar

| Posso afirmar | Não posso afirmar |
|---|---|
| Nos dois meses e premissas testados, nenhuma configuração reduziu o KM vazio estimado por corrida. | Que o reposicionamento nunca reduz KM vazio em outra operação, região ou política de despacho. |
| O reposicionamento preventivo aumentou pouco o atendimento simulado (≤ +3%), com IC acima de zero em setembro. | Que a empresa ganharia esse atendimento na prática (adesão, comportamento e demanda não reagem no replay). |
| Cada corrida extra custou de ~10 a ~138 km vazios estimados, conforme o algoritmo, o regime e o mês. | Qualquer economia ou prejuízo em reais: custo por km e margem não foram fornecidos. |
| A perda de atendimento da rampa matinal está associada a motoristas livres longe (mediana de 3,6–5,3 km); a do pico das 17–19h, não. | Que a distância causa o não atendimento. |
| Com a escala prevista às 20h (regime A), o plano quase não muda o resultado. | Que a escala de D+1 pode ser conhecida na operação real (DECISÃO DO ALUNO, a confirmar). |
| A média do mesmo dia da semana é o preditor mais simples sem perda relevante nesta janela. | Que a previsão é boa por zona-hora (WAPE ≈ 1 com contagens esparsas). |
| Os números são reprodutíveis com um comando, a partir dos extratos com hash registrado. | Que os valores são KM rodado, KPI corporativo ou economia observada. |
