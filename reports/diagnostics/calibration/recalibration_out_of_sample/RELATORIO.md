# Rodada 5: recalibração temporal e teste fora da amostra (09/11/2026)

**Tudo aqui é análise posterior aos resultados congelados.** Os 120 resultados (dia × política) de setembro e outubro, os critérios E1–E3 e os
manifestos congelados não foram alterados. Plano escrito antes: `PLANO.md` (15:03). Calibração congelada às 16:59 (`calibracao_congelada.json`,
com SHA-256 do plano, deste script e do código do simulador). Setembro, outubro e 26/10–08/11 não foram usados na calibração.

Comandos (dados reais autorizados pelo proprietário só nesta rodada; somente leitura; processamento local; saídas agregadas):
`python scripts/pos_hoc_rodada5.py inventario | calibrar | teste | setout | mensal | componentes | intervalos` e
`python scripts/figura_rodada5.py`. Simulações rodaram uma vez cada, depois do congelamento; nenhuma foi repetida.

## 1. Inventário e extração

- Inventário por contagens (`inventario_por_*.csv`): dados em todos os dias de 01/01 a 08/11/2026; ~720 instantes de posição por dia em todos os
  meses; nenhum mês excluído por cobertura. Volume em queda ao longo do ano (pedidos em tempo real/dia: 1.249 em março, 946 em agosto, 874 em
  outubro); **quebra em 31/10** (149–395 pedidos e 25–68 motoristas por dia), vista antes de qualquer simulação.
- Extração somente leitura de 6 entidades (jan, abr–ago e 26/10–08/11; 1.000 lotes novos), mesma chave HMAC (`chave_id` 02f6c9316eb0),
  manifesto e SHA-256 por lote; nenhum lote existente foi regravado (assinaturas conferidas). Cadastro de veículos: **mantida a fotografia de
  08/11/2026**.
- Incidente: o caminho padrão do extrator e do `.env` apontava para `src/` (resto da reorganização). Os lotes foram gravados em
  `src/data/extraido/`, movidos para `data/extraido/` (só dias ausentes), e a cópia em `src/` foi removida. Reextrair dias já existentes
  reproduziu o conteúdo (posições de 20/01 e pedidos de 05/01 idênticos, salvo a coluna do instante de extração). Caminho corrigido em
  `data/reading/env.py` e `data/extraction/saida.py`, com teste.

## 2. Calibração (jan–ago, 242 dias elegíveis; 23/08 fora por < 200 pedidos)

| Medida | n | P25 | Mediana | P75 | Calibração de março |
|---|---:|---:|---:|---:|---:|
| Fator rua/reta da aproximação | 90.022 | 1,32 | **1,54** | 1,88 | 1,30 (n = 466) |
| Velocidade de aproximação (km/h) | 118.256 | 13,0 | **18,3** | 24,6 | 16,1 |
| Busca observada, registro → chegada (s) | 102.392 | 434 | 704 | 1.207 | — |

- O fator difere do de março pela fonte da distância: aqui, a distância aceite–chegada registrada na solicitação; em março, outro campo
  (`distMotorista`). A definição foi fixada no plano e não foi trocada depois de ver o valor. Fator e velocidade vêm da mesma distância, de modo
  que o par reproduz o tempo de aproximação observado; o nível do km estimado muda, o Δ% quase não (Seção 3.3 do artigo).
- Grade de raio × paciência (critério original): escolhidos **4,5 km e 240 s** (perda 0,102). Mesmo nesse ponto, o simulador atende
  **67,7%** contra **53,8%** de aceite observado; a espera mediana simulada é 571 s contra 704 s de busca observada. Igualar o aceite exige
  2 km e 60 s, e então a espera cai para 302 s. **Raio e paciência não fecham a defasagem.** A paciência ficou no limite superior da grade.
- Modelo de aceite descritivo (271.010 pedidos, 99% com distância ao motorista ofertado mais próximo): aceite de 64% com motorista livre a
  ≤ 0,5 km, 49% a 2–3 km e ~40% acima de 6 km; faixa 16–19 h com chance muito menor (coeficiente −0,86); pseudo-R² 0,05. Há recusa ou perda
  mesmo com motorista perto, o que o simulador não representa. O modelo não entrou no simulador.

## 3. Resultados

Valores: km vazio total do período (Δ%), ΔN em pedidos, IC95% da diferença média diária em km por *t* pareado. O *bootstrap* de blocos de 7
dias é **degenerado** com ≤ 7 dias (o bloco cobre a série) e não é usado nos subperíodos do teste nem nos 4 dias viários.

### 3.1 Teste fora da amostra, 26/10–08/11 (12 dias elegíveis; 01/11 e 08/11 fora por < 200 pedidos)

| Período | C×A km | IC95% km/dia | C×A ΔN | C×B km | IC95% km/dia | C×B ΔN | D×C km | D×C ΔN |
|---|---:|---|---:|---:|---|---:|---:|---:|
| 26/10–08/11 (12 dias) | −2,79% | −55,8 a +4,9 | −18 | +0,87% | −17,1 a +32,4 | +29 | −0,62% | +29 |
| 26–30/10 (5) | −3,68% | −135,0 a +17,6 | −3 | +1,13% | −58,6 a +92,9 | +34 | −1,10% | +19 |
| 31/10–08/11 (7) | −0,39% | −9,9 a +6,6 | −15 | +0,21% | −11,4 a +13,1 | −5 | +0,63% | +10 |
| Parâmetros de março, 12 dias | −2,18% | −39,1 a +6,0 | −31 | −0,46% | −23,8 a +17,0 | −8 | — | — |

C teve menos km que A em 7 dos 12 dias e mais que B em 8 dos 12. Participação do km vazio no km total modelado: 17,3% em A e em C (redução de
0,48% do km total de A; a participação praticamente não muda porque C também tem menos km com passageiro).

### 3.2 Setembro e outubro com a calibração nova (comparar com o congelado)

| Período | C×A km | C×A ΔN | C×B km | C×B ΔN | D×C km | D×C ΔN | Congelado C×A / C×B km |
|---|---:|---:|---:|---:|---:|---:|---|
| Setembro | −6,77% | −40 | −3,64% | +136 | −1,23% | −41 | −5,96% / −2,74% |
| Outubro | −4,62% | −54 | −2,83% | +55 | −2,04% | −25 | −5,04% / −1,40% |

Participação do km vazio no total: setembro 22,4% (A) → 21,4% (C); outubro 21,5% → 20,9%. Nos dois meses C atendeu menos que A.

### 3.3 Corte mês a mês (calibração com jan..m−1)

| Mês | C×A km | C×A ΔN | C×B km | C×B ΔN | A atendidos |
|---|---:|---:|---:|---:|---:|
| fev | −5,20% | +145 | −2,46% | +314 | 66,5% |
| mar | −6,04% | +64 | −3,68% | +211 | 73,1% |
| abr | −7,43% | −114 | −3,85% | +297 | 65,1% |
| mai | −7,55% | +122 | −4,76% | +369 | 68,5% |
| jun | −7,17% | +147 | −4,72% | +422 | 66,8% |
| jul | −5,69% | +92 | −2,62% | +99 | 67,3% |
| ago | −5,15% | +55 | −3,18% | +178 | 72,4% |

Em todos os meses de fevereiro a agosto, o IC95% (*t*) da diferença diária de km ficou abaixo de zero para C×A e C×B. Fevereiro e março
já tinham sido examinados no desenvolvimento.

### 3.4 Simulado × observado (política A), antes e depois da recalibração

| | Treino | Validação | Set | Out | 26–30/10 | 31/10–08/11 |
|---|---:|---:|---:|---:|---:|---:|
| Aceite observado (%) | 55,9 | 58,9 | 44,2 | 40,5 | 44,8 | 41,8 |
| Atendidos A, março (%) | 67,6 | 73,4 | 65,8 | 61,9 | 67,5 | 50,3 |
| Atendidos A, nova (%) | 67,9 | 73,8 | 66,0 | 62,0 | 67,6 | 50,5 |
| Aproximação observada, mediana (km) | 3,08 | 3,12 | 3,84 | 4,10 | 4,34 | 6,86 |
| Aproximação simulada A, março (km/atendido) | 2,50 | 2,44 | 2,66 | 2,69 | 2,43 | 2,42 |
| Aproximação simulada A, nova (km/atendido) | 2,99 | 2,93 | 3,18 | 3,18 | 2,94 | 2,82 |
| Busca observada, mediana (s) | 675 | 709 | 870 | 891 | 959 | 1.574 |
| Espera simulada A, março, mediana (s) | 521 | 504 | 578 | 588 | 501 | 543 |
| Espera simulada A, nova, mediana (s) | 564 | 540 | 625 | 613 | 539 | 563 |
| Motoristas simulados por dia | 106,8 | 111,3 | 86,7 | 74,3 | 78,4 | 50,3 |

A recalibração aproximou o km de aproximação e a espera, mas **não** o atendimento: a diferença simulado − observado continua de 9 a 23 p.p. (12 a 23 p.p. fora do período de baixa demanda).
(Aceite aqui = pedido com evento `CondutorACaminho`; difere levemente da definição da rodada 4, que somava encerradas e canceladas pós-aceite.)

### 3.5 Faixas sobre todas as variantes (rodada 4 + calibração nova; `intervalos_variantes.csv`)

Setembro e outubro, 14 variantes distintas (congelado, 8 de parâmetros, 4 de disponibilidade, calibração nova): C×A de −3,3% a −7,4% (set) e
−4,0% a −5,9% (out), IC95% *t* abaixo de zero em todas; C×B de −0,3% a −4,6% (set) e −0,8% a −2,8% (out), com IC95% *t* incluindo zero em 3 de
14 variantes em cada mês. **C atendeu menos que A em 5 de 14 variantes em setembro e em 12 de 14 em outubro**; C atendeu menos que B em 0 e 2.
No teste, C atendeu menos que A nas duas calibrações. Atendimento por dia: `atendimento_por_dia_variantes.csv`; figura
`article/figures/rodada5_diario.pdf`.

## 4. Leitura

- A redução de km de C contra A aparece em todos os meses de 2026 e em todas as variantes de setembro e outubro, mas **encolhe no teste fora da
  amostra** (−2,8%, intervalo que inclui zero) e quase some no período de baixa demanda de 31/10–08/11 (−0,4%). Mecanismo coerente: com poucos
  pedidos simultâneos por lote, a atribuição conjunta tem pouco a reordenar; isso é interpretação, não teste.
- A vantagem de C sobre B, estável de fevereiro a outubro (−2,5% a −4,8% por mês), **não apareceu no teste** (+0,9%, intervalo com zero). Com
  12 dias e uma quebra de regime, o teste tem pouco poder; não é evidência de efeito nulo nem de efeito contrário.
- O atendimento de C contra A é negativo em outubro e no teste sob quase todas as hipóteses; nos meses de fevereiro a agosto é positivo em 6 de 7.
- A defasagem simulado × observado no atendimento não foi resolvida pela recalibração: o simulador não modela recusa, e o aceite observado cai
  com a distância e no fim da tarde. A validação operacional continua não alcançada.

## 5. Decisões posteriores (com data)

- 09/11/2026, antes do congelamento: workers limitados a 6 após falha por memória virtual na primeira tentativa (nenhum resultado produzido).
- 09/11/2026, depois dos resultados: o *bootstrap* de blocos não é reportado para séries de ≤ 7 dias (degenerado); usa-se só o *t* pareado.
  Nenhuma simulação foi refeita por isso.
- 09/11/2026, depois dos resultados: figura e tabelas do artigo montadas a partir destes CSV; nenhum número novo além dos listados aqui.
