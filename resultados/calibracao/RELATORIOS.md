# Relatórios curtos de calibração (por família)

Gerados por `protocolo.calibration_report` a partir de `resultados/calibracao/<família>.json`. Estimativas de simulação; não são KM rodado nem economia observada.

## fluxo_custo_minimo

Código `d321f4d+alteracoes`; calibração 2–15/03, regime B, 04–11h; baseline 1760 corridas e 2.632 km vazios por corrida.

| Configuração | Corridas (%) | KM vazio/corrida (%) | B/corrida | R/corrida | Mov. exec. | Dias com redução | Piso | Tempo (s/dia) |
|---|---:|---:|---:|---:|---:|---:|:---:|---:|
| `fluxo_custo_minimo|teto|H3|s1` **(finalista)** | -0.06 | +4.11 | 2.655 | 0.086 | 78 | 0/14 | sim | 0.03 |
| `fluxo_custo_minimo|teto|H3|s1.3` | -0.06 | +4.48 | 2.655 | 0.096 | 87 | 0/14 | sim | 0.03 |
| `fluxo_custo_minimo|valor_marginal|H3|s1.3` | +0.51 | +4.51 | 2.643 | 0.108 | 99 | 0/14 | sim | 0.03 |
| `fluxo_custo_minimo|demanda|H3|s1` | +0.51 | +4.61 | 2.650 | 0.104 | 93 | 0/14 | sim | 0.03 |
| `fluxo_custo_minimo|valor_marginal|H3|s1` | +0.51 | +4.92 | 2.652 | 0.110 | 99 | 0/14 | sim | 0.03 |
| `fluxo_custo_minimo|demanda|H3|s1.3` | +0.57 | +5.28 | 2.650 | 0.121 | 111 | 0/14 | sim | 0.03 |
| `fluxo_custo_minimo|teto|H4|s1` | +0.11 | +6.27 | 2.651 | 0.146 | 111 | 0/14 | sim | 0.03 |
| `fluxo_custo_minimo|teto|H4|s1.3` | +0.28 | +7.24 | 2.660 | 0.162 | 124 | 0/14 | sim | 0.03 |
| `fluxo_custo_minimo|demanda|H4|s1` | +0.91 | +9.43 | 2.632 | 0.249 | 165 | 0/14 | sim | 0.03 |
| `fluxo_custo_minimo|valor_marginal|H4|s1` | +0.85 | +9.59 | 2.635 | 0.249 | 172 | 0/14 | sim | 0.03 |
| `fluxo_custo_minimo|valor_marginal|H4|s1.3` | +1.14 | +9.84 | 2.644 | 0.247 | 171 | 0/14 | sim | 0.03 |
| `fluxo_custo_minimo|demanda|H4|s1.3` | +0.85 | +11.40 | 2.658 | 0.275 | 183 | 0/14 | sim | 0.03 |

Nenhuma configuração reduziu o KM vazio por corrida na calibração (de +4,1% a +11,4%); em nenhum dia o finalista ficou abaixo do baseline. Saltos de 4 km movem quase o dobro de motoristas e dobram o aumento. O KM de busca por corrida do finalista também subiu (2,655 contra 2,632 km do baseline): os movimentos não encurtaram a busca. Corridas praticamente iguais (−1 corrida em 14 dias).

## hungaro

Código `53ff94f`; calibração 2–15/03, regime B, 04–11h; baseline 1760 corridas e 2.632 km vazios por corrida.

| Configuração | Corridas (%) | KM vazio/corrida (%) | B/corrida | R/corrida | Mov. exec. | Dias com redução | Piso | Tempo (s/dia) |
|---|---:|---:|---:|---:|---:|---:|:---:|---:|
| `hungaro|teto|H3|s1` **(finalista)** | +0.00 | +6.05 | 2.650 | 0.142 | 124 | 0/14 | sim | 0.02 |
| `hungaro|teto|H3|s1.3` | +0.11 | +6.26 | 2.630 | 0.167 | 145 | 0/14 | sim | 0.02 |
| `hungaro|demanda|H3|s1` | +0.85 | +7.41 | 2.623 | 0.205 | 171 | 0/14 | sim | 0.03 |
| `hungaro|valor_marginal|H3|s1` | +0.68 | +8.07 | 2.625 | 0.220 | 186 | 0/14 | sim | 0.03 |
| `hungaro|demanda|H3|s1.3` | +0.68 | +8.82 | 2.620 | 0.244 | 205 | 0/14 | sim | 0.03 |
| `hungaro|teto|H4|s1` | +0.28 | +9.21 | 2.655 | 0.219 | 156 | 0/14 | sim | 0.02 |
| `hungaro|valor_marginal|H3|s1.3` | +0.45 | +9.34 | 2.654 | 0.225 | 189 | 0/14 | sim | 0.03 |
| `hungaro|teto|H4|s1.3` | +0.51 | +10.79 | 2.652 | 0.265 | 187 | 0/14 | sim | 0.02 |
| `hungaro|demanda|H4|s1` | +1.42 | +15.83 | 2.633 | 0.415 | 273 | 0/14 | sim | 0.03 |
| `hungaro|valor_marginal|H4|s1` | +1.14 | +16.72 | 2.633 | 0.440 | 289 | 0/14 | sim | 0.03 |
| `hungaro|valor_marginal|H4|s1.3` | +0.74 | +17.57 | 2.655 | 0.439 | 288 | 0/14 | sim | 0.03 |
| `hungaro|demanda|H4|s1.3` | +1.02 | +18.07 | 2.638 | 0.470 | 311 | 0/14 | sim | 0.03 |

Mesma escolha de configuração que 5.1 (alvo com teto 2, H = 3 km, share 1,0), mas com mais movimentos executados (124 contra 78) e KM vazio por corrida maior (+6,05% contra +4,11%). A diferença para 5.1 não é pequena e tem causa identificável: 5.1 decide o fluxo entre centróides e descarta, na conversão para motoristas, unidades cujo deslocamento real passa de H; o húngaro mede do motorista até a vaga e preenche todas as vagas alcançáveis. Preencher mais vagas aumenta o reposicionamento sem reduzir a busca (2,650 contra 2,632 km por corrida do baseline). Corridas iguais ao baseline; nenhum dia com redução.

## milp

Código `6d8552b`; calibração 2–15/03, regime B, 04–11h; baseline 1760 corridas e 2.632 km vazios por corrida.

| Configuração | Corridas (%) | KM vazio/corrida (%) | B/corrida | R/corrida | Mov. exec. | Dias com redução | Piso | Tempo (s/dia) |
|---|---:|---:|---:|---:|---:|---:|:---:|---:|
| `milp|cap1|b0.99|mu0.5` **(finalista)** | +0.00 | +0.00 | 2.632 | 0.000 | 0 | 0/14 | sim | 0.09 |
| `milp|cap1|b1|mu0.5` | +0.00 | +0.12 | 2.632 | 0.003 | 2 | 0/14 | sim | 0.11 |
| `milp|cap1|b1|mu0` | +0.00 | +2.32 | 2.629 | 0.065 | 52 | 0/14 | sim | 0.11 |
| `milp|cap1|b0.99|mu0` | +0.17 | +2.48 | 2.635 | 0.062 | 52 | 0/14 | sim | 0.09 |
| `milp|cap1.5|b0.99|mu0.5` | +2.22 | +23.81 | 2.591 | 0.668 | 547 | 0/14 | sim | 7.48 |
| `milp|cap1.5|b1|mu0.5` | +2.05 | +24.69 | 2.599 | 0.683 | 556 | 0/14 | sim | 8.05 |
| `milp|cap1.5|b0.99|mu0` | +2.50 | +27.15 | 2.562 | 0.785 | 792 | 0/14 | sim | 9.56 |
| `milp|cap1.5|b1|mu0` | +2.61 | +28.24 | 2.575 | 0.801 | 800 | 0/14 | sim | 11.31 |
| `milp|cap3|b0.99|mu0.5` | +2.90 | +29.80 | 2.618 | 0.799 | 614 | 0/14 | sim | 19.04 |
| `milp|cap3|b0.99|mu0` | +2.56 | +29.82 | 2.598 | 0.819 | 646 | 0/14 | sim | 16.97 |
| `milp|cap3|b1|mu0.5` | +3.01 | +29.89 | 2.607 | 0.812 | 617 | 0/14 | sim | 18.83 |
| `milp|cap3|b1|mu0` | +2.78 | +30.28 | 2.606 | 0.823 | 646 | 0/14 | sim | 19.34 |

Solver: 139 de 168 instâncias com ótimo provado; 29 pararam no limite de 30 s (6 com cap 1,5 e 23 com cap 3), com gap máximo de 0,24%. Com cap = 1 (hipótese da primeira corrida) e penalidade de 0,5 km por movimento, o modelo não move ninguém em nenhum dia: pela desigualdade triangular, mover um veículo que atende uma única corrida não encurta a busca no modelo. Por isso o finalista pela regra pré-registrada é um plano vazio (igual ao baseline, 0,00%); no teste ele não pode passar no critério 1. Sem penalidade, cap = 1 move 52 vezes em 14 dias e aumenta o KM vazio por corrida em 2,3–2,5%. Com cap = 1,5 ou 3 o modelo move de 547 a 800 vezes, ganha 2,0–3,0% de corridas e aumenta o KM vazio por corrida em 24–30%: o modelo estático supõe que cada veículo atende cap corridas da nova posição, o que o simulador não confirma. A hipótese da primeira corrida (cap ≈ 1–1,5) não produziu redução.

## busca_local

Código `2389841+alteracoes`; calibração 2–15/03, regime B, 04–11h; baseline 1760 corridas e 2.632 km vazios por corrida.

| Configuração | Corridas (%) | KM vazio/corrida (%) | B/corrida | R/corrida | Mov. exec. | Dias com redução | Piso | Tempo (s/dia) |
|---|---:|---:|---:|---:|---:|---:|:---:|---:|
| `lns|fluxo|E100|k2` **(finalista)** | +0.00 | +0.17 | 2.632 | 0.004 | 3 | 0/14 | sim | 8.56 |
| `lns|fluxo|E300|k2` | +0.06 | +0.23 | 2.634 | 0.004 | 3 | 0/14 | sim | 19.79 |
| `lns|guloso|E100|k2` | +0.00 | +0.51 | 2.636 | 0.010 | 8 | 0/14 | sim | 10.82 |
| `lns|fluxo|E100|k4` | +0.06 | +0.55 | 2.634 | 0.013 | 11 | 0/14 | sim | 9.28 |
| `lns|guloso|E100|k4` | +0.01 | +0.71 | 2.636 | 0.015 | 12 | 0/14 | sim | 11.41 |
| `lns|fluxo|E300|k4` | +0.11 | +0.79 | 2.636 | 0.017 | 13 | 0/14 | sim | 22.29 |
| `lns|guloso|E300|k2` | +0.02 | +0.79 | 2.637 | 0.016 | 13 | 0/14 | sim | 25.24 |
| `lns|guloso|E300|k4` | -0.05 | +1.34 | 2.645 | 0.022 | 18 | 0/14 | sim | 28.19 |

Em 70 planos por configuração (14 dias × 5 sementes), a aceitação nos pseudodias disjuntos escolheu o plano vazio em 56 a 66 casos e nunca o plano inicial (guloso ou fluxo): os movimentos que melhoram J nos pseudodias de busca não se sustentam nos outros dias históricos. O resultado no dia real fica perto do baseline: de +0,17% a +1,34% de KM vazio por corrida, nenhum dia com redução. Tempo de plano de 9 a 28 s por dia (5 sementes de 100 a 300 avaliações).

## recozimento

Código `05ef4eb`; calibração 2–15/03, regime B, 04–11h; baseline 1760 corridas e 2.632 km vazios por corrida.

| Configuração | Corridas (%) | KM vazio/corrida (%) | B/corrida | R/corrida | Mov. exec. | Dias com redução | Piso | Tempo (s/dia) |
|---|---:|---:|---:|---:|---:|---:|:---:|---:|
| `sa|T0.02|r0.98` **(finalista)** | +0.02 | +0.57 | 2.636 | 0.011 | 10 | 0/14 | sim | 26.73 |
| `sa|T0.02|r0.995` | +0.11 | +0.58 | 2.634 | 0.014 | 10 | 0/14 | sim | 29.00 |
| `sa|T0.005|r0.995` | +0.11 | +1.00 | 2.638 | 0.021 | 18 | 0/14 | sim | 28.01 |
| `sa|T0.005|r0.98` | +0.10 | +1.38 | 2.641 | 0.028 | 23 | 0/14 | sim | 26.51 |

Mesmo padrão do LNS: nos 280 planos (4 configurações × 14 dias × 5 sementes), a aceitação escolheu o plano vazio em 236 e o melhor plano da busca em 44; nunca o guloso inicial. KM vazio por corrida de +0,57% a +1,38%, corridas de +0,02% a +0,11%, nenhum dia com redução para o finalista (T0 = 0,02; r = 0,98). Tempo de plano de 27 a 29 s por dia (5 sementes × 300 avaliações).

## pso

Código `056eb91`; calibração 2–15/03, regime B, 04–11h; baseline 1760 corridas e 2.632 km vazios por corrida.

| Configuração | Corridas (%) | KM vazio/corrida (%) | B/corrida | R/corrida | Mov. exec. | Dias com redução | Piso | Tempo (s/dia) |
|---|---:|---:|---:|---:|---:|---:|:---:|---:|
| `pso|p0.95|w0.5` **(finalista)** | +0.14 | +0.92 | 2.637 | 0.020 | 16 | 0/14 | sim | 28.46 |
| `pso|p0.8|w0.5` | +0.11 | +0.95 | 2.635 | 0.022 | 16 | 0/14 | sim | 25.52 |
| `pso|p0.8|w0.8` | +0.15 | +1.02 | 2.640 | 0.019 | 14 | 1/14 | sim | 35.77 |
| `pso|p0.95|w0.8` | +0.00 | +1.04 | 2.642 | 0.017 | 14 | 0/14 | sim | 35.78 |

Aceitação: plano vazio em 212 de 280 planos, melhor partícula em 68, guloso inicial nunca. KM vazio por corrida de +0,92% a +1,04%, corridas de 0,00% a +0,15%. Finalista p_ficar = 0,95, w = 0,5 (+0,92%). Tempo de 26 a 36 s por dia (5 sementes × 300 avaliações).

## robusto_cenarios

Código `64ce556`; calibração 2–15/03, regime B, 04–11h; baseline 1760 corridas e 2.632 km vazios por corrida.

| Configuração | Corridas (%) | KM vazio/corrida (%) | B/corrida | R/corrida | Mov. exec. | Dias com redução | Piso | Tempo (s/dia) |
|---|---:|---:|---:|---:|---:|---:|:---:|---:|
| `robusto|S10|esperado` **(finalista)** | +0.00 | +0.02 | 2.632 | 0.000 | 1 | 0/14 | sim | 0.52 |
| `robusto|S20|esperado` | +0.00 | +0.02 | 2.632 | 0.001 | 1 | 0/14 | sim | 1.14 |
| `robusto|S5|esperado` | +0.00 | +0.03 | 2.632 | 0.001 | 1 | 0/14 | sim | 0.26 |
| `robusto|S10|cvar` | +0.06 | +0.05 | 2.631 | 0.003 | 2 | 1/14 | sim | 0.65 |
| `robusto|S20|cvar` | +0.03 | +0.08 | 2.632 | 0.003 | 2 | 0/14 | sim | 1.60 |
| `robusto|S5|cvar` | +0.02 | +0.11 | 2.632 | 0.003 | 2 | 0/14 | sim | 0.27 |

Com cap = 1, β = 0,99 e μ = 0,5 km herdados do finalista 5.3 (pré-registro), o MILP por cenários quase não move: 0,6 a 2 movimentos executados em 14 dias (média das sementes). KM vazio por corrida de +0,02% a +0,11%, nenhum dia com redução. Sensibilidade a S: com valor esperado, S = 5, 10 e 20 dão +0,03%, +0,02% e +0,02%; com CVaR₀,₈, +0,11%, +0,05% e +0,08%. O tempo cresce com S (0,26 a 1,6 s por dia). Como a demanda por cenário não muda a desigualdade triangular com cap = 1, o resultado repete o de 5.3.

## mpc

Código `7e28d10`; calibração 2–15/03, regime B, 04–11h; baseline 1760 corridas e 2.632 km vazios por corrida.

| Configuração | Corridas (%) | KM vazio/corrida (%) | B/corrida | R/corrida | Mov. exec. | Dias com redução | Piso | Tempo (s/dia) |
|---|---:|---:|---:|---:|---:|---:|:---:|---:|
| `mpc|H1h|a0.5` **(finalista)** | +0.00 | +0.01 | 2.632 | 0.000 | 1 | 0/14 | sim | 0.11 |
| `mpc|H2h|a0.5` | -0.06 | +0.42 | 2.630 | 0.013 | 21 | 0/14 | sim | 0.11 |
| `mpc|H1h|a0.2` | +0.11 | +1.90 | 2.623 | 0.059 | 76 | 1/14 | sim | 0.11 |
| `mpc|H2h|a0.2` | +0.85 | +13.13 | 2.634 | 0.344 | 293 | 0/14 | sim | 0.13 |

**Cenário intradiário (fora do escopo D+1; não entra na tabela principal).** Replanejamento a cada 30 min com o estado da frota em tempo real. O KM vazio por corrida cresce com a agressividade: +0,01% (α = 0,5, H = 1 h; 1 movimento em 14 dias), +0,42%, +1,90% e +13,13% (α = 0,2, H = 2 h; 293 movimentos, +0,85% de corridas). Nenhum dia com redução para o finalista. Saber em tempo real onde está cada motorista não mudou o sinal.

## despacho

Código `7e28d10`; calibração 2–15/03, regime B, 04–11h; baseline 1760 corridas e 2.632 km vazios por corrida.

| Configuração | Corridas (%) | KM vazio/corrida (%) | B/corrida | R/corrida | Mov. exec. | Dias com redução | Piso | Tempo (s/dia) |
|---|---:|---:|---:|---:|---:|---:|:---:|---:|
| `despacho|lote60s|raio-1` | -15.28 | -24.73 | 1.981 | 0.000 | 0 | 14/14 | não | 0.00 |
| `despacho|lote30s|raio-1` | -12.73 | -22.43 | 2.042 | 0.000 | 0 | 14/14 | não | 0.00 |
| `despacho|lote60s|raio+0` | -4.43 | -2.12 | 2.576 | 0.000 | 0 | 10/14 | não | 0.00 |
| `despacho|lote30s|raio+0` **(finalista)** | -3.07 | -1.69 | 2.588 | 0.000 | 0 | 11/14 | não | 0.00 |

**D+0 (fora da tabela principal).** O despacho em lote (atribuição de custo mínimo a cada 30 ou 60 s) reduz o KM de busca por corrida, mas perde corridas em todas as configurações: −3,07% (lote de 30 s, raio calibrado) a −15,28% (lote de 60 s, raio − 1 km). Nenhuma configuração respeita o piso de −1%, então o finalista é o de maior razão de corridas (regra pré-registrada). **A redução do KM vazio por corrida aqui vem de recusar ou perder corridas (espera do lote além da paciência e raio menor) e não pode ser chamada de melhoria.**

