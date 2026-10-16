# Bateria de algoritmos de reposicionamento D+1

**16/10/2026.** Protocolo pré-registrado em [ORCAMENTO_CONFIGURACOES.md](ORCAMENTO_CONFIGURACOES.md) (commit `d321f4d`, anterior a qualquer resultado); auditoria em [AUDITORIA_BATERIA.md](AUDITORIA_BATERIA.md). Finalistas congelados em `9778c7f`, antes de qualquer dia de teste. Todos os números vêm de execuções registradas em `resultados/` (CSV por dia e semente, registro de configurações e sementes 11, 23, 37, 41, 53). São **estimativas de simulação** (Haversine × fator rua/reta calibrado, baseline simulado), não KM rodado nem economia observada (DT003).

## Resumo executivo

**Nenhum algoritmo passou nos 5 critérios. Nenhum reduziu o KM vazio total por corrida em março nem em setembro.** Foram 13 algoritmos na tabela principal: 8 famílias novas (fluxo de custo mínimo, húngaro, MILP min(B+R) com piso, LNS, recozimento simulado, NSGA-II, MILP robusto por cenários e PSO) e as 5 referências do artigo. Em regime B, janela 04–11h, todas as estimativas pontuais da variação do KM vazio por corrida ficaram em zero ou acima (+0,01% a +35,8%), e nenhum IC 95% ficou abaixo de zero. Não houve sequer um "indício": nenhum algoritmo passa no critério 1 sem correção. Todos passam na não inferioridade de atendimento (critério 2). As famílias que avaliam planos no simulador (LNS, recozimento, PSO e NSGA-II) convergem para "não mover": na calibração, os pseudodias históricos de aceitação escolheram o plano vazio em 76% a 94% dos planos (conforme a configuração), e o NSGA-II não achou nenhuma configuração abaixo do baseline. Os dois experimentos fora do escopo D+1 também não mudam o quadro. O MPC intradiário só não piora quando quase não move. O despacho em lote D+0 reduz o KM vazio por corrida (−3,9% em março, −2,8% em setembro), mas **perde corridas** (−2,4% em março, IC [−3,9; −1,1]): é redução por negar serviço, não melhoria. O resultado repete e reforça o do artigo (H1 rejeitada), agora com otimizadores exatos, metaheurísticas e busca multiobjetivo.

## Tabela comparativa final (teste, regime B, 04–11h)

Variação contra o baseline sem reposicionamento; IC 95% por bootstrap pareado de dias (2.000 reamostragens). Baseline: 2,648 km vazios por corrida em março (16 dias) e 2,596 em setembro (15 dias). p de Holm sobre os 13 algoritmos de cada mês. Fonte: `resultados/tabela_final_criterios.csv`, `finalistas_marco.csv` e `finalistas_setembro.csv`.

| Algoritmo | Corridas mar (%) | Corridas set (%) | KM vazio/corrida mar (%) | KM vazio/corrida set (%) | Dias com redução (mar; set) | C1 | C2 | C3 | C4 | C5 | Aprovado |
|---|---:|---:|---:|---:|:---:|:-:|:-:|:-:|:-:|:-:|:-:|
| Proporcional (artigo) | +1,09 [+0,30; +2,10] | +1,97 [+0,39; +4,31] | +8,15 [+6,44; +10,11] | +9,81 [+7,76; +11,77] | 1/16; 0/15 | não | sim | não | não | sim | não |
| Guloso α = 0,05 (artigo) | +0,40 [−0,46; +1,34] | +2,32 [+0,94; +3,93] | +16,77 [+14,92; +18,99] | +17,80 [+15,01; +20,78] | 0/16; 0/15 | não | sim | não | não | sim | não |
| Guloso α = 0,2 (artigo) | +0,40 [−0,37; +1,20] | +2,06 [+1,21; +3,10] | +9,88 [+8,36; +11,48] | +7,83 [+5,85; +9,66] | 0/16; 1/15 | não | sim | não | não | sim | não |
| Guloso α = 0,5 (artigo) | +0,20 [+0,00; +0,46] | +0,86 [+0,34; +1,39] | +3,59 [+2,72; +4,35] | +2,57 [+1,65; +3,51] | 0/16; 1/15 | não | sim | não | não | sim | não |
| Regra de limiar (artigo) | +1,09 [+0,36; +1,87] | +2,92 [+1,76; +4,10] | +28,55 [+24,75; +33,44] | +35,75 [+31,00; +42,40] | 0/16; 0/15 | não | sim | não | não | sim | não |
| 5.1 Fluxo de custo mínimo | −0,25 [−0,71; +0,10] | +1,03 [+0,23; +2,15] | +2,59 [+1,88; +3,49] | +4,16 [+2,80; +5,63] | 0/16; 0/15 | não | sim | não | não | sim | não |
| 5.2 Húngaro | −0,10 [−0,51; +0,38] | +0,94 [+0,00; +2,14] | +4,00 [+2,90; +5,18] | +6,04 [+4,47; +7,54] | 0/16; 0/15 | não | sim | não | não | sim | não |
| 5.3 MILP min(B+R) | +0,00 [+0,00; +0,00] | +0,00 [+0,00; +0,00] | +0,02 [+0,00; +0,07] | +0,08 [+0,00; +0,24] | 0/16; 0/15 | não | sim | não | não | sim | não |
| 5.4 LNS | +0,15 [+0,00; +0,34] | +0,10 [−0,03; +0,30] | +0,43 [+0,20; +0,69] | +0,58 [+0,12; +1,23] | 0/16; 0/15 | não | sim | não | não | sim | não |
| 5.5 Recozimento simulado | +0,21 [+0,00; +0,51] | +0,19 [+0,00; +0,45] | +1,27 [+0,26; +3,04] | +0,41 [+0,13; +0,72] | 1/16; 0/15 | não | sim | não | não | sim | não |
| 5.6 NSGA-II | +0,00 [+0,00; +0,00] | +0,00 [+0,00; +0,00] | +0,01 [+0,00; +0,03] | +0,01 [−0,00; +0,02] | 0/16; 0/15 | não | sim | não | não | sim | não |
| 5.7 Robusto por cenários | +0,00 [+0,00; +0,00] | +0,00 [+0,00; +0,00] | +0,01 [+0,00; +0,04] | +0,02 [+0,00; +0,05] | 0/16; 0/15 | não | sim | não | não | sim | não |
| 5.8 PSO | +0,23 [+0,03; +0,55] | +0,29 [+0,05; +0,63] | +1,31 [+0,28; +3,02] | +0,38 [+0,10; +0,70] | 1/16; 2/15 | não | sim | não | não | sim | não |

C1: KM vazio por corrida com IC abaixo de zero nos dois meses (com Holm para "confirmado"). C2: limite inferior do IC das corridas ≥ −1%. C3: redução medida no simulador. C4: ≥ 50% dos dias com redução e regime A sem aumento. C5: plano ≤ 900 s/dia em média (o mais lento, PSO, levou 29 s). Decomposição B/R por corrida, KM vazio por corrida extra (*e*), fração não incremental de equilíbrio (*f*\*), fração de motoristas movidos, km por movimento, tempo até o passageiro e regime A estão em `resultados/tabela_final_criterios.csv`; B + R = total conferido em todas as linhas. Regime A (robustez): todas as variações ficaram entre −0,00% e +12,4%, sem redução (`finalistas_*.csv`). LaTeX gerado em `tabelas/tab_bateria_principal.tex` e `tabelas/tab_bateria_criterios.tex`.

## Experimentos fora da tabela principal

| Mês | Experimento | Corridas (%) | KM vazio/corrida (%) |
|---|---|---:|---:|
| mar | Cenário intradiário (5.9, MPC α = 0,5, H = 1 h) | +0,00 [+0,00; +0,00] | +0,00 [+0,00; +0,00] |
| mar | D+0 (5.11, lote de 30 s, raio calibrado) | **−2,44 [−3,90; −1,10]** | −3,92 [−5,95; −1,44] |
| mar | D+1 + D+0 (5.7 + 5.11) | **−2,44 [−3,90; −1,10]** | −3,90 [−5,95; −1,41] |
| set | Cenário intradiário (5.9) | +0,00 [+0,00; +0,00] | +0,00 [+0,00; +0,00] |
| set | D+0 (5.11) | −1,97 [−4,82; +0,80] | −2,83 [−4,72; −1,04] |
| set | D+1 + D+0 | −1,97 [−4,82; +0,80] | −2,83 [−4,72; −1,04] |

O despacho em lote reduz o KM vazio por corrida porque atende menos: na calibração, todas as 4 configurações perderam de 3,1% a 15,3% das corridas, e nenhuma respeitou o piso de −1%. Isso não é melhoria. O MPC escolhido (o único sem piora na calibração) faz 1 movimento em 14 dias; os mais agressivos chegaram a +13% de KM vazio por corrida. A combinação usou o finalista 5.7 (regra fixada antes do teste: menor KM vazio por corrida na calibração entre os que movem), que quase não move; por isso ela coincide com o despacho isolado. `tabelas/tab_bateria_extras.tex`.

## Por que nenhum algoritmo venceu

1. **Desigualdade triangular.** Deslocar um motorista e depois buscar o passageiro nunca percorre menos do que buscar direto. O reposicionamento só reduz o total quando muda quem é atendido, e cada corrida extra precisa custar menos KM vazio que a busca média (2,6 km por corrida). Nas referências, cada corrida extra custou de 10 a 115 km vazios.
2. **O modelo promete o que o simulador não entrega.** O MILP com cap ≥ 1,5 moveu de 547 a 800 motoristas na calibração e aumentou o KM vazio por corrida em 24–30%: o modelo estático supõe que cada veículo atende `cap` corridas da nova posição. Com cap = 1 (hipótese da primeira corrida), o modelo não vê ganho e não move. A hipótese não produziu redução.
3. **Quando o objetivo é medido no simulador, a melhor decisão é quase não mover.** LNS, recozimento e PSO acharam melhorias nos pseudodias de busca que não se sustentaram nos pseudodias de aceitação (plano vazio escolhido em 56 a 66 de 70 planos por configuração do LNS, 236 de 280 no recozimento e 212 de 280 no PSO). Nas 1.500 avaliações do NSGA-II, nenhuma configuração ficou abaixo do baseline. Os pequenos aumentos no teste (+0,4% a +1,3%) vêm de planos aceitos que não se repetiram no dia real.
4. **Fluxo e húngaro diferem mais do que o esperado** (+2,6% contra +4,0% em março): o húngaro preenche todas as vagas alcançáveis medindo do motorista até a vaga, e o fluxo descarta unidades cujo deslocamento real passa do salto. Mais vagas preenchidas significam mais reposicionamento, sem busca menor.

## Conferências feitas

- `pytest`: 162 aprovados, 1 pulado (preexistente).
- Regressão: as referências pela interface `Planner` reproduzem os números diários do `final-run 20261016T013428Z` (372 linhas, diferença máxima de 5·10⁻⁵, arredondamento do CSV), e a tabela de teste reproduz a Tabela 6 do artigo.
- Recalibração do 5.1 do zero: 12 configurações idênticas (diferença máxima de 5·10⁻⁷).
- Seleção só na calibração: `finalistas.json` foi commitado em `9778c7f`, antes de existir qualquer arquivo de teste; `run_test` recusa rodar se esse arquivo não estiver versionado e limpo.
- B + R = total em todas as linhas diárias (checagem independente: 0 divergências).
- **Segunda checagem independente:** (a) `scripts/checagem_independente.py` recalcula as razões e o bootstrap com NumPy e outro gerador, sem importar o pacote, e reproduz todas as estimativas pontuais e os IC (diferenças só de reamostragem); (b) os finalistas estocásticos reexecutados com 5 sementes novas (61, 67, 71, 73, 79; `resultados/reexecucao_sementes.csv`) dão de +0,00% a +1,95% de KM vazio por corrida, sem IC abaixo de zero.

## Limitações

- Mesmo construto do artigo: KM vazio estimado (Haversine × fator), sem retorno nem odômetro; baseline simulado, que atende 1,4–4,6 p.p. a mais que o aceite observado.
- O simulador é determinístico. As sementes só variam os algoritmos estocásticos e o sorteio de cenários; a incerteza vem dos dias (15–16 por mês).
- A simulação no laço usa pseudodias sem compromissos externos (desconhecidos no corte) e com horário previsto; o desempenho no dia real é sempre medido pelo simulador completo.
- Hiperparâmetros de calibração do simulador (raio e paciência) foram estimados com os dias 2–15 de cada mês, que incluem dias posteriores a alguns dias de calibração dos algoritmos; os dias de teste não têm esse problema.
- NSGA-II, PSO e recozimento são implementações próprias e curtas (pymoo não estava instalado), testadas em problemas conhecidos, mas sem comparação com bibliotecas.
- Uma região, dois meses, uma empresa; regime B depende de escala conhecida, ainda não confirmada.

## Não testado

- **5.10 Aprendizado por reforço profundo: não testado.** Pelo pré-registro, entraria só se sobrasse tempo, com *timebox* de 4 h. Nesta rodada, o tempo foi para as conferências da seção 7 (checagem independente, novas sementes e recalibração). Não há resultado de RL e ele não deve ser descrito como "testado sem ganho".
- Regime C (oráculo): excluído por desenho; não é limite superior.
- A pasta `referencia_exploratoria/` não existe no repositório; os números exploratórios do pedido não foram reproduzidos nem são citáveis.

## Reprodução

`scripts/bateria_algoritmos.ps1` (local). `databricks/bateria/nb_bateria_algoritmos.py` está escrito, mas **não foi executado no workspace**. Código em `src/tcc_frota/algoritmos/`; relatórios curtos por família em `resultados/calibracao/RELATORIOS.md`; fronteira de Pareto da calibração em `resultados/fronteira_pareto.csv` e `.png`.
