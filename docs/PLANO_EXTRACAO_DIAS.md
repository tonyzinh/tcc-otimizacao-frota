# Plano de extração: de onde vêm os 211 dias (08/11/2026)

**211 não é a soma de combinações entidade–dia nem duplicação.** É o número de dias de calendário **distintos** da entidade `solicitacao` (e de `status_solicitacao`): os 99 dias dos períodos aprovados mais 112 dias de **histórico de aquecimento** necessário ao método existente (`lookback_days=56` para previsão de demanda). Antes eu mostrei esse 211 sem rotulá-lo; a unidade correta é "dias distintos por entidade".

## Períodos aprovados (99 dias distintos)
| Finalidade | Intervalo | Dias |
|---|---|---|
| Treino | 01/02–15/03/2026 | 43 |
| Validação | 16/03–31/03/2026 | 16 |
| Replicação | 16/09–30/09/2026 | 15 |
| Avaliação final reservada (só integridade) | 01/10–25/10/2026 | 25 |

## Aquecimento (112 dias; justificativa: janela de 56 dias anteriores ao primeiro dia-alvo)
| Finalidade | Intervalo | Dias | Entidades |
|---|---|---|---|
| Histórico do treino (1º alvo 01/02) | 07/12/2025–31/01/2026 | 56 | solicitacao, status_solicitacao |
| Histórico da replicação (1º alvo 16/09; cobre também 01/10, que precisa de 06/08) | 22/07–15/09/2026 | 56 | solicitacao, status_solicitacao |

Contigüidade: 56 + 43 + 16 = 115 dias (07/12–31/03) e 56 + 15 + 25 = 96 dias (22/07–25/10); 115 + 96 = **211**. Os dias 01/04–21/07 não são extraídos. Setembro e outubro não são usados para ajustar método.

## Tabela por entidade (dias distintos esperados)
| Entidade | Intervalos | Dias | Finalidade |
|---|---|---|---|
| ods/solicitacao, ods/status_solicitacao | 07/12/25–31/03/26; 22/07–25/10/26 | 211 cada | demanda (incl. não atendidas) e histórico |
| ods/veiculo | snapshot | 1 | ponte código→placa |
| ods/veiculo_condutor, jornada_motorista, log_status_motorista | 99 dias aprovados | 99 cada | vínculos, jornada, disponibilidade |
| ods/reposicionamento, compromissos_externos, telemetria_cobli (com vehicle_group) | 99 dias aprovados | 99 cada | KM/ações de reposicionamento, compromissos, diagnóstico Cobli |
| es/posicao_ofertas | 04/01–31/03/26; 19/08–25/10/26 | 87 + 68 = 155 | posições da frota (histórico de 28 d, `fleet._comparable_days`) |
| es/sumario_ofertas, es/reposicionamento_sugerido | 99 dias aprovados | 99 cada | contexto de oferta e sugestões |

Soma: 1.017 lotes ODS-dia + 353 ES-dia (`2×211 + 1 + 6×99` e `155 + 2×99`); antes do ajuste de ES eram 381.

## Excedente preservado
`es/posicao_ofertas` de **07/12/2025 a 03/01/2026** (28 dias) foi extraído antes do ajuste e **não tem finalidade** com histórico de frota de 28 dias. Fica preservado (lotes válidos, esquema 2), fora do plano, e `scripts/cobertura_campanha.py` os relata como `excedentes_preservados`.

## Concorrência (adotada)
Um único leitor ODS pesado por vez, na ordem: P0 fatia técnica de treino (07–13/03, todas as entidades) → P1 núcleo e vínculos do desenvolvimento (01/02–31/03) → P2 compromissos, reposicionamento e Cobli com `vehicle_group` → P3 aquecimento do treino → P4 replicação e avaliação final → P5 aquecimento 22/07–15/09. ES roda em fluxo próprio (outro sistema; ~2 s por dia, não é gargalo). Investigações complementares do DW só quando o ODS estiver ocioso. Cada lote grava duração, linhas e falhas em `data/extraido/v1_viagens/LOG_LOTES.jsonl`; o tempo restante é estimado desses números, sem prometer prazo.
