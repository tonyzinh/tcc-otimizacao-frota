# Disponibilidade, universo de solicitações e a execução P0 (08/11/2026)

> **Revisado por `docs/CENARIOS_E_J_E_DENOMINADORES.md`.** Os percentuais simulados deste arquivo (71,5 / 84,5 / 82,7 %) vieram de uma construção do cenário E que fragmentava sessões (buraco de cerca de 1 s entre classes de status) e estão **substituídos** pelos de lá (67,3 / 83,8 / 80,4 %). As contagens de 321, 431 e 442 "pares" também foram revistas (cadeias).

Fatia técnica de **treino**: 07, 10 e 13/03/2026. Tudo abaixo é **simulação ou diagnóstico**; nada demonstra redução de km morto. Scripts: `diagnosticar_feed_ofertas.py`, `tabela_evidencias.py`, `decompor_solicitacoes.py`, `executar_referencia_fatia.py`. Código: `src/tcc_frota/referencia/`.

## 1. O que é o feed `posicao_ofertas` (evidência de 10/03; 3 dias em `reports/extracao_v1_viagens/diagnostico_feed_ofertas.json`)
| Pergunta | Resposta medida | Leitura |
|---|---|---|
| Veículos por snapshot | 16 a 86 (mediana 60), a cada ~120 s (712 snapshots) | roster do processo de oferta, não cadastro da frota |
| Há veículos ocupados? | **Sim**: status 3 = 20.513 linhas, 100% com solicitação associada, 48,7% com passageiro embarcado | presença ≠ disponibilidade |
| Status 1 e 5 | sem solicitação e sem passageiro (12.039 e 5.535 linhas) | compatíveis com "livre", mas o enum é **inferido** |
| Timestamp | `dataHora` do snapshot; GPS observado é anterior (mediana −2,7 s) | não é o instante da oferta a uma solicitação |
| Duplicidade por (snapshot, motorista) | 0 | — |
| Durante as 738 viagens encerradas, status do feed | 100% status 3; **141 viagens (19%) sem nenhuma linha** do motorista na viagem; 13 de 124 motoristas com corrida ausentes do feed no dia | o feed **subcobre** parte da atividade real: ausência não prova indisponibilidade |

Regra adotada: a presença é **observação condicionada ao processo de oferta**. Não se constrói jornada contínua entre a primeira e a última oferta do dia (a mediana desse intervalo é 11,5 h e o p95 chega a 24 h). Só presença contínua (lacuna ≤ 3 snapshots = 360 s) vira intervalo; lacunas maiores viram **desconhecido**, nunca "livre".

## 2. Tabela de evidências (`scripts/tabela_evidencias.py`; individual em `reports/runs/`, ignorado pelo git)
Cada linha: motorista, placa (pseudônimo), início/fim, estado, fonte, certeza, posição e horário da observação, e se o planejador sabia (dia-alvo = retrospectivo). Estados: `ocupado_com_evidencia`, `presente_sem_viagem_es` (hipótese de livre, certeza baixa), `em_jornada_registrada` (hipótese), `desconhecido`. O que cada fonte afirma e o que deixa desconhecido: `reports/extracao_v1_viagens/evidencias_disponibilidade.json` (chave `fontes`).

10/03 (sem jornada ainda): ES ocupado 683,2 h; ES presente sem viagem 587,7 h; lacunas desconhecidas 264,8 h; viagens V1 observadas 331,6 h (retrospectivo). As 683 h de ocupação no ES superam as 332 h de viagens V1 porque o status 3 inclui deslocamento até o passageiro e espera.

## 3. Reconstrução histórica × simulação
- **Reconstrução:** as viagens V1 observadas explicam estados reais.
- **Simulação:** a ocupação é a das viagens que o próprio simulador atribui. As viagens V1 históricas **não** entram como compromissos (teste `test_mundo_exclui_agendamento_por_tipo_mantem_cancelados_e_nao_bloqueia_por_viagem_v1`; o relatório da execução traz `compromissos_que_sao_pedidos_v1_simulados (deve ser 0)`). A posição após a divergência é a do simulador; a posição histórica só inicializa o início da jornada.
- Entradas comuns aos cenários (natureza declarada): janelas de disponibilidade (cenário E ou J), compromissos externos (fora do universo V1; hipótese: conhecidos desde o início), posição inicial (condição A).

## 4. Cenários de disponibilidade (sensibilidade, não limites garantidos)
- **E, evidência restrita:** janelas = presença contínua no feed (qualquer status; o simulador substitui a ocupação). Lacunas ficam fora.
- **J, jornada registrada + hipóteses:** E ∪ jornada registrada do condutor levada ao motorista por vínculo vigente → veículo → placa → motorista do feed; ambiguidades descartadas e contadas. Pausas dentro da jornada contam como disponíveis (hipótese). Precisa de `veiculo_condutor` e `jornada_motorista` (em extração).

## 5. As 1.325 solicitações de 10/03 (`decomposicao_solicitacoes.json`)
| Desfecho (sequência de eventos) | 10/03 | 07/03 | 13/03 |
|---|---|---|---|
| Encerradas | 738 | 512 | 810 |
| Não atendidas | 252 | 433 | 400 |
| Canceladas após atribuição (`CondutorACaminho` na sequência) | 141 | 120 | 170 |
| Canceladas antes da atribuição | 131 | 195 | 158 |
| Limite de espera atingido | 24 | 40 | 56 |
| Pagamento rejeitado | 23 | 28 | 39 |
| Outros / sem sequência no log | 16 | 20 | 34 |
| **Total** | **1.325** | **1.348** | **1.667** |

Outros pontos de 10/03: 46 agendamentos (4%), 197 pedidos passaram por `AguardandoCondutorEmOutraViagem`, 16 `Retracamento`, 70 pedidos entre 00h e 05h59, 38 entre 22h e 23h59; todos têm origem e destino; primeiro status do log coincide com `dt_registro` (mediana 0 s), o que **não** prova que o pedido ficou conhecido ali (RN024 pendente). **321 pares de pedidos do mesmo passageiro em até 10 min e 150 m** (07/03: 431; 13/03: 442): possíveis novas tentativas da mesma demanda; **nada foi removido**.

Universo simulado (padrão): todas as solicitações com origem, **recortadas só por tipo** (agendamento fora, pois o despacho imediato não modela o horário agendado; contados em `pedidos_excluidos_por_tipo`). Cancelados e não atendidos **permanecem como demanda**. Opção de sensibilidade `--deduplicar` (novas tentativas). Cancelamento/abandono: o simulador usa paciência de 180 s **herdada** da calibração anterior, não calibrada nesta base; é hipótese e precisa de sensibilidade.

## 6. "82% × 56%" revisados
Não são métricas equivalentes. Definições:
- **Proporção atendida pelo simulador sob suas hipóteses** (baseline sem reposicionamento, disponibilidade E, universo TempoReal): 10/03 = 1.081 de 1.279 (84,5%); 07/03 = 71,5%; 13/03 = 82,7%.
- **Proporção historicamente encerrada no universo observado:** 738 de 1.325 (55,7%) em 10/03; denominador inclui agendamentos, e o numerador depende de aceite, pagamento e cancelamento reais.

Causas candidatas (nenhuma foi usada para ajustar parâmetros; estado da evidência):
| Causa | Estado |
|---|---|
| Disponibilidade superestimada (presença no feed inclui pausas e tempo parado) | plausível; 1.270,8 h de janela em 10/03 (9,6 h por motorista) para 332 h de viagem V1; **não quantificado contra jornada** (aguarda J) |
| Ausência de jornadas, pausas e compromissos | compromissos e jornada ainda não carregados nesta execução parcial |
| Abandono/cancelamento (131 antes + 141 após a atribuição) | o simulador não modela aceite nem cancelamento pós-atribuição (`post_accept_cancel=False`) |
| Restrições de serviço (tipo de serviço, região, aceite do motorista) | **não representadas** |
| Deslocamento subestimado (velocidade/fator herdados) | parâmetros da calibração anterior, não recalibrados |
| Atribuição ≠ conclusão | no histórico, 141 atribuídas foram canceladas depois |
| Horizonte e encerramento | janela de 24 h com cauda; início de jornada pela 1ª observação |

## 7. Execução P0 parcial × completa
Parcial (diagnóstica, **substituída para avaliação**): `reports/referencia_fatia_teste/` (gap de 20 min, agendamentos incluídos) e `reports/referencia_fatia_diag_E/` (cenário E sem jornada nem compromissos). Efeitos medidos até agora (E sem jornada, 3 dias): 749, 1.270,8 e 1.212,7 h de disponibilidade; 88, 132 e 125 motoristas; espera mediana 516,6, 379,1 e 357,8 s; km de busca estimado 2.306, 2.260 e 2.771. A comparação completa (jornada J e compromissos) entra aqui quando `jornada_motorista` e `compromissos_externos` terminarem a extração. Registrar então: veículos elegíveis, horas, atendidos, espera, km de busca, violações de compromissos e períodos desconhecidos.

## 8. Critério para iniciar a comparação de políticas (A espera × B guloso)
| Requisito | Estado |
|---|---|
| Universo de solicitações definido | **sim**, com hipóteses de tipo, cancelamento e novas tentativas configuráveis |
| Disponibilidade documentada | cenários E e J definidos; **J aguarda extração** |
| Compromissos externos | módulo e auditoria prontos; **aguardam extração**; teletransporte da v2 é limitação auditada |
| Condições iniciais sem informação futura | **sim** (condição A; B pendente por falta de coordenadas) |
| Contabilidade de tempo e km | auditada (sem violações nos 3 dias) |
| Hipóteses configuráveis e identificadas | sim (`config/hipoteses_tempo.yaml`, `config/referencia_espera_destino.yaml`) |
| Guloso "atual" nos mesmos dados | **não executado**: precisa do adaptador de entrada `Inputs` e das regras; não reescrito |
