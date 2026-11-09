# Disponibilidade de motoristas

> Documento consolidado em 09/11/2026 na reestruturação do repositório. Cada parte abaixo é o documento de origem, com o conteúdo preservado; só os caminhos de arquivos foram atualizados para a estrutura nova (mapa em `reports/manifests/repository_restructure/path_map.csv`). Datas e afirmações são as da origem.
> Caminhos marcados com † são de arquivos retirados da árvore ativa nas reorganizações de 09/11/2026 (código e documentos do estudo anterior, scripts substituídos pelo pacote). As cópias estão na pasta de preservação `../tcc-otimizacao-frota_preservacao_2026-11-09/` (`arvore_antiga/`, `rodada4_arquivamento/`, `copia_completa_pre_migracao/`). Nos trechos anteriores a 09/11/2026, `data/raw/` designa a pasta de extrato bruto antiga, apagada em 08/11; desde a reestruturação, `data/raw/` é a antiga `data/extraido/`.


## Cenários E e J, auditoria das horas e denominadores (08/11/2026, revisão 2)

_Origem: `docs/availability.md`._

Fatia técnica de treino 07, 10 e 13/03/2026. **Simulação e diagnóstico, não resultado científico.** Substitui os percentuais simulados de `availability.md`.

### 1. Presença, disponibilidade e ocupação são coisas distintas
| Conceito | O que é | O que NÃO prova |
|---|---|---|
| Presença | o motorista consta no feed `posicao_ofertas` num snapshot (~120 s) | disponibilidade; completude da frota |
| Idade da coordenada GPS | `gps_observado_em` vs instante (mediana de -2,7 s em relação ao snapshot) | que o veículo esteja livre |
| Idade da observação de estado | tempo desde o último snapshot do motorista | idem |
| Intervalo entre snapshots | ~120 s (cadência do ES) | — |
| Disponibilidade operacional | **desconhecida**; o enum de status é inferido | — |
| Ocupação | status 3 com solicitação associada (evidência); viagens V1 observadas (retrospectivo) | quem seria atendido numa política alternativa |

`presente_sem_viagem_es` (status 1, 4 e 5) é **evidência de presença sem viagem associada**, não confirmação de que estava livre. Uma posição recente não comprova que o veículo esteja livre.

### 2. Regra formal do cenário E (evidência restrita)
Hipótese H-E (a única que transforma observação em elegibilidade): **o motorista é elegível ao despacho simulado em todo instante coberto por presença contínua no feed, em qualquer status**; a ocupação histórica é descartada e substituída pelas viagens atribuídas pelo simulador. Presença contínua = snapshots consecutivos com lacuna menor ou igual a `gap_sessao_s` (padrão 360 s = 3 cadências; **hipótese de validade da observação, não regra da empresa; configurável**). Cada observação vale até o snapshot + 120 s. Lacunas maiores são **desconhecidas e ficam fora**.

Limitações: pausas curtas dentro de uma presença contínua contam como elegíveis. Motorista fora do feed não é elegível mesmo que estivesse operando (13 de 124 motoristas com corrida em 10/03 nem aparecem; 141 de 738 viagens sem linha no feed). A presença é condicionada à operação histórica (processo de oferta), não é observação independente da política.

Influência de `gap_sessao_s` (10/03, TempoReal; `rastreio_percentual_2026-03-10.json`):

| gap_sessao_s | Atendidos / pedidos | % | Horas-motorista |
|---|---|---|---|
| 240 | 1.054 / 1.279 | 82,4 | 1.267,0 |
| 360 | 1.072 / 1.279 | 83,8 | 1.271,9 |
| 600 | 1.077 / 1.279 | 84,2 | 1.272,3 |
| 1.200 | 1.077 / 1.279 | 84,2 | 1.272,4 |

### 3. Regra formal do cenário J (jornada registrada)
Janela do motorista = **jornada registrada ∩ (presença no feed estendida por pontes de lacunas menores ou iguais a `gap_ponte_s` = 1.200 s)**.
- A jornada **delimita** o período operacional; nunca é tratada inteira como tempo livre.
- Dentro da jornada, lacunas do feed maiores que a ponte são desconhecidas e ficam **fora** (pausas e compromissos restringem). Compromissos externos continuam bloqueando o motorista no simulador.
- Posição inicial: observação válida do feed (condição A, idade máxima configurável). Jornada **sem nenhuma observação** do feed = sem posição válida: motorista **não simulado** (contado em `jornada_sem_feed`).
- Observações do feed **fora** da jornada: **excluídas** de J (conflito resolvido a favor da jornada) e contadas em horas.
- Motorista no feed sem jornada atribuída (ponte ausente ou ambígua): mantém a janela de E (contado), pois não há como delimitar.
- Jornada usada: início/fim **realizados** = informação do avaliador retrospectivo, não do planejador na véspera. Para o planejador valeria só a escala estimada, que não foi validada.
- J é análise de sensibilidade e **não** é limite superior garantido. Bloqueio atual: `jornada_motorista` ainda em extração.

### 4. Auditoria das horas de 10/03 (`auditoria_horas_evidencia.json`)
Unidade: **horas-motorista** (cada intervalo pertence a um motorista). 132 motoristas, 121 placas, 712 snapshots, horizonte de 24 h.

| Estado | Horas-motorista (soma) | União por motorista | Sobreposição interna | Intervalos |
|---|---|---|---|---|
| ocupado com evidência (ES, status 3 com solicitação) | 683,2 | 683,2 | 0 | 650 |
| presente sem viagem (ES, status 1, 4 e 5) | 587,7 | 587,7 | 0 | 775 |
| desconhecido (lacunas do feed maiores que 360 s) | 264,8 | 264,8 | 0 | 635 |

- Sobreposição entre estados do mesmo motorista: 0,045 h (cerca de 2,7 min no total, por o fim ser último snapshot + 120 s).
- Duplicidade (snapshot, motorista) = 0; mesma placa duas vezes no mesmo snapshot = 0.
- Presença total: 1.270,8 h-motorista = 1.270,8 h-veículo (uma placa por motorista por vez).
- **16 motoristas usaram mais de uma placa e 27 placas tiveram mais de um motorista no dia** (revezamento sequencial).
- As horas são de presença observada, **não capacidade disponível**: o status 3 inclui deslocamento ao passageiro e o enum é inferido.

### 5. Denominadores de 10/03
Desfechos das 1.325 solicitações V1 (sequência de eventos do log, não só status final):

| Desfecho | Contagem |
|---|---|
| Encerradas | 738 |
| Não atendidas | 252 |
| Canceladas após a atribuição | 141 |
| Canceladas antes da atribuição | 131 |
| Limite de espera atingido | 24 |
| Pagamento rejeitado | 23 |
| Outros / sem sequência no log | 16 |
| **Soma** | **1.325** |

Escada do universo simulado:

| Etapa | Contagem |
|---|---|
| Universo bruto (solicitações V1 do dia) | 1.325 |
| Exclusão por tipo Agendamento (motivo único; o despacho imediato não modela o horário agendado) | -46 |
| Exclusão por falta de origem | 0 |
| **Universo elegível (TempoReal)** | **1.279** |
| Atendidos pelo simulador (cenário E, gap 360 s) | 1.072 |
| Proporção atendida pelo simulador sob suas hipóteses | 1.072 / 1.279 = 83,8 % |
| Encerradas historicamente no universo bruto | 738 / 1.325 = 55,7 % |

As duas proporções não são equivalentes (denominadores e definições diferentes; a histórica depende de aceite, pagamento e cancelamento reais).

### 6. De onde veio a mudança de "82 %" para "84,5 %" (rastreada)
| Versão | Mudança | Resultado |
|---|---|---|
| Execução parcial original | todos os tipos, gap 1.200 s | 1.084 / 1.325 = 81,8 % |
| Universo | só TempoReal | 1.077 / 1.279 = 84,2 % |
| Regra de sessão | gap 360 s | 1.072 / 1.279 = 83,8 % |
| Substituída | o "84,5 %" (1.081 / 1.279) vinha de uma **falha de implementação** do E novo: runs de classes diferentes ficavam separados por buracos de cerca de 1 s e fragmentavam as sessões | corrigida; a versão 1 reproduz exatamente 81,8 % |

Mudaram, portanto, o **universo** (-0,0 a +2,4 pp) e a **regra de sessão** (-0,4 pp); o 84,5 % foi artefato de código, já corrigido.

### 7. Novas tentativas: cadeias, não "321 duplicidades"
Critério de sinalização: mesmo passageiro, até 10 min, origem a até 150 m. Em 10/03: **1.081 pares**, **542 solicitações em algum par**, **156 cadeias** (tamanhos de 2 a 16; 88 de tamanho 2), 99 cadeias com alguma corrida encerrada. Uma solicitação pode estar em vários pares; pares não são duplicidades nem demandas independentes. 07/03: 214 cadeias (746 solicitações); 13/03: 242 cadeias (771).

**De 321 para 1.081.** Os 321 (07/03: 431; 13/03: 442) eram pares *consecutivos* do mesmo passageiro (vizinho imediato), no universo de 1.325, calculados na primeira versão; os 1.081 (07/03: 1.281; 13/03: 1.223) são *todos* os pares i<j não ordenados dentro de 10 min e 150 m, e as cadeias vêm de componentes conexos desses pares. Mesmo universo e critério; mudaram a contagem (consecutivo vs. todos os pares) e o tratamento de cadeias. Ambas as contagens são reproduzidas por `scripts/decompor_solicitacoes.py`† (`pares_consecutivos_versao_1` e `pares`). Tolerâncias (10 min, 150 m) não foram alteradas.

**Nada foi removido.** A base original é preservada. `--deduplicar` (manter a primeira de cada cadeia consecutiva) é **sensibilidade**: 968 pedidos, 845 atendidos (87,3 %).

O desfecho futuro não decide retroativamente que um pedido nunca deveria existir. Três comportamentos ficam separados: (a) elegibilidade conhecida na chegada (origem, tipo, região); (b) cancelamento ou abandono posterior (hoje: paciência herdada de 180 s, sem cancelamento pós-atribuição); (c) novas tentativas da mesma demanda (sem modelo de comportamento). Limitação declarada: sem modelo defensável de (b) e (c), a demanda simulada depende dessas hipóteses; o universo original e a versão agrupada são **cenários de sensibilidade distintos**, não limites inferior/superior da demanda real.

### 8. Reconstrução × simulação (conferida)
A) Reconstrução histórica: status e viagens observadas descrevem a operação registrada. B) Simulação: depois da inicialização, ocupação e posição vêm das viagens que o simulador atribui; o status histórico "ocupado" não é aplicado ao veículo simulado, e posições posteriores não corrigem sua trajetória. Jornadas e compromissos externos são entradas comuns às políticas e não duplicam V1 (teste e contador `compromissos_que_sao_pedidos_v1_simulados`).

### 9. Inicialização, unicidade de recursos e planos de informação (revisão 3)
- **Presença no feed só delimita participação.** Para receber pedido o veículo também precisa estar livre no estado do simulador, com compromissos e pausas respeitados. `aparar_inicio_ocupado`: veículo cuja janela começa com evidência de ocupação (status 3 com solicitação) só entra quando a viagem histórica em andamento termina. Aproximação registrada: usa a duração observada (informação do avaliador, igual a todas as políticas). Em 07, 10 e 13/03: 30, 31 e 29 janelas (de 114, 160 e 160) começavam ocupadas; 29,2, 49,0 e 34,7 h aparadas. Depois da inicialização só viagens simuladas determinam ocupação.
- **Três planos de informação.** (1) Calendário de presença do ambiente: construído retrospectivamente (a presença contínua depende de observar o snapshot seguinte); (2) planejador D+1: só o feed de D com `event_time <= corte − atraso_base_s` (120 s) e a demanda de datas anteriores a D; nunca o fim de sessão reconstruído nem observação futura; (3) despacho: conhece apenas os motoristas elegíveis no instante, sem consultar o fim da sua janela. **O cenário J usa a jornada realizada e, portanto, não valida a capacidade de prever a disponibilidade em D+1.**
- **Unicidade (`resolver_unicidade`, `trocas_de_recurso`).** Sobreposição acima de 150 s na mesma placa entre motoristas diferentes, ou do mesmo motorista em duas placas, é recortada (trecho excluído e contado). Em 07, 10 e 13/03: 0 conflitos de placa, 0 de motorista, 0 h excluídas; trocas observadas de placa/motorista: 7 e 4, 1 e 1, 5 e 4; nenhuma com salto maior que 2 km (sem teleporte). Ausência de conflito dentro do dia não prova ausência entre sessões de outros dias; vínculos ambíguos não são resolvidos por inferência.
- **Hipótese D+1 do adaptador.** Repetir a presença de D em D+1 é hipótese de previsão (`escala_persistente`), não escala confirmada. Parâmetros do guloso: origem única `ARTICLE_GREEDY` (alpha 0,2; rho 2,5 km; max 3,0 km), hash do arquivo registrado por `proveniencia_parametros()`; não ajustados com dados de outubro.


## Disponibilidade, universo de solicitações e a execução P0 (08/11/2026)

_Origem: `docs/availability.md`._

> **Revisado por `docs/availability.md`.** Os percentuais simulados deste arquivo (71,5 / 84,5 / 82,7 %) vieram de uma construção do cenário E que fragmentava sessões (buraco de cerca de 1 s entre classes de status) e estão **substituídos** pelos de lá (67,3 / 83,8 / 80,4 %). As contagens de 321, 431 e 442 "pares" também foram revistas (cadeias).

Fatia técnica de **treino**: 07, 10 e 13/03/2026. Tudo abaixo é **simulação ou diagnóstico**; nada demonstra redução de km morto. Scripts: `diagnosticar_feed_ofertas.py`, `tabela_evidencias.py`, `decompor_solicitacoes.py`, `executar_referencia_fatia.py`. Código: `src/tcc_frota/data/`.

### 1. O que é o feed `posicao_ofertas` (evidência de 10/03; 3 dias em `reports/data_quality/v1_viagens_extraction/diagnostico_feed_ofertas.json`)
| Pergunta | Resposta medida | Leitura |
|---|---|---|
| Veículos por snapshot | 16 a 86 (mediana 60), a cada ~120 s (712 snapshots) | roster do processo de oferta, não cadastro da frota |
| Há veículos ocupados? | **Sim**: status 3 = 20.513 linhas, 100% com solicitação associada, 48,7% com passageiro embarcado | presença ≠ disponibilidade |
| Status 1 e 5 | sem solicitação e sem passageiro (12.039 e 5.535 linhas) | compatíveis com "livre", mas o enum é **inferido** |
| Timestamp | `dataHora` do snapshot; GPS observado é anterior (mediana −2,7 s) | não é o instante da oferta a uma solicitação |
| Duplicidade por (snapshot, motorista) | 0 | — |
| Durante as 738 viagens encerradas, status do feed | 100% status 3; **141 viagens (19%) sem nenhuma linha** do motorista na viagem; 13 de 124 motoristas com corrida ausentes do feed no dia | o feed **subcobre** parte da atividade real: ausência não prova indisponibilidade |

Regra adotada: a presença é **observação condicionada ao processo de oferta**. Não se constrói jornada contínua entre a primeira e a última oferta do dia (a mediana desse intervalo é 11,5 h e o p95 chega a 24 h). Só presença contínua (lacuna ≤ 3 snapshots = 360 s) vira intervalo; lacunas maiores viram **desconhecido**, nunca "livre".

### 2. Tabela de evidências (`scripts/tabela_evidencias.py`†; individual em `data/processed/run_outputs/`, ignorado pelo git)
Cada linha: motorista, placa (pseudônimo), início/fim, estado, fonte, certeza, posição e horário da observação, e se o planejador sabia (dia-alvo = retrospectivo). Estados: `ocupado_com_evidencia`, `presente_sem_viagem_es` (hipótese de livre, certeza baixa), `em_jornada_registrada` (hipótese), `desconhecido`. O que cada fonte afirma e o que deixa desconhecido: `reports/data_quality/v1_viagens_extraction/evidencias_disponibilidade.json` (chave `fontes`).

10/03 (sem jornada ainda): ES ocupado 683,2 h; ES presente sem viagem 587,7 h; lacunas desconhecidas 264,8 h; viagens V1 observadas 331,6 h (retrospectivo). As 683 h de ocupação no ES superam as 332 h de viagens V1 porque o status 3 inclui deslocamento até o passageiro e espera.

### 3. Reconstrução histórica × simulação
- **Reconstrução:** as viagens V1 observadas explicam estados reais.
- **Simulação:** a ocupação é a das viagens que o próprio simulador atribui. As viagens V1 históricas **não** entram como compromissos (teste `test_mundo_exclui_agendamento_por_tipo_mantem_cancelados_e_nao_bloqueia_por_viagem_v1`; o relatório da execução traz `compromissos_que_sao_pedidos_v1_simulados (deve ser 0)`). A posição após a divergência é a do simulador; a posição histórica só inicializa o início da jornada.
- Entradas comuns aos cenários (natureza declarada): janelas de disponibilidade (cenário E ou J), compromissos externos (fora do universo V1; hipótese: conhecidos desde o início), posição inicial (condição A).

### 4. Cenários de disponibilidade (sensibilidade, não limites garantidos)
- **E, evidência restrita:** janelas = presença contínua no feed (qualquer status; o simulador substitui a ocupação). Lacunas ficam fora.
- **J, jornada registrada + hipóteses:** E ∪ jornada registrada do condutor levada ao motorista por vínculo vigente → veículo → placa → motorista do feed; ambiguidades descartadas e contadas. Pausas dentro da jornada contam como disponíveis (hipótese). Precisa de `veiculo_condutor` e `jornada_motorista` (em extração).

### 5. As 1.325 solicitações de 10/03 (`decomposicao_solicitacoes.json`)
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

### 6. "82% × 56%" revisados
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

### 7. Execução P0 parcial × completa
Parcial (diagnóstica, **substituída para avaliação**): `reports/historical/development/reference_slices/test/` (gap de 20 min, agendamentos incluídos) e `reports/historical/development/reference_slices/diag_E/` (cenário E sem jornada nem compromissos). Efeitos medidos até agora (E sem jornada, 3 dias): 749, 1.270,8 e 1.212,7 h de disponibilidade; 88, 132 e 125 motoristas; espera mediana 516,6, 379,1 e 357,8 s; km de busca estimado 2.306, 2.260 e 2.771. A comparação completa (jornada J e compromissos) entra aqui quando `jornada_motorista` e `compromissos_externos` terminarem a extração. Registrar então: veículos elegíveis, horas, atendidos, espera, km de busca, violações de compromissos e períodos desconhecidos.

### 8. Critério para iniciar a comparação de políticas (A espera × B guloso)
| Requisito | Estado |
|---|---|
| Universo de solicitações definido | **sim**, com hipóteses de tipo, cancelamento e novas tentativas configuráveis |
| Disponibilidade documentada | cenários E e J definidos; **J aguarda extração** |
| Compromissos externos | módulo e auditoria prontos; **aguardam extração**; teletransporte da v2 é limitação auditada |
| Condições iniciais sem informação futura | **sim** (condição A; B pendente por falta de coordenadas) |
| Contabilidade de tempo e km | auditada (sem violações nos 3 dias) |
| Hipóteses configuráveis e identificadas | sim (`configs/data/time_access_assumptions.yaml`, `configs/data/destination_wait_reference.yaml`) |
| Guloso "atual" nos mesmos dados | **não executado**: precisa do adaptador de entrada `Inputs` e das regras; não reescrito |
