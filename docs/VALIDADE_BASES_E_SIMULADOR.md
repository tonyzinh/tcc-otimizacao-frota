# Validade das bases e do simulador (09/11/2026)

Verificação do que consta no pedido (itens 5 e 6). Rótulos: **testado** (teste automatizado), **verificado** (inspeção ou execução nesta etapa), **limitação** (permanece), **pendente**.

## 1. Bases reais (`data/extraido/v1_viagens`)

| Item | Situação | Evidência |
|---|---|---|
| Integridade dos arquivos e cobertura | verificado | `scripts/verificar_bases_reais.py` → `reports/revisao/verificacao_bases_reais.json`: todas as partições abrem; 01/02–31/03, 16–30/09 e 01–25/10 têm todos os dias nas entidades ODS e ES usadas; `telemetria_cobli` só fev–mar; `veiculo` é cadastro sem partição diária |
| Linhas Parquet × log de extração | verificado (corrigido em 09/11) | a divergência de 89 partições era defeito do verificador (somava `rejeitados.parquet`; diferença = `rejeitadas` do log em todas as 89). Corrigido; `problemas: 0` em `reports/revisao/verificacao_bases_reais.json` |
| Esquema / versão | verificado | `jornada_motorista`, `veiculo_condutor` e `posicao_ofertas` têm 2 esquemas (partições de `v1_viagens_esquema1_*` não misturadas); pseudonimização `hmac-sha256-v1` com `chave_id` registrado |
| Filtro V1 Viagens | herdado | R-04/R-05 (produto V1, região 1, serviços 1, 11, 12 e 19, sem Prime); não reconferido aqui |
| Vínculo motorista–veículo no tempo | testado | `test_posicao_inicial`, `test_disponibilidade` (unicidade de placa, troca de recurso); histórico de cadastro não é tratado como vínculo confirmado |
| Jornadas, pausas | cenário J = jornada realizada | **limitação**: jornada realizada não é escala conhecida na véspera; o planejador D+1 usa persistência (hipótese B) |
| Compromissos externos | testado | `test_compromissos_deslocamento` (5), `test_referencia_espera_destino` (compromisso bloqueia despacho; deslocamento até a origem) |
| Viagens V1 históricas não bloqueiam veículos | testado | `test_mundo_exclui_agendamento..._nao_bloqueia_por_viagem_v1`: só compromissos *externos* ao universo bloqueiam; viagens V1 são os pedidos a (re)atribuir |
| Condição inicial | verificado | `primeira_posicao_observada` (idade máxima 1.800 s); posição futura nunca localiza instante anterior (`test_nunca_usa_posicao_futura...`) |
| Cancelamentos e novas tentativas | **limitação** | a identificação de novas tentativas do mesmo passageiro não foi feita; pedidos cancelados entram como no universo da referência (`DISPONIBILIDADE_E_UNIVERSO.md`) |
| Cobli (km) | n/a | km Cobli não conciliado **não** é usado como km morto; reconciliação em `RECONCILIACAO_COBLI_COMPARACAO.md` |
| Presença no feed ≠ disponibilidade | respeitado | cenário J usa a jornada para delimitar; feed só localiza |

Elegibilidade dos dias (fixada antes dos algoritmos, R-22): ≥ 300 snapshots do ES e jornada; dia fora dela é excluído com motivo; todos os dias do treino 01/02–15/03 passaram.

## 2. Simulador (`v2/sim.py`; sintético e real)

| Verificação pedida | Situação | Evidência |
|---|---|---|
| Sem teletransporte | testado | real: movimento só após livre e com tempo por distância/velocidade (`test_motorista_fica_no_destino_e_o_segundo_pickup_parte_dali`); sintético: `MetricaRede` falha para posição fora dos pontos (`test_sintetico`) |
| Sem serviços simultâneos | testado | `test_invariantes_passam_no_mundo_simples`, `test_unicidade_placa...`; auditoria de unicidade no executor |
| Busca e reposicionamento consomem tempo e km | testado | `test_recomendacao_vira_movimento_com_km_integral...`; `test_contabilidade_e_viabilidade_dos_planos` (sintético) |
| Compromissos incluem deslocamento | testado | `test_compromissos_deslocamento`; classes de folga A/B/C (R-21) |
| Estado do veículo segue as decisões simuladas | testado | idem; `commit_events` |
| Políticas só veem informação disponível | testado | real: `test_previsao_exclui_o_dia_de_corte...`, `test_frota_planejada_nao_usa_observacao_depois_do_corte...`; sintético: `test_planejador_nao_acessa_pedidos_do_dia_avaliado`; grupo D vê só pedidos já chegados (`test_lote_conta_a_espera_da_janela_e_nao_atribui_antes_da_chegada`) |
| Solicitação não atendida duas vezes | testado | `test_assigner_que_viola_unicidade_e_rejeitado`, `resultado.served_ids` |
| Custos pendentes no fim do horizonte | verificado no código | horizonte = janela + `tail_s` (3 h): corridas iniciadas dentro da janela terminam e o km é contado; movimento que não cabe na janela vira `not_free_in_window` (contado como não executado, não escondido) |
| Reconstrução de disponibilidade com informação posterior | respeitado | usada só no ambiente de avaliação (cenário J), nunca entregue ao planejador como previsão |

## 3. Limitações que permanecem

Velocidade constante e fator rua/reta único no real (16,079 km/h; 1,3012, herdados de março, não recalibrados); no sintético, rede viária OSM entre pontos de parada. O baseline é o despacho ao mais próximo simplificado e calibrado, **não** a operação manual. `move_mode="inicio_turno"`. Cenário J usa a jornada realizada. Km é estimado. Reposicionamento e atribuição são decisões diferentes e o grupo D usa informação do instante (pedidos já chegados), o que altera o escopo D+1 se for o vencedor.
