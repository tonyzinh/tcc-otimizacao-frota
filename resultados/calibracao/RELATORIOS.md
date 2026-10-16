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

