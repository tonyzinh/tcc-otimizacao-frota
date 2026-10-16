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

