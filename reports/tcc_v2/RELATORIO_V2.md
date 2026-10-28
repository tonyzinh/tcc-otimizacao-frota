# Relatório da extensão v2 (28/10/2026)

Branch `v2-extensoes`; v1 congelada na tag `v1-congelada` (`de3865c`). Nada em `reports/tcc_final/` foi alterado. Todo código novo está em
`src/tcc_frota/v3/`; os resultados estão em `reports/tcc_v2/`. Processamento local e somente agregados, conforme autorização do proponente (D3).

**Resumo em uma frase:** o nulo da v1 se confirma e se fortalece. Nenhum dos 10 planejadores reduz o KM vazio por corrida em nenhum cenário
(baselines B0–B4, oráculo de demanda, grade de recuperabilidade × conformidade); o que aparece é aumento. Um controle positivo sintético confirma que o simulador e a inferência registram ganho quando ele existe. O protocolo tem poder para enxergar
uma redução de ~5% do KM por corrida e um ganho de ~1–2% em corridas, então o nulo não é "falta de poder" para efeitos dessa ordem.

## (a) O que foi registrado no protocolo e quando

`docs/V2_PREREGISTRO.md`, versionado no Git, commitado antes de qualquer execução da v2.

| Commit | Data/hora | Conteúdo |
|---|---|---|
| `dc1057e` | 2026-10-28 11:30 | Pré-registro (hipóteses H1'/H2', famílias F1–F4, regras de decisão, lista de algoritmos/baselines/cenários, desvios históricos da v1) |
| `3b4b5cb` | 11:32 | Esclarecimentos operacionais E1–E6 (antes da Fase 1) |
| `4640db7` | 11:41 | Desvios D1–D4 (margem −1%, grade e\*, autorização local, m1/m2) |
| `d9cf99e`…`647f6c2` | 11:47–11:52 | D5–D9 (escada de ruído, oráculo, contabilização, interpretação de m1/m2, contagem de 10 planejadores), antes da Fase 3 |
| `747a46a` | 12:01 | D10–D11 (m2 revisada, parâmetros de B1–B4), antes da Fase 4 |

Limite honesto: o carimbo é o histórico do Git local, sem carimbo externo. D1 e D2 foram pedidos pelo proponente **depois** de ver a Fase 1 (que usou −2%);
nenhuma decisão mudou (0 reduções antes e depois).

## (b) O que mudou em relação à v1, tabela a tabela

| Tabela v1 | Equivalente v2 | O que mudou |
|---|---|---|
| tab11 (162 linhas, IC percentil iid, p de permutação) | `fase1_inferencia_linhas.csv`, `fase1_comparacao_v1_v2.csv`, `fase1_ic_variantes.csv` | IC por 8 variantes de bootstrap por dia (iid, dia da semana, circular e estacionário com blocos 2/3/7); IC de decisão = o mais largo; p bruto, Holm e Romano–Wolf por família. Pontos reproduzem a v1 (diferença máx. 0,0001 pp). IC de decisão com largura ≈ a do v1 (razão média 1,01). **0 reduções, 98 aumentos significativos, 64 inconclusivas** (F1); na família primária F1p, 17 de 18 aumentos |
| tab14 (razão `e`, IC percentil) | `fase1_nb.csv`, `fase1_nb_curva.csv`, `fase1_e_fieller.csv` | Sem razão: NB(e\*) = ΔN/dia − Δ(B+R)/dia / e\*, grade {3,5,10,20,30,50,100} e curva contínua. NB>0 com IC inteiro positivo só aparece em e\* ≥ 20 (3 linhas em 20, 9 em 30, 14 em 50, 25 em 100). Fieller: 126 de 162 intervalos **ilimitados**; `e` pontual só em 38 linhas |
| (inexistente) | `fase1_mde.csv` | MDE (80%, 5%): ΔKM/corrida ≈ 2,5–2,7% e ΔN ≈ 1,1–1,6% (janela 04–11, regime B, mediana) |
| (inexistente) | `fase1_dispersao_*.csv` | Média, desvio, mín., máx. e por dia da semana das diferenças diárias (ex.: guloso α=0,1, mar: ΔKM vazio/dia de +20 a +80 km) |
| tab15 (escada de informação) | `fase3_*` | Oráculo e escada de WAPE (seção e) |
| (inexistente) | `fase4_*` | Baselines B0–B4, ρ, conformidade, placebo (seção d) |

## (c) Taxa de falso positivo, poder e cobertura (Fase 2, semi-sintética)

Método: pseudopopulação com as diferenças diárias reais recentradas, efeito conhecido injetado, 1 000 réplicas por efeito, analisadas com o procedimento real
(`fase2_curva_poder.csv`, `fase2_falsos_positivos.csv`, `fase2_curva_poder.pdf`). Uma primeira versão tinha réplicas idênticas (taxa de 0,000 sem significado); foi corrigida antes de qualquer conclusão.

* **Falso positivo, amostragem iid** (realista: autocorrelação lag-1 das diferenças diárias ≈ 0,02): **5,3% a 8,4%** no nível de 5%, dentro da faixa definida no protocolo [2%, 9%], mas perto do limite superior (procedimento levemente liberal com 15–16 dias). Cobertura de IC 92–95%.
* **Falso positivo sob dependência serial artificial** (blocos de 3 dias): 8,6% a 15% em parte das combinações, **fora** da faixa. Está declarado como teste de estresse; não corresponde ao que os dados mostram.
* **Poder** (período, janela 04–11, IC mais largo): ΔN de 1% → 58% (mar) e 32% (set); 2% → 99% e 83%; 5% → 100%. Redução de KM/corrida de 2% → 51% e 27%; 5% → 100%. Para ΔN ≤ 0,5% o poder é ≤ 21%.
* Regra pré-definida ("poder para ΔN ≤ 2% < 50% ⇒ nulo inconclusivo"): lida no ponto 2%, o poder é ≥ 83%, logo a regra **não dispara**; para efeitos de 0,25–0,5% de ΔN o protocolo **não distingue** o plano do ruído. Essa leitura do "≤ 2%" é minha; pode ser revista.
* **Controles sintéticos (D12/D13, mundo 100% sintético, 16 dias, 10 planejadores, mesmo pipeline de inferência):** `fase2_controle_*`. **Positivo, cenário "fora do raio"** (a demanda está fora do raio de despacho da frota ociosa): o baseline atende 7 de 70 pedidos no dia de teste de fumaça e as sete variantes orientadas a demanda (proporcional, três guloso, limiar, fluxo, húngaro) sobem ΔN em +165% a +226% (IC inferior de ΔN% ≥ 123%) e NB(30) tem IC inferior de 32,1 a 43,1 corridas/dia: **o critério D13 foi atendido**, logo o simulador e a inferência registram ganho quando ele existe. Nesse mesmo cenário o KM por corrida **sobe** (+18,6% a +86,2%), a ilustração direta de por que NB(e\*) é o desfecho primário. Busca local, recozimento e PSO não se movem (Δ = 0): confirmado que avaliam e rejeitam os movimentos pelo próprio objetivo (`J_busca_vazio` < `J_busca_inicial`), não é bug. **Cenário "alcançável"** (controle neutro): ΔN = 0 e KM/corrida sobe em 4 de 10 linhas (+15% a +47%) porque o reposicionamento paga o mesmo deslocamento que o baseline pagaria na primeira coleta. **Negativos exatos:** N1 (baseline × baseline) e N2 (alvo = posição atual) dão Δ = 0 em 16 dias (`fase2_controle_nulos.csv`). **N3 (previsão sem informação) não é um nulo válido em "fora do raio"** (ΔN +94% a +153%): com 4 zonas candidatas e 12 motoristas, espalhar cobre a geografia sem informação. Registrado como falha de desenho do controle, sem reescrever o critério; no mundo real o papel de nulo fica com o placebo da Fase 4.
* **Ainda não feito:** controle negativo com muitas zonas ou movimentos embaralhados entre dias em dados reais.

## (d) Resultado contra cada baseline (Fase 4)

Contabilização primária ("origem": os dois braços começam na última posição de D). ρ = 1, conformidade = 1, 10 planejadores, 100 linhas por contabilização (F4).

| Baseline | ΔKM vazio/corrida, mediana entre planejadores (mar / set) | Faixa (mín.–máx.) | ΔN mediano |
|---|---|---|---|
| B0 estacionário | +4,9% / +4,9% | 0,3 a 36,5% | +0,1% |
| B1 retorno à origem | +1,7% / +1,2% | 0,0 a 8,7% | +0,2% |
| B2 movimento observado | +2,5% / +1,6% | 0,1 a 15,5% | +0,0% |
| B3 cruzeiro local 2×2 km | +1,0% / +0,2% | −0,4 a 5,0% | +0,1% |
| B4 reativo | +4,6% / +4,3% | 0,3 a 32,5% | +0,1% |

* **Decisões (F4, p-RW):** 0 reduções, 56 aumentos, 44 inconclusivas. Em KM absoluto, o plano soma ~12–16 km/dia a mais em mediana contra qualquer baseline.
* O aumento relativo encolhe com B1/B3 porque o baseline realista gasta muito KM de deriva (B1 ≈ 875 e B3 ≈ 1 700 km/dia num dia de teste), que infla o denominador; o KM absoluto adicional do plano não diminui.
* **Placebo** (mesma quantidade de movimentos, motoristas e alvos aleatórios a ≤ salto máximo da origem): mediana de ΔKM/corrida +4,1% (mar, B0), próxima à dos planos (+4,9%). Plano contra placebo: 5 reduções (todas do `proporcional`, que move menos/mais perto, ou seja, custo menor, não informação de demanda), 10 aumentos, 85 inconclusivas.
* **B4 como candidato** (sem plano) contra B0: ΔKM/corrida +8,2% (mar) e +12,6% (set) com ΔN ≈ 0: não reduz. Contra B1–B3, o KM cai 41 a 85%, mas com **perda de 4 a 8% das corridas**; isso é o custo de substituir uma deriva que também atende melhor, e não um ganho sem perda de serviço.
* **Contabilizações alternativas (as três são reportadas; nenhuma é "o resultado"):** (i) v1 bruta: 0 reduções, 49 aumentos; (ii) "pagar nos dois braços": **24 reduções**, mas o placebo aleatório também gera 18 de 100 "reduções" nessa contabilização, portanto é artefato (seção f, D10).
* **Grade ρ × conformidade** (`fase4_grade_rho_conformidade*.csv`, `fase4_mapa_calor_rho_conformidade.pdf`; descritiva, sem p-valores): com e\* = 30, a fração de pares (planejador, baseline) com NB>0 e IC inteiro positivo é 0–2% em todas as 12 células. **Não há região do espaço de parâmetros em que o reposicionamento compense** com e\* ≤ 30; só com e\* = 50–100 aparecem alguns NB>0 (F4: 2 e 5 de 100 linhas).
* **Literatura (53–82% menos deadheading com informação de demanda futura e estacionamento de curto prazo ilimitado):** B1/B2 se afastam dessa premissa (o motorista continua despachável e paga o KM de deriva) e a v1/v3 não oferece estacionamento ilimitado. Não afirmo a causa da diferença; isso exigiria teste (por exemplo, um baseline que contabilize só o KM com passageiro e estacione sem custo).

## (e) Resultado com oráculo (Fase 3; regime O, viola o corte D+1, limite superior)

* WAPE do modelo real nos dias de teste: 0,902 (mar) e 0,862 (set); demanda real fora das zonas conhecidas: 0,03% e 0%.
* **Oráculo, contabilização v1 (primária):** 0 reduções, **20 aumentos em 20** (ΔKM/corrida de +1,5% a +34,7%). O oráculo só melhora ΔN, até +3,7% (regra de limiar, set).
* Oráculo contra a previsão (mesmo algoritmo): 0 reduções, 6 aumentos, resto inconclusivo; a informação perfeita de demanda **não** reduz o KM por corrida.
* **Escada de ruído** (WAPE 0,1; 0,3; 0,5; 0,7; 0,9): 63 de 63 linhas com aumento; o sinal não inverte em nenhum nível. Mesmo com WAPE 0,1, ΔKM/corrida vai de +1,6% (guloso α=0,5, set) a +35,3% (limiar, set). Resposta à pergunta "que acurácia seria necessária": nesta configuração, nenhuma, porque o custo do deslocamento supera o ganho de atendimento em todos os níveis.
* NB(e\*) do oráculo: positivo com IC inteiro >0 em 0/20 linhas para e\* ≤ 20, 1 para e\* = 30, 5 para 50 e 8 para 100.
* A contabilização "pagar nos dois" nesta fase traz reduções (9 de 20) que são o mesmo artefato; use só como sensibilidade.
* **Não feito:** previsor melhorado (LightGBM/binomial negativa) e comparação H3 res. 7 × 8 (opcionais).

## (f) Desvios do protocolo registrado e achados de método

D1–D11 estão em `docs/V2_PREREGISTRO.md` §12. Os que afetam leitura:
* **D1/D2** (margem −1%, grade e\* com 3 e 30 e curva contínua), pedidos pelo proponente após a Fase 1.
* **D9**: eram 10 planejadores, não 9 (F3 = 20, F4 = 100).
* **D10 (m2):** a primeira operacionalização ("pagar o trecho noturno nos dois braços") produzia economia espúria: o placebo de movimentos aleatórios deu ΔKM = −21 a −31 km/dia nela, contra +36 a +39 na v1. Passou-se a `start_at_origin` (os dois braços começam na última posição de D, premissa do regime B). **A interpretação de m1/m2 é minha** a partir da descrição do proponente (`docs/V2_CONTABILIZACAO.md`) e pode ser corrigida. m1 (reposicionamento que passa do fim da sessão) só atua no modo `inicio_turno` (regime A); o regime B, usado em tudo, não é afetado.
* **D12/D13 (controle sintético):** D12 definiu o desenho antes de rodar; D13 corrigiu o critério (KM/corrida no cenário "alcançável" era inatingível por construção; o critério positivo passou a ser ΔN e NB(30) em "fora do raio") depois de um teste de fumaça de um dia, antes da execução completa.
* **Erros meus corrigidos durante o trabalho:** (1) duas execuções simultâneas da Fase 3 por um `nohup` que não encerrou (a segunda foi morta; resultados da primeira); (2) o controle nulo inicial da Fase 2 tinha réplicas idênticas; (3) `average_seeds` misturava baselines de ρ/Bk diferentes (teste adicionado); (4) o pareamento plano × placebo colapsava os 5 baselines (corrigido antes dos números aqui). Os resultados reportados são os pós-correção.
* Fase 3 rodou antes da revisão D10; seu campo `empty_km_sim` é "pagar nos dois" (sensibilidade). A comparação primária da Fase 3 usa o `empty_km` da v1.
* A autorização de dados (D3) foi usada só localmente; nenhum bruto, ID ou coordenada individual foi impresso ou versionado (`reports/runs/` é ignorado; os CSV versionados são agregados por dia ou mais).

## (g) Sugestões de reescrita (não aplicadas)

* **Resumo/conclusão:** trocar "o nulo da v1" por "nenhum dos 10 planejadores reduz o KM vazio por corrida; a evidência é de aumento (98/162 linhas, Romano–Wolf), e o resultado persiste sob oráculo de demanda e sob baselines com deriva realista".
* Substituir "razão `e` com IC" por NB(e\*) e dizer que o IC de `e` é frequentemente ilimitado (126/162).
* Dizer que o protocolo detecta redução de ~5% no KM/corrida e ganho de ~1–2% em corridas com poder ≥ 80%, mas não efeitos de 0,25–0,5% (ΔN).
* Remover "13 algoritmos" e "pré-registrado" no sentido forte (ver D1/D2: parte do critério foi definida depois), usar "protocolo registrado no Git antes da execução da v2".
* Explicitar que a "economia" que aparece quando o baseline paga o trecho noturno só nos moves é artefato, não resultado.

## (h) O que ficou por fazer

* **Fase 5 (distâncias viárias):** não feita. Exige baixar o OSM do Espírito Santo (rede fora de pip/npm), o que pede sua autorização. Mantém-se Haversine × fator; lacuna M4 segue aberta.
* **Fase 6 (terceiro período):** não feita. Os lotes disponíveis são `mar2026`, `set2026` e as janelas de histórico (`historico56`, `historico56_set`), usadas como treino de previsão; não há um terceiro mês independente. Setembro é replicação parcial, não independente.
* Fase 2: controle negativo com muitas zonas e movimentos embaralhados em dados reais (ver (c)); o controle positivo foi feito.
* Fase 3 opcional (previsor melhorado, H3 7 × 8).
* Planejadores não conhecem o baseline Bk (limitação); o B4 usa parâmetros fixos (5 min, 15 min, 3 km) sem varredura.
* Reescrita das tabelas do artigo: gerados `reports/tcc_v2/tex/*.tex` e `numeros_v2.tex`; a integração ao artigo é manual.

## Testes

`python -m pytest`: **256 passed, 1 skipped** (linha de base antes da v2: 179 passed, 1 skipped; 77 testes novos, incluindo regressão bit a bit do `simulate3` contra a v1).
