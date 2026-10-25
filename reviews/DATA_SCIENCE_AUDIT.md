# Auditoria de Ciência de Dados: TCC "Otimização da Alocação de Frota em Aplicativos de Transporte Urbano"

*Data: 2026-10-25. Modo: somente leitura sobre código, dados, artigo e resultados. Único arquivo criado: este relatório (mais scripts temporários fora do repositório, no scratchpad da sessão).*

---

## 0. Como ler este relatório

- **Verificado** = recomputado por mim com código executado nesta sessão, ou lido linha a linha no código. **Não verificado** = dito explicitamente (§9).
- Toda cifra desta auditoria vem de saída de código executado ou de arquivo lido, com o caminho citado. Não há número estimado de cabeça.
- **Limite central de execução.** Não reexecutei o `final-run` completo. `tcc-frota final-run` recusa rodar sem `TCC_REAL_DATA_AUTHORIZED=YES` (`src/tcc_frota/ingestion/files.py:16`). Esse portão protege dados da empresa e eu não o contornei. Toda análise numérica abaixo parte dos **agregados por dia e cenário já gerados** (`reports/runs/tcc_final/20261016T013428Z/individual/dias_cenarios.csv`, sem dados pessoais), de `reports/tcc_final/` e de `resultados/`. Isso permite refazer a inferência estatística e várias checagens de consistência, mas **não** refazer a simulação nem auditar os extratos brutos.

---

## 1. Resumo executivo

**Veredito curto.** O resultado central do trabalho, *"nenhum dos algoritmos que de fato moveram a frota reduziu o KM vazio por corrida no simulador"*, é **estatisticamente sólido e robusto a todas as ameaças que testei**. Reproduzi independentemente o efeito do guloso intermediário (+9,88% em março, +7,83% em setembro), com bootstrap em blocos, leave-one-out e as 19 sensibilidades do próprio `tab13`: o sinal não muda em nenhuma. O trabalho é, como TCC, rigoroso e honesto acima do esperado.

O que **não** se sustenta é o que o texto afirma *além* disso:

| Afirmação do artigo | Situação |
|---|---|
| H1 não se confirma para os algoritmos testados (no simulador) | **Sustentada** |
| "Nenhum dos 13 algoritmos reduz o KM vazio" | **Sustentada, mas enganosa**: 6 dos 13 quase não moveram veículos (≤ 3% dos motoristas) e não informam sobre a hipótese; só 7 são testes reais, e os 7 pioram |
| "A alocação preventiva funcionou como troca de km por atendimento, e não como economia" (resumo) | **Não sustentada como afirmação geral**: o lado "atendimento" é frágil (março: IC [−0,37; +1,20]%, 11 de 16 dias sem corrida extra) e o lado "não economia" é testado só contra uma previsão sem informação e uma função-objetivo que supera o ganho realizado em 6 a 60 vezes |
| "Critérios pré-registrados" | **Parcialmente**: o protocolo de calibração/teste foi commitado antes; o critério de H1/H2 por IC foi definido depois da execução (`tcc-artigo-latex/PENDENCIAS.md`, §1), o regime B foi redefinido depois de ver o teste (DT015), e houve um replay exploratório anterior, com efeitos maiores, que não aparece no artigo |
| "Os dados são reais; só o simulador é simulação" | **Enganosa**: todos os desfechos (KM, atendimento, tempo) são saídas do simulador |

**Achados novos mais importantes** (não estavam nos relatórios anteriores, ou estavam sem número):

1. **A previsão que alimenta o plano é pior que prever zero na faixa que mais importa.** WAPE por zona-hora 0,88–1,04 no modelo usado; na faixa 04–07h, IC 95% do WAPE de M0 = [1,06; 1,26] e de M1 = [1,04; 1,42], inteiramente **acima de 1** (ver §4, P-04).
2. **O valor que o guloso promete é de 6 a 60 vezes o que o simulador entrega, sem correlação diária** (março, α=0,2: 25,5 corridas/dia planejadas vs 0,50 realizadas; Spearman diário −0,03). Isso identifica *por que* o plano não funciona e quebra a leitura de que o resultado nulo é "do conceito".
3. **Os 7 algoritmos informativos estão todos na mesma fronteira adversa**, com custo crescente no km reposicionado. Isso indica um limite estrutural do desenho (raio de despacho 4,0–4,5 km > salto máximo 3 km > escala da zona H3 r7), e não um problema de escolha de algoritmo.
4. **Para o KM vazio por corrida cair, a busca precisaria encurtar 9,8–11,6% (guloso α=0,2); ela encurta 1,7–2,0%.** Esse é um argumento de ordem de grandeza que sobrevive ao erro de nível do simulador no pickup (−26% vs observado) e dá ao resultado nulo uma base quantitativa independente.
5. **Poder:** com 15–16 dias, o efeito mínimo detectável (80%) para o KM vazio/corrida é ≈ 3%. O efeito observado é +9,9% (sentido oposto) com IC [8,4; 11,5]: a hipótese de redução está excluída para esse algoritmo. Para MILP, NSGA-II e MILP robusto (0,00–0,08%) não há poder, porque quase não houve intervenção.

**Há evidências suficientes para sustentar as hipóteses no contexto de um TCC de graduação?** Sim para a conclusão *negativa e delimitada* (§12). Não para as conclusões gerais sobre "alocação preventiva" ou sobre "troca de km por atendimento".

---

## 2. Inventário das skills

| # | Skill solicitada | Localizada? | Carregada? | Origem / caminho | Uso efetivo |
|---|---|---|---|---|---|
| 1 | `data-scientist` (DAAF) | **Não** | **Não** | Nenhum arquivo com "DAAF" em `~/.claude/skills`, `~/.claude/plugins`, `~/.agents`; `.agents/.skill-lock.json` não a lista | **Indisponível. Não utilizada.** |
| 2 | `statistical-analysis` (Anthropic) | Sim | Sim | `anthropics/knowledge-work-plugins`, `data/skills/statistical-analysis`; `~/.claude/skills/statistical-analysis/SKILL.md` | **Utilizada** (significância vs relevância prática, comparações múltiplas, Simpson, sobrevivência, dependência) |
| 3 | `data-scientist` (tronghieu) | Sim | Sim | `tronghieu/agent-skills`, `skills/data-scientist`; `~/.claude/skills/data-scientist/` | **Utilizada**: fluxo *Review* (adversarial), regras não negociáveis (todo número vem de código executado; incerteza em toda estimativa), `checklists/leakage.md` e `checklists/analysis-review.md` |
| 4 | `data-science` (Absolutely Skilled) | **Não** | **Não** | Nenhuma skill com esse nome | **Indisponível. Não utilizada.** |

Notas de integridade:

- **Não houve conflito de sobrescrita** entre as duas `data-scientist`: só a versão tronghieu está instalada, e o lock registra apenas ela. Portanto **duas das quatro skills pedidas não puderam ser usadas** e este relatório **não alega** ter aplicado a metodologia DAAF (inferência causal/geoespacial) nem a da Absolutely Skilled.
- Existe a skill sincronizada `data-science-logistics-inventory` (outra origem; foco em estoque). **Não** foi usada como substituta.
- `senior-data-scientist` não foi utilizada, conforme pedido.
- Dos *scripts* da tronghieu (`profile_data.py`, `baseline_model.py`): **não se aplicam** (não há modelo preditivo supervisionado com CSV de entrada; o estimador de demanda é uma média por dia da semana). A porta de vazamento foi aplicada como lista de verificação semântica e mecânica (§5-A), não como script.

---

## 3. O que foi executado e o que não foi

| Atividade | Estado | Resultado |
|---|---|---|
| `python -m pytest -q` (venv do projeto, Python 3.12.14) | **Executado** | **179 aprovados, 1 ignorado**, sem falhas (72+72+36 pontos; 1 `s`) |
| Reexecução completa `final-run` com dados brutos | **Não executado** (portão de autorização, §0) | — |
| Recomputação do resultado principal a partir de `dias_cenarios.csv` | **Executado** | Reproduz o publicado (ver T-1) |
| Bootstrap em blocos circulares (L=3), 20.000 reamostragens | **Executado** | IC praticamente idêntico |
| Leave-one-day-out, autocorrelação lag-1, consistência por dia | **Executado** | Estável (ver T-1) |
| Efeito mínimo detectável a partir da dispersão diária | **Executado** | ≈ 3% (km/corrida), 0,3–5% (corridas), por cenário |
| Correlação diária entre ganho planejado e ganho simulado | **Executado** | Sem sinal (ver T-3) |
| Previsão: WAPE ≥ 1 por dia (comparação com "prever zero") | **Executado** | 3 a 4 dos 14–16 dias por conjunto |
| Conferência dos números do resumo/conclusão contra `resultados/` | **Executado** | Conferem (−0,71%; 61/135=45%; 108/135=80%; +9,9/+7,8%) |
| Diff de `v2/sim.py` entre o commit do run publicado (`69b8647`) e `HEAD` | **Executado** | Só rastreamento (`trace`, `move_outcomes`); nenhuma decisão do replay mudou |
| Leitura integral de `v2/{sim,fleet,rules,policy,stats,forecast,experiment,final_run}.py`, `algoritmos/{estatistica,protocolo}.py` (até l.120), `analise/demanda.py` (cabeçalho), artigo `sections/00`, `03`, `05` | **Executado** | — |
| Auditoria dos extratos brutos, Silver/Gold, deduplicação, outliers | **Não executado** (dados) | Só agregados (`tab01`, `tab02`, `tab05`, `result.json`) |

### T-1. Recomputação independente (guloso α=0,2, regime B, janela 04–11h)

| | Março | Setembro |
|---|---|---|
| Publicado (`tab11`) | +9,88% [8,36; 11,48] | +7,83% [5,85; 9,66] |
| Meu bootstrap i.i.d. (20.000) | +9,88% [8,35; 11,45] | +7,83% [5,94; 9,68] |
| Bootstrap em blocos circulares L=3 | [8,51; 11,13] | [5,85; 9,55] |
| Leave-one-day-out | 9,51 a 10,34 | 7,41 a 8,20 |
| Autocorrelação lag-1 do efeito diário | 0,02 | 0,25 |
| Dias com efeito > 0 | **16 de 16** | **14 de 15** |
| KM vazio/corrida (base → proposto) | 2,648 → 2,909 | 2,596 → 2,800 |
| Busca/corrida (base → proposto) | 2,648 → 2,603 (−1,7%) | 2,596 → 2,545 (−2,0%) |
| Reposicionamento/corrida | 0,306 km | 0,255 km |

**Conclusão de T-1:** a dependência temporal é fraca, nenhum dia isolado domina e o efeito é positivo em quase todos os dias. A inferência de H1 é sustentável.

---

## 4. Matriz de problemas

Convenção: **CRITICAL** = compromete a validade de uma conclusão *declarada* no artigo; **MAJOR** = altera materialmente tamanho, confiança ou interpretação; **MINOR** = precisão, clareza ou higiene. "Estado": **NOVO** = não estava nos relatórios anteriores (ou estava sem evidência); **CONFIRMADO** = já conhecido e confirmado por mim; **REFINADO** = conhecido, mas minha evidência muda o alcance.

### CRITICAL

| ID | Problema | Evidência (arquivo, cálculo) | Impacto | Estado |
|---|---|---|---|---|
| **C-01** | **A afirmação "troca de km por atendimento" (resumo l.21-22; considerações l.50-52) não é sustentada.** O lado "atendimento" é frágil e o lado "não economia" é consequência parcial do desenho. | Março, guloso α=0,2: corridas +0,40% **IC [−0,37; +1,20]**, extras 0,50/dia, **11 de 16 dias com extras ≤ 0**. Setembro: +2,06% [1,21; 3,10], extras 1,60/dia, 4 de 15 dias ≤ 0. `tab13`: efeito em corridas oscila de −0,29% a +1,01% nas 19 sensibilidades (IC contém 0 em 13 de 20 linhas, incluindo a referência; 15 se contarmos limites iguais a 0,00). Baseline estático (`sim.py:237-251`, `become_free` só atribui pedidos; não há evento de deslocamento voluntário): reposicionar é custo puro; só reduz km se mudar *quem* atende. | O resumo converte "KM sobe de forma robusta; corridas extras são pequenas e dependem do mês" em uma lei geral ("função de troca"). Um examinador pode derrubar a frase com o IC de março. | CONFIRMADO + NOVO (contagem de dias, oscilação em `tab13`) |
| **C-02** | **Sem limite superior (oráculo de demanda), o nulo não separa "conceito ruim" de "previsão + objetivo ruins".** O regime C é oráculo só de *frota*; a demanda do plano é sempre `fc.predict(...)` (`experiment.py:139`). | (a) WAPE zona-hora do modelo usado (`media_dia_semana`): 0,967 / 0,957 (mar cal/teste), 1,043 / 0,882 (set cal/teste); dias com WAPE ≥ 1: 4/14, 4/16, 4/14, 3/15 (`previsao_por_dia.csv`). **WAPE = 1 é o erro de prever zero.** (b) Faixa **04–07h** (a que mais deveria render): M0 1,15 [1,06; 1,26], M1 1,18 [1,04; 1,42] (`resultados/demanda/wape.csv`), IC inteiro > 1. (c) **Ganho planejado vs realizado** (T-3): razão 0,017 a 0,16, Spearman diário −0,17 a +0,27 (único p<0,05: α=0,5 em setembro). | A planejadora otimiza uma previsão sem informação espacial a uma função-objetivo que não prevê o simulador. O experimento testa *este* par previsão+objetivo, e o texto o generaliza à "alocação preventiva". | CONFIRMADO (ausência do oráculo) + NOVO (quantificação P-04/T-3) |

### MAJOR

| ID | Problema | Evidência | Impacto | Estado |
|---|---|---|---|---|
| **M-01** | **O regime principal B usa a escala real de D+1.** `chosen = sorted(actual)` com `actual = {d.did for d in world}`, o mundo observado de D+1 (`fleet.py:180, 189-190`). Além disso a execução é instantânea e sem custo de tempo: o motorista "teleporta" à zona-alvo ao iniciar a sessão (`sim.py:261-279`; `jobs.append((did, t, t, ...))`), e o corte de frota é 24h enquanto o de demanda é 20h (`fleet.py:177-179`; `CUT_HOUR = 20`). | Regime A (D+1 estrito, escala prevista): execução 82 de 306 movimentos em março (27%) e 42 de 168 em setembro (25%); efeito em km +3,08% / +3,27%, em corridas −0,25% / +0,43% (`tab11`). | O título fala em D+1; o único regime estritamente D+1 quase não executa. **Direção do viés: favorece a hipótese**, logo o nulo é *conservador* quanto a esta ameaça. A ameaça é de *construto/representatividade*, não de falso negativo. | CONFIRMADO + NOVO (execução 25–27%, teletransporte, cortes distintos) |
| **M-02** | **O KM de busca simulado não foi validado contra o observado, e o nível está ~26% abaixo.** Calibra-se aceite e tempo mediano, não distância (`experiment.py:244`). | Observado (`resultados/pickup/pickup_realizado_decis.csv`): média 3,58 km (mar), 3,65 (set), mediana 3,45/3,46, **cobertura de apenas 25,7% e 23,2% das aceitas**. Simulado baseline: 2,65 / 2,60, mediana 2,46 / 2,47. Velocidade de busca (16,1 km/h) é derivada de aceite→chegada e absorve atrasos de reação. | O nível do denominador de H1 está subestimado e a amostra observada pode ser seletiva (só 1 em 4 corridas tem o campo). **Mitigação:** o ponto de equilíbrio (reduzir a busca ≥ 9,8–11,6% vs 1,7–2,0% obtido) segue válido; com busca-base de 3,58 km, o necessário seria 0,306/3,58 = 8,5%, ainda várias vezes o obtido (1,7–2,0%). | CONFIRMADO + NOVO (cobertura, argumento de equilíbrio) |
| **M-03** | **"Nenhum dos 13" mistura 7 testes reais com 6 intervenções quase nulas.** | Fração de motoristas movidos (`resultados/finalistas_*.csv`, regime B): MILP 0,07/0,09%, NSGA-II 0,03/0,02%, MILP robusto 0,03/0,04% (ESSENCIALMENTE VAZIOS); LNS 1,20/0,69%; recozimento 2,83/0,66%; PSO 2,66/0,60%. Informativos: fluxo 5,6/5,4%, húngaro 8,9/8,3%, guloso α 0,05/0,2/0,5: 32,7/19,9/8,6% (mar), proporcional 31,8/28,0%, limiar 50,5/49,8%. Todos os 7 informativos têm km_vazio_var > 0 com IC > 0; o seletivo (C2) moveu **0** motoristas. | O artigo diz isso em parte, mas o resumo e a conclusão contam "13". A evidência sobre a hipótese vem de 7 configurações (3 delas o mesmo guloso com α diferente). | CONFIRMADO + NOVO (quantificação) |
| **M-04** | **O baseline mantém os livres parados e o KM de retorno não é medido** (`sim.py:237-251`; `limitacoes.md` itens 1 e 11). | O KM vazio dos dois cenários é incompleto, com viés de direção desconhecida. O artigo reconhece, mas não mitiga (nenhuma análise com baseline "à deriva"). | O resultado vale contra uma política que ninguém executa. Em particular, "não como economia" fica parcialmente garantido pelo desenho. | CONFIRMADO |
| **M-05** | **Calibração fracamente identificada.** Dois parâmetros (raio, paciência) ajustados a dois momentos; superfície quase plana. | Março: perda 0,0065 (4,5 km; 180 s), 0,0074 (5,0; 60 s), 0,0076 (4,5; 90 s), 0,0078 (4,5; 120 s): configurações com paciências de 60 a 240 s empatam em ruído (`tab08`). Fora da amostra (`tab09`): atendimento simulado 60,6% vs 56,0% (mar, teste), 47,2% vs 45,8% (set); na faixa 04–07h: 26,5% vs 21,9% e 22,3% vs 16,2%. | Afeta o lado *atendimento* (C-01). Para H1 é inócuo: as 19 sensibilidades (raio ±1 km, paciência ×0,5/×2, fator 1,2/1,6, velocidade ±25%) mantêm IC > 0 (estimativas pontuais de +3,1% a +32,0%; menor limite inferior do IC: +1,54%). | CONFIRMADO (parcialmente REFINADO: neutro para H1) |
| **M-06** | **Inferência sobre `e` (km vazio por corrida extra) e destaque dos máximos de 13 cenários no resumo.** | Denominador de poucas corridas (guloso α=0,2 em março: 0,50/dia → ≈ 8 extras em 16 dias): `e` = 68,7 com **IC [24,1; 523,7]**. "Até 45% (LNS) e 80% (PSO)": são o máximo entre 13 cenários; PSO em setembro tem 0,2267 extras/dia (≈ 3,4 corridas no período); pelo limite superior do IC a fração cai a 0% (mar) e 25% (set: 34/135). | Winner's curse + razão de denominador minúsculo. A grade é definida pelos autores e sem limiar. | CONFIRMADO |
| **M-07** | **"Pré-registro" e "critérios pré-registrados" excedem o que houve.** | Verificável no Git: registro da bateria `d321f4d` 16/10 12:09 → finalistas congelados 13:19 → teste 14:09 (sequência correta). Mas: (i) o critério de H1/H2 por IC foi "definido nesta revisão, depois da execução" (`PENDENCIAS.md` §1); (ii) o regime B foi corrigido "depois de ver o teste" (DT015); (iii) a bateria e o seletivo nasceram depois de o `final-run` de 15/10 22:34 já ter mostrado resultado adverso **nos mesmos dias de teste**; (iv) existiu um replay exploratório com efeitos maiores (corridas +8,1% vs +0,40%) cujos arquivos não existem (`AUDITORIA_BATERIA.md` §5) e que o artigo não menciona; (v) o registro é interno, sem carimbo externo (qualquer commit é reescrevível). | Para um resultado **negativo** isso não infla falso positivo, mas torna a palavra "pré-registrado" em selo que a evidência não sustenta, e o conjunto de teste foi consultado muitas vezes. | CONFIRMADO + NOVO (item iv: arquivo ausente; item iii: ordem temporal) |
| **M-08** | **Premissa de oferta vs comportamento: a demanda "recuperável" depende da faixa horária.** O simulador atribui todo pedido a um livre dentro do raio com aceite certo. | `tab04`: na faixa **04–07h** o não aceite é 70,4% (mar) / 78,1% (set) e só 17,0% / 34,1% dos não aceitos tinham livre a ≤ 2 km (mediana do livre mais próximo 5,3 / 3,6 km): **limitado por oferta**. Em 08–16h (41–46%) e 17–19h (53–55%) a maioria tinha livre próximo: **limitado por comportamento**. | O relatório anterior citou 53–55% sem notar que isso é a faixa **17–19h, fora da janela do estudo**. Para 04–07h a premissa de oferta se sustenta; para 07–11h os dados agregados de `tab04` não separam. | REFINADO |
| **M-09** | **Os parâmetros do guloso principal foram escolhidos por "corridas extras por km extra", não pela métrica de H1.** | `experiment.py:257-263`, `final_run.py:256,262`: `score = dr/dk`. A bateria, ao contrário, escolhe o finalista pelo **menor KM vazio/corrida com piso de atendimento** (`ORCAMENTO_CONFIGURACOES.md` §1). | Atenuado: a grade completa de α é reportada no teste (`tab11`), e o efeito sobe monotonicamente com a intensidade (α=1,0: +0,82% / +0,04% ≈ nenhum movimento). Nenhum α reduz o KM. | REFINADO (limitado às referências) |

### MINOR

| ID | Problema | Evidência | Estado |
|---|---|---|---|
| m-01 | Estatística do p de Holm (média das diferenças diárias de razões, `stats.py:105-106`) ≠ estatística do IC (razão de somas, `stats.py:68-71`). | Código | CONFIRMADO |
| m-02 | Teste de permutação é bilateral (`stats.py:42`), a hipótese é unilateral; Holm só cobre KM vazio/corrida, não H2 nem `e`. Nenhum impacto prático: todos os efeitos de H1 são ≥ 0. | `estatistica.py:32-40` (Holm correto) | NOVO |
| m-03 | Índices do percentil do bootstrap truncam (`int(0.025*(n-1))`), viés < 1 posição em 2.000. | `stats.py:26-27` | NOVO (irrelevante) |
| m-04 | Texto "56 dias antes de cada mês" vs janela móvel de 56 dias antes de cada dia-alvo, excluindo Carnaval (`forecast.py:56-60`). A seção de método já diz "anteriores ao dia do corte". Só a seção de dados é imprecisa. | Código vs `03-metodologia.tex:43` | CONFIRMADO |
| m-05 | Mistura de modelos de previsão: o artigo cita WAPE global 0,86–0,93 (M0/M1) e Poisson 1,48–1,50 (M2, sklearn, Bloco 1 exploratório) mas o plano usa `media_dia_semana` (Msim), e o Poisson interno da v2 (`tab07`: 0,92–0,97 no teste) é outro. | `analise/demanda.py:1-12` vs `forecast.py:16` | CONFIRMADO |
| m-06 | Assimetria de posição noturna: o baseline começa na posição real da sessão; o proposto parte da última posição de D. Mediana da distância entre as duas = 0,49 / 0,46 km, p90 = 4,97 / 3,98 km (`tab05`). Para ~10% dos motoristas a diferença excede o salto máximo de 3 km. | `tab05`, `sim.py:261-279` | CONFIRMADO |
| m-07 | Em `inicio_turno` (regime A e uma sensibilidade), o reposicionamento tem prioridade sobre pedidos em espera (`sim.py:241`, `try_move` antes do laço `waiting`). Não afeta o regime B. | Código | NOVO |
| m-08 | Resolução H3 r7 fixada sem comparação (aresta ~1,2–1,4 km < salto 3 km < raio 4–4,5 km). Já declarado. | `03-metodologia.tex:151-154` | CONFIRMADO |
| m-09 | Semente 20261016 duplicada em 4 módulos; `scipy` importado em `algoritmos/{fluxo_custo_minimo,hungaro,milp,sim_estendido}.py` mas ausente das dependências (`pyproject.toml:10 dependencies = []`; `scipy~=1.15.3` só em `[tool.uv] constraint-dependencies`, l.237); `--daily` padrão aponta para `reports/runs/tcc_final/20261016T013428Z/...` fora do Git (`algoritmos/cli.py:21`); orquestração só PowerShell. | Verificado por leitura/grep | CONFIRMADO |
| m-10 | Seleção de política só em março (`experiment.py:42`) e sensibilidade só em março (`final_run.py:414`). O artigo precisa declarar a assimetria; hoje declara parcialmente. | Código | CONFIRMADO |

---

## 5. Análises obrigatórias

### A. Engenharia e qualidade dos dados

**Verificado (agregados):** as contagens ingeridas por lote (`result.json: contagens_ingeridas`) somam 205.983 solicitações; o universo do replay é 117.309 após exclusão de agendadas (79.161), fora da caixa (1.257) e não-demanda (4.652 pagamento + 1.977 retraçamento + 1.621 operador + 6 transitórios). `tab02`: 100% das corridas encerradas com tempos ordenados nos seis meses (jan, fev, mar, jul, ago, set), cobertura de coordenadas de origem 100% (jan e fev conferidos linha a linha), `nu_dr_real_pendente` 33% em janeiro (campo não usado). Manifestos reconciliam com as contagens (relatado em `docs`; **não** reconferido por mim).

**Checklist de vazamento (tronghieu `checklists/leakage.md`), aplicada ao pipeline D+1:**

| Item | Resultado | Evidência |
|---|---|---|
| Semântica temporal do treino | **OK** | `forecast.py:56-60`: `first <= d < cut`, cut = D (dia do corte excluído); `predict` ainda restringe a `safe = history.restricted(cutoff_date(target))`, redundante e correto |
| κ (corridas por motorista-hora) | **OK** | `experiment.py:128-134`: usa dias até D, janela 4–11h, antes do corte de 20h |
| Centróides das zonas | **OK** | `plan_inputs` soma só `train` |
| Calibração do simulador | **OK** | `measured_parameters(period.calibration)` e grade de calibração usam só dias 2–15 |
| Seleção de hiperparâmetros | **OK** | só calibração de março (`final_run.py:228-229`); finalistas commitados antes do teste (`protocolo.py`; Git) |
| Planejadores que simulam no laço | **OK** | pseudodias anteriores a D; "o dia D+1 real nunca é simulado pelo planejador" (`ORCAMENTO_CONFIGURACOES.md` §1) |
| **Frota do regime B** | **VAZAMENTO DECLARADO** | `fleet.py:190` usa a escala real de D+1 (M-01). Direção favorável à hipótese |
| Sessões do mundo, posições iniciais | OK (são o *mundo*, idêntico nos dois cenários) | `build_world` |
| Mesmo mundo nos pares | **OK, verificado por assinatura** | `sim.py:84-91`, `experiment.py:213-214` |
| Retenção do teste "usada uma vez" | **NÃO** | Dias de teste consultados no `final-run`, nas 19 sensibilidades, na bateria, no seletivo e nos Blocos 1–3. Irrelevante para um nulo, mas relevante para qualquer sinal positivo |
| Sonda "bom demais" | Não aplicável | o resultado é desfavorável, não suspeito |

Veredito: **sem vazamento de informação futura além do declarado em B.** Não pude auditar dedup/outliers/identificadores nos extratos brutos.

**Representatividade:** dois meses, uma empresa, uma região; 14 dias de calibração e 15–16 de teste; janela de 7h; 207 e 177 motoristas distintos no mês (109 e 87 por dia). 25% de cobertura do campo de distância no pickup observado (M-02). A caixa geográfica retangular (`rules.py:18-20`, RN002 pendente) exclui 1.257 pedidos (0,6%).

### B. Estatística e inferência

| Aspecto | Avaliação |
|---|---|
| Bootstrap pareado por dia (`stats.py:13-28`) | Correto e **reproduzido** (T-1). Percentil, 2.000 reamostragens, semente fixa |
| Dependência temporal | Autocorrelação lag-1 do efeito diário 0,02 (mar) e 0,25 (set); bootstrap em blocos dá IC praticamente igual. **Não é problema para H1**; seria para `e` |
| Permutação por troca de sinal (`stats.py:31-46`) | Exata até n=16, correta. Bilateral (m-02). Estatística diferente da do IC (m-01) |
| Holm (`estatistica.py:32-40`) | Implementação correta (passo a passo, monotônica) |
| Bonferroni | Aplicado ao IC de KM vazio e de corridas na bateria |
| Tamanho de efeito | Relatado em % e em km; `e` instável (M-06) |
| **Poder / efeito mínimo detectável** | **Ausente no artigo.** Meu cálculo (80%, α=0,05, via dispersão diária): km/corrida ≈ 3,1% (guloso α=0,2) e 1,3–1,6% (α=0,5); corridas ≈ 1,4% (mar) e 2,4% (set) para α=0,2, 0,3–0,8% para α=0,5. **O efeito de H1 observado (+9,9%) excede 3 vezes o MDE, em sentido oposto.** Para os 6 algoritmos quase vazios o MDE é irrelevante: não há intervenção |
| Múltiplas comparações | Holm só em KM vazio/corrida entre 13. 19 sensibilidades, 3 janelas × 3 regimes × 9 cenários × 2 meses, 7 desfechos primários, sem família declarada. Neutro para H1 (todos os sinais coincidem), relevante para qualquer "achado" em corridas ou tempo |
| Ausência de significância ≠ ausência de efeito | **O artigo respeita** em H1 (o IC exclui redução) e em H2. Em corridas de março ("sem diferença estatística"), o IC [−0,37; +1,20] **não permite afirmar ausência de ganho nem ganho**: diz que o estudo não tem poder (MDE 1,4%) |
| IC na escala da razão | Razão de somas com n=15–16 dias: cobertura nominal não verificada por simulação. Em H1 há folga (IC a 8% do zero); em `e`, não |

**Confirmação:** as conclusões **de H1** são estatisticamente sustentáveis. As conclusões em **corridas (H2), em `e` e na grade** são frágeis e dependem de máximos entre cenários.

### C. Validação do simulador

Leitura integral de `sim.py`, `fleet.py`, `rules.py`:

- **Regra de despacho:** o livre mais próximo em linha reta dentro do raio (`sim.py:307-310`), fila FIFO com paciência (`sim.py:313-314`, `244-251`). Determinística. Não modela recusa nem ordem de oferta; no teste, março tem aceite observado de 56,0% contra 60,6% simulado e setembro 45,8% contra 47,2% (`tab09`).
- **Disponibilidade:** sessões reais, compromissos externos como bloqueios, sem ocupação simultânea (`AssertionError` em `sim.py:288-289`; testes passam). `eligible()` rejeita corridas que colidam com compromissos futuros (`sim.py:206`), conservador.
- **Movimento de livres:** inexistente (M-04).
- **KM vazio:** `pickup_km + reposition_km` (`sim.py:79-81`), por rua = Haversine × fator (fator de busca 1,30 / 1,38, medido na calibração). Sem retorno.
- **Fidelidade ao observado:** nível de atendimento +4,6 pp (mar teste) e +1,4 pp (set teste); busca simulada ~−26% abaixo da observada (M-02); mediana do tempo até o passageiro 564 vs 604 s (mar) e 543 vs 594 s (set).
- **Pergunta específica do pedido: o erro do simulador compromete a interpretação dos ganhos?**
  - *H1 (KM/corrida):* **não**. Delta pareado, mesmo mundo, sinal invariante às 19 perturbações; o equilíbrio exigido (≥ 9,8% de queda na busca) é uma ordem de grandeza acima do obtido (1,7–2,0%).
  - *Atendimento / corridas extras:* **sim**. O ganho (8 corridas em 16 dias em março) é menor que o erro de nível (≈ 150 pedidos de 3.317) e a oscilação em `tab13` cobre zero. Aqui o relatório anterior estava certo; a diferença é que o erro de *nível* cancela em parte no delta pareado, mas o erro de *mecanismo* (aceite certo, sem recusa) não.
- **Viés de direção:** teleporte sem tempo (favorece a proposta), aceite certo (favorece a proposta), roster perfeito em B (favorece a proposta), baseline estático e sem retorno (indeterminado). **Todos os vieses identificados de direção conhecida favorecem a hipótese e mesmo assim ela é rejeitada.**

### D. Algoritmos de otimização

- **Equivalência de condições:** mesmo simulador, dias, baseline, assinatura SHA-256 (`experiment.py:213`); sementes 11/23/37/41/53 e média por dia para estocásticos; pseudodias sem D+1.
- **Espaço de ação desigual:** referências com salto 3 km; bateria com H ∈ {3, 4} (fluxo/húngaro), 4 (demais), 1,5–6 (NSGA-II); orçamentos de 300 avaliações para LNS/SA/NSGA/PSO. Registrado no pré-registro; é uma assimetria, não um viés demonstrado.
- **Critério de seleção desigual** (M-09): as referências do artigo pelo escore `dr/dk`; a bateria pelo H1 com piso 0,99. Para H1 a bateria é o teste justo; as referências são uma fronteira.
- **Função-objetivo:** `V(x)=Σ min(λ, κ·m)` com associação zona-motorista por centróide ≤ ρ (`policy.py:54-56`). Supõe oferta local por zona; o despacho real usa raio 4,0–4,5 km. Isso explica **por que o ganho planejado é 6–60 vezes o realizado** (T-3): mover um motorista 3 km dentro de um raio de 4 km raramente muda quem fica dentro do alcance de um pedido.
- **Dose-resposta entre algoritmos (todos adversos e ordenados por km reposicionado, regime B, março):** LNS 2,2 km/dia → +0,43%; fluxo 9,9 → +2,6%; húngaro 16,6 → +4,0%; guloso α=0,5 14,7 → +3,6%; α=0,2 38,6 → +9,9%; proporcional 33,5 → +8,2%; α=0,05 66,5 → +16,8%; limiar 102,2 → +28,5%. O ganho em corridas extras por dia não cresce junto (−0,31 a +1,38 por dia). **Interpretação (hipótese, não comprovada):** o limite é estrutural (escala espacial), não de algoritmo.
- **Seletivo (C2):** 0 movimentos nos dois meses. Cumpre critério de segurança e **não informa** sobre H1.

### E. Experimentos e reprodutibilidade

| Item | Avaliação |
|---|---|
| Regimes A/B/C | A = escala prevista por presença ≥ 50% em dias comparáveis, posição às 20h, execução no início do turno; B = escala real de D+1, posição no fim de D, execução ao iniciar a sessão; C = oráculo de frota. A diferença A→B (27% → 76% de execução; km +3% → +10%) mostra que **o efeito adverso acompanha a adesão** (associação entre regimes, não causalidade comprovada), e não o contrário |
| Informação D+1 | Plano depende só de D e anteriores, **exceto** a lista de B (M-01) |
| Treino/teste | Cronológico, 2–15 / 16–fim. Sem aleatorização |
| Sementes | Bootstrap fixo; simulador determinístico; sem uso de `random` global |
| Rastreabilidade | `result.json` com `git_head`, hashes SHA-256 dos arquivos de entrada, sementes, parâmetros medidos; checagem independente (`scripts/checagem_independente.py`) |
| Código no commit do run vs `HEAD` | `v2/sim.py`: só rastreamento (verificado no diff). O restante do diff são módulos novos (bateria, análises) |
| Execução dos pipelines | Testes passam (179); `final-run` **não reexecutado** (portão de dados) |
| Dependências | `scipy` não declarada (m-09); `uv.lock` não validado |

### F. Consistência científica (afirmação → evidência)

| Afirmação | Evidência | Classe |
|---|---|---|
| H1 não se confirma (nenhum IC < 0) | `finalistas_*.csv`, `tab11`; recomputação T-1 | **Resultado simulado**, comprovado |
| +9,9% (mar), +7,8% (set) | `tab11`; recomputado | Resultado simulado, comprovado |
| Faixa 0,00% a +35,75% | `finalistas_setembro.csv` (limiar 35,75); mínimos ≈ 0,01 | Comprovado |
| Menor LI de corridas −0,71% (fluxo, mar) | `finalistas_marco.csv`: −0,7103 | Comprovado |
| "Todos cumpriram não inferioridade" em corridas | LI mínimo setembro = −0,03; março = −0,71 | Comprovado |
| 61/135 = 45% (LNS, mar); 108/135 = 80% (PSO, set) | `equilibrio_cenarios.csv` | Comprovado como **máximo entre cenários**, sob grade dos autores (hipótese) |
| "Pickup das extras é maior" e "custo quase todo do reposicionamento" | Não reverificado (M-06 aponta o denominador) | **Exploratório, inferência** |
| "Funcionou como troca" | C-01 | **Conclusão não comprovada** |
| "O simulador está calibrado" | `tab08/09`; M-05 | **Hipótese de modelagem**, com erro declarado em `tab09` |
| "179 testes aprovados, 1 ignorado" | **Executado: 179 passed, 1 skipped** | Comprovado |
| "Os dados são reais; só o simulador é simulação" | todo desfecho é saída do simulador | **Enganosa**; sugerir "insumos históricos; a resposta ao plano é simulada" |

---

## 6. Problemas já conhecidos: confirmados ou descartados

| Fonte | Item | Veredito |
|---|---|---|
| `reviews/code_review_report.md` | 179 testes não reconfirmados | **Confirmado** (179 aprovados, 1 ignorado) |
| idem | Treino "56 dias antes de cada mês" vs janela móvel | **Confirmado** (m-04); só a seção de dados está imprecisa |
| idem | Seleção/sensibilidade só em março | **Confirmado** (m-10) |
| idem | "13 algoritmos" = 13 configurações (3 do guloso) | **Confirmado**, agravado por M-03 |
| idem | p de Holm ≠ estatística do IC | **Confirmado** (m-01) |
| idem | `scipy` fora das dependências; run-id fixo no CLI | **Confirmados** (m-09) |
| idem | "Não foi lido `fleet.py`/`sim.py`/`rules.py`/`policy.py`" | **Resolvido**: lidos integralmente; reposicionamento entra no total (`sim.py:230,276`); corte D+1 correto exceto a escala de B (M-01) |
| `PRE_SUBMISSION_REVIEW` | Efeito menor que o erro do simulador | **Refinado**: válido para corridas, **não** para H1 (delta pareado; sinal invariante a 19 perturbações) |
| idem | Demanda "não atendida" não recuperável | **Parcialmente descartado**: o dado citado (53–55%) é da faixa 17–19h, fora da janela; em 04–07h a oferta é limitante (M-08) |
| idem | Baseline estacionário | **Confirmado**, sem mitigação (M-04) |
| idem | Falta oráculo de demanda | **Confirmado** (C-02) e reforçado por novos números |
| idem | Regime B usa a escala real de D+1 | **Confirmado** (M-01); direção favorável à hipótese |
| idem | Algoritmos afinados para outro objetivo | **Refinado**: só as referências (M-09); a bateria usa H1 |
| idem | Pickup simulado < real amostrado | **Confirmado** e quantificado (M-02) |
| idem | ICs de `e` enormes; máximos no resumo | **Confirmado** (M-06) |
| idem | Dias não independentes; bootstrap frágil em razões | **Parcialmente descartado** para H1 (bloco ≈ i.i.d.; AC1 baixa); **confirmado** para `e` |
| idem | Pré-registro não verificável externamente | **Confirmado** (M-07) |
| `limitacoes.md` | Itens 1–17 | Consistentes com os achados; item 15 ("sem correção para comparações múltiplas") só vale fora da bateria |
| `code_review_report.md` | "Pickup das extras: intervalo vale só com filtro `e_km` não nulo" | **Não reverificado** (fora do escopo executado) |

---

## 7. Novos problemas descobertos

C-02(b,c), M-01 (execução 25–27% em A, teletransporte, cortes 20h/24h), M-02 (cobertura 25%, argumento de equilíbrio), M-03 (quantificação 7 vs 6), M-07(iii,iv), M-08 (reinterpretação por faixa), T-3 (ganho planejado vs realizado), dose-resposta entre algoritmos, m-02, m-03, m-07, poder (MDE).

---

## 8. Testes e análises realizados

- **T-1** Recomputação independente de H1 (§3).
- **T-2** Eficiência/eficácia do despacho de reposicionamento: reposicionamento/corrida 0,306 e 0,255 km vs queda de busca 0,045 e 0,051 km/corrida (diferença líquida +0,261 e +0,204).
- **T-3** *Ganho planejado vs simulado* (regime B, 04–11h):

| Cenário | Mês | Planejado/dia | Realizado/dia | Razão | Spearman diário (p) |
|---|---|---:|---:|---:|---|
| guloso α=0,05 | mar | 30,28 | 0,50 | 0,017 | −0,07 (0,78) |
| guloso α=0,05 | set | 13,16 | 1,80 | 0,137 | −0,17 (0,55) |
| guloso α=0,2 | mar | 25,54 | 0,50 | 0,020 | −0,03 (0,90) |
| guloso α=0,2 | set | 10,01 | 1,60 | 0,160 | +0,15 (0,59) |
| guloso α=0,5 | mar | 14,76 | 0,25 | 0,017 | +0,27 (0,32) |
| guloso α=0,5 | set | 4,21 | 0,67 | 0,158 | +0,59 (0,02) |

- **T-4** Previsão: ver C-02. 
- **T-5** MDE e ponto de equilíbrio do KM de busca (M-02, §5-B).
- **T-6** pytest (§3).
- **T-7** Diff de `sim.py` (§3).

Nada disso é validação científica do simulador. Testes unitários verificam código, não o modelo.

---

## 9. O que não pôde ser verificado

1. Reexecução do `final-run` (portão `TCC_REAL_DATA_AUTHORIZED`; decisão sua, não minha).
2. Silver/Gold, deduplicação, outliers, identificadores, integridade de chaves nos extratos brutos (só agregados).
3. Equivalência Databricks ↔ local (sem logs; o próprio artigo diz isso).
4. Fidelidade da pseudonimização e risco de reidentificação.
5. A tabela de pickup das extras e a decomposição `e = e_B + e_R` (arquivos `resultados/pickup/*`, não recalculados).
6. As 5 sementes extras e a "reexecução com sementes novas" (`scripts/reexecucao_sementes.py`), apenas descritas.
7. Referências bibliográficas e literatura (não verifiquei fontes; os relatórios anteriores também dizem que não leram o texto integral).
8. Cobertura nominal do IC de razão de somas por simulação.
9. O replay exploratório anterior (arquivos inexistentes).
10. As skills DAAF e Absolutely Skilled (indisponíveis).

---

## 10. Experimentos adicionais recomendados

| # | Experimento | O que resolve | Esforço | Observação |
|---|---|---|---|---|
| E1 | **Oráculo de demanda**: usar a demanda real de D+1 por zona-hora no lugar de `fc.predict`, regime B | C-02: limite superior da alocação preventiva sob este simulador. Se nem o oráculo reduz o KM/corrida, o nulo deixa de ser "previsão ruim" | Baixo (1 função) | Requer o portão de dados |
| E2 | **Controle positivo (efeito injetado)**: criar um dia sintético com déficit espacial conhecido e provar que o protocolo detecta a melhoria | "Contribuição metodológica" hoje sem prova de detectabilidade | Médio | Pode ser todo sintético, sem dados reais |
| E3 | **Placebo de movimentos aleatórios** com a mesma distribuição de distâncias e quantidade do guloso | Dizer se o guloso é pior ou equivalente a mover ao acaso: mede a informação do plano | Baixo | |
| E4 | **Baseline com deriva dos livres** (pré-registrada) e KM de retorno | M-04: o nulo vale contra um baseline que alguém executa? | Médio | Memória do projeto já aponta esse como próximo passo possível |
| E5 | **Calibrar também a distância** (3 momentos: aceite, tempo, km de busca) | M-02 | Médio | |
| E6 | **Recuperabilidade da demanda**: aceite com probabilidade p < 1 para pedidos que o baseline perdeu | M-08 e `e` | Baixo | |
| E7 | **Resolução H3 r6/r7/r8 e alvo sem zona** | m-08 e o desencontro raio × zona | Médio | |
| E8 | **Terceiro mês** (jan, fev, jul ou ago) | Generalização | Alto | |
| E9 | **Curva de poder** por reamostragem de dias | Dar ao leitor o MDE de cada algoritmo | Baixo | Só agregados |

---

## 11. Plano de correção (impacto científico ÷ esforço)

| Ordem | Ação | Mexe em | Impacto | Esforço |
|---:|---|---|---|---|
| 1 | Reescrever no resumo/abstract e nas considerações: "troca de km por atendimento" → "no simulador, o KM vazio por corrida aumentou; corridas extras foram pequenas e dependentes do mês" | `00-resumo.tex` l.21-22, `05` l.50-52 | **Muito alto** (C-01) | Muito baixo |
| 2 | Substituir "13 algoritmos" por "7 configurações com intervenção relevante + 6 que quase não moveram veículos"; incluir a tabela de fração de motoristas movidos | resumo, `05`, quadro da bateria | Alto (M-03) | Baixo |
| 3 | Trocar "pré-registrado" por "protocolo registrado no Git antes do teste; critério de H1/H2 por IC e regime B definidos após a primeira execução; bateria posterior ao `final-run`" e mencionar o replay exploratório | resumo, `01`, `03` | Alto (M-07) | Muito baixo |
| 4 | Remover os máximos "até 45% / 80%" do resumo; manter a faixa conservadora (IC) ou omitir | resumo | Alto (M-06) | Muito baixo |
| 5 | Trocar "os dados são reais; só o simulador é simulação" | `04:8`, `05:6-7` | Médio | Muito baixo |
| 6 | Acrescentar o argumento de ordem de grandeza (busca precisaria cair ≥ 9,8%; cai 1,7–2,0%) e a comparação ganho planejado × realizado | `04` | Alto: dá base quantitativa ao nulo | Baixo |
| 7 | Declarar o MDE (≈ 3%) e a diferença entre ausência de poder (6 algoritmos) e evidência contrária (7) | `03`, `04` | Alto | Baixo |
| 8 | **E1 (oráculo de demanda)** e **E3 (placebo)** | experimentos | **Muito alto** | Baixo a médio |
| 9 | **E2 (controle positivo)** | experimentos | Alto para a "contribuição metodológica" | Médio |
| 10 | **E4, E5, E6** | experimentos | Médio | Médio |
| 11 | Reprodutibilidade: declarar `scipy`, remover o run-id fixo de `algoritmos/cli.py:21`, script mestre, centralizar a semente | repositório | Médio | Baixo |
| 12 | Para trabalhos futuros: carimbo externo do protocolo (tag assinada ou OSF/Zenodo) | processo | Médio | Muito baixo |

---

## 12. Notas (0 a 10)

| Dimensão | Nota | Justificativa |
|---|---:|---|
| **Qualidade dos dados** | **7,0** | Contagens reconciliam, tempos 100% ordenados, universo e exclusões declarados; perde por `dT_REGISTRO` não homologado, estado inferido, fotos a cada 10 min, campo de distância cobrindo 25% das aceitas, caixa retangular. *Sem auditoria dos extratos brutos.* |
| **Metodologia** | **6,5** | Corte temporal D+1 sem vazamento (exceto o declarado em B), calibração/teste cronológicos, comparações pareadas por assinatura. Perde por: regime principal fora do D+1 estrito, baseline estático, previsão sem informação, sem oráculo |
| **Estatística** | **7,5** | H1 reproduzida e robusta (blocos, LOO, poder); Holm e Bonferroni corretos. Perde por: sem declaração de poder, famílias de testes indefinidas, `e` com denominador minúsculo e máximos no resumo |
| **Simulação** | **5,0** | Código claro, determinístico, bem testado, sensibilidade ampla. Perde por: pickup 26% abaixo do observado sem calibração de distância, calibração com superfície plana, aceite certo, teleporte, baseline estático |
| **Algoritmos** | **6,0** | Bateria ampla (8 famílias), protocolo comum, pseudodias sem D+1. Perde por: metade da bateria quase sem mover, objetivo-proxy com razão 0,017–0,16 ao realizado, ações e orçamentos desiguais |
| **Experimentação** | **6,5** | Escada A/B/C, 19 sensibilidades, janelas e meses; perde por: dias de teste consultados muitas vezes, sem controle positivo nem placebo, sem terceiro período |
| **Reprodutibilidade** | **7,5** | Comando único, hashes, proveniência no resultado, checagem independente, 179 testes; perde por: `scipy` não declarada, caminho fixo, Windows-only, ausência de carimbo externo e de reexecução auditada por mim |

---

## 13. Dez perguntas difíceis para a banca

1. **WAPE de 0,9 a 1,0 é o erro de prever zero.** Em que sentido o plano "usa a demanda prevista"? Qual seria o resultado com a demanda real de D+1?
2. O guloso planeja 25,5 corridas extras por dia e o simulador entrega 0,5, sem correlação diária. O que isso diz sobre o objetivo `V(x)`? Por que otimizar um proxy que não prevê o avaliador?
3. O regime B usa a lista real de motoristas de D+1 e executa o movimento sem custo de tempo. Isso é "D+1"? O que acontece no regime A, que é D+1 estrito, e por que ele só executa 27% dos movimentos?
4. O pickup simulado é 2,65 km e o observado, 3,58 km. Qual o erro do KM vazio *nível* e por que o *delta* seria confiável?
5. Seis dos treze algoritmos moveram menos de 3% da frota. Que conclusão sobre H1 é possível a partir deles?
6. O senhor/a senhora diz "a alocação preventiva funcionou como troca". Em março o IC das corridas é [−0,37; +1,20]% e 11 de 16 dias não tiveram corrida extra. Qual é a "troca"?
7. O baseline mantém os livres parados, mas os dados mostram que eles se movem. O resultado se mantém contra um baseline que retorna a pontos de espera?
8. "Pré-registrado": o critério por IC foi definido depois da execução, o regime B foi corrigido depois de ver o teste e houve um replay exploratório com efeitos maiores. O que, exatamente, foi registrado antes? Com que carimbo externo?
9. Os parâmetros do guloso foram escolhidos por "corridas por km extra", e não pelo critério da hipótese. Isso não seria um teste injusto de H1?
10. Se H3 r7 tem aresta de cerca de 1,2 km, o salto máximo é de 3 km e o raio de despacho é de 4 km, o que um deslocamento de 3 km pode mudar na probabilidade de atender um pedido?

---

## 14. Conclusão: evidências suficientes?

**No contexto de um TCC de graduação: sim, para a conclusão delimitada.**

O trabalho evidencia, com reprodução independente, bootstrap em blocos, leave-one-out, 19 sensibilidades e poder explícito, que **neste simulador, com esta previsão e estes planejadores, reposicionar veículos livres na véspera aumentou o KM vazio por corrida, e nenhum dos algoritmos que de fato moveram frota o reduziu, em março e em setembro de 2026**. Isso responde à pergunta de pesquisa nos termos em que ela foi testada, a metodologia é transparente, as limitações centrais estão no texto e o resultado negativo é tratado com honestidade. A execução está acima da média de TCCs de Computação.

**O que o trabalho não sustenta, e deve ser reescrito ou testado antes da defesa:**
1. a conclusão geral de que a alocação preventiva "troca km por atendimento" (C-01);
2. qualquer afirmação sobre o conceito de alocação preventiva em si, sem o oráculo de demanda e sem o placebo (C-02);
3. os máximos entre 13 cenários na grade hipotética (M-06);
4. as palavras "pré-registrado" e "calibrado" como selo (M-05, M-07).

**Limitações que impediriam uma publicação científica mais exigente:**
- baseline estático e sem retorno, sem validação do simulador contra um contrafactual real nem contra a distância de busca observada (M-02, M-04);
- previsão sem informação espacial e objetivo-proxy que não prevê o avaliador (C-02);
- regime principal fora do D+1 estrito, adesão total sem custo (M-01);
- dois meses, uma empresa, uma região, janela de 7h; reuso do conjunto de teste e processo de pré-registro interno (M-07);
- sem controle positivo que mostre que o protocolo detecta um efeito real (E2);
- contribuição "metodológica" não demonstrada fora desse caso;
- reprodução por terceiros impossível (dados confidenciais), com dependências não declaradas.

Em resumo: **o resultado nulo é confiável; a interpretação do que ele significa é o que precisa ser contida.**
