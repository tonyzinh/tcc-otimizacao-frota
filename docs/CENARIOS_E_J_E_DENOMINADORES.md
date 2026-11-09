# Cenários E e J, auditoria das horas e denominadores (08/11/2026, revisão 2)

Fatia técnica de treino 07, 10 e 13/03/2026. **Simulação e diagnóstico, não resultado científico.** Substitui os percentuais simulados de `DISPONIBILIDADE_E_UNIVERSO.md`.

## 1. Presença, disponibilidade e ocupação são coisas distintas
| Conceito | O que é | O que NÃO prova |
|---|---|---|
| Presença | o motorista consta no feed `posicao_ofertas` num snapshot (~120 s) | disponibilidade; completude da frota |
| Idade da coordenada GPS | `gps_observado_em` vs instante (mediana de -2,7 s em relação ao snapshot) | que o veículo esteja livre |
| Idade da observação de estado | tempo desde o último snapshot do motorista | idem |
| Intervalo entre snapshots | ~120 s (cadência do ES) | — |
| Disponibilidade operacional | **desconhecida**; o enum de status é inferido | — |
| Ocupação | status 3 com solicitação associada (evidência); viagens V1 observadas (retrospectivo) | quem seria atendido numa política alternativa |

`presente_sem_viagem_es` (status 1, 4 e 5) é **evidência de presença sem viagem associada**, não confirmação de que estava livre. Uma posição recente não comprova que o veículo esteja livre.

## 2. Regra formal do cenário E (evidência restrita)
Hipótese H-E (a única que transforma observação em elegibilidade): **o motorista é elegível ao despacho simulado em todo instante coberto por presença contínua no feed, em qualquer status**; a ocupação histórica é descartada e substituída pelas viagens atribuídas pelo simulador. Presença contínua = snapshots consecutivos com lacuna menor ou igual a `gap_sessao_s` (padrão 360 s = 3 cadências; **hipótese de validade da observação, não regra da empresa; configurável**). Cada observação vale até o snapshot + 120 s. Lacunas maiores são **desconhecidas e ficam fora**.

Limitações: pausas curtas dentro de uma presença contínua contam como elegíveis. Motorista fora do feed não é elegível mesmo que estivesse operando (13 de 124 motoristas com corrida em 10/03 nem aparecem; 141 de 738 viagens sem linha no feed). A presença é condicionada à operação histórica (processo de oferta), não é observação independente da política.

Influência de `gap_sessao_s` (10/03, TempoReal; `rastreio_percentual_2026-03-10.json`):

| gap_sessao_s | Atendidos / pedidos | % | Horas-motorista |
|---|---|---|---|
| 240 | 1.054 / 1.279 | 82,4 | 1.267,0 |
| 360 | 1.072 / 1.279 | 83,8 | 1.271,9 |
| 600 | 1.077 / 1.279 | 84,2 | 1.272,3 |
| 1.200 | 1.077 / 1.279 | 84,2 | 1.272,4 |

## 3. Regra formal do cenário J (jornada registrada)
Janela do motorista = **jornada registrada ∩ (presença no feed estendida por pontes de lacunas menores ou iguais a `gap_ponte_s` = 1.200 s)**.
- A jornada **delimita** o período operacional; nunca é tratada inteira como tempo livre.
- Dentro da jornada, lacunas do feed maiores que a ponte são desconhecidas e ficam **fora** (pausas e compromissos restringem). Compromissos externos continuam bloqueando o motorista no simulador.
- Posição inicial: observação válida do feed (condição A, idade máxima configurável). Jornada **sem nenhuma observação** do feed = sem posição válida: motorista **não simulado** (contado em `jornada_sem_feed`).
- Observações do feed **fora** da jornada: **excluídas** de J (conflito resolvido a favor da jornada) e contadas em horas.
- Motorista no feed sem jornada atribuída (ponte ausente ou ambígua): mantém a janela de E (contado), pois não há como delimitar.
- Jornada usada: início/fim **realizados** = informação do avaliador retrospectivo, não do planejador na véspera. Para o planejador valeria só a escala estimada, que não foi validada.
- J é análise de sensibilidade e **não** é limite superior garantido. Bloqueio atual: `jornada_motorista` ainda em extração.

## 4. Auditoria das horas de 10/03 (`auditoria_horas_evidencia.json`)
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

## 5. Denominadores de 10/03
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

## 6. De onde veio a mudança de "82 %" para "84,5 %" (rastreada)
| Versão | Mudança | Resultado |
|---|---|---|
| Execução parcial original | todos os tipos, gap 1.200 s | 1.084 / 1.325 = 81,8 % |
| Universo | só TempoReal | 1.077 / 1.279 = 84,2 % |
| Regra de sessão | gap 360 s | 1.072 / 1.279 = 83,8 % |
| Substituída | o "84,5 %" (1.081 / 1.279) vinha de uma **falha de implementação** do E novo: runs de classes diferentes ficavam separados por buracos de cerca de 1 s e fragmentavam as sessões | corrigida; a versão 1 reproduz exatamente 81,8 % |

Mudaram, portanto, o **universo** (-0,0 a +2,4 pp) e a **regra de sessão** (-0,4 pp); o 84,5 % foi artefato de código, já corrigido.

## 7. Novas tentativas: cadeias, não "321 duplicidades"
Critério de sinalização: mesmo passageiro, até 10 min, origem a até 150 m. Em 10/03: **1.081 pares**, **542 solicitações em algum par**, **156 cadeias** (tamanhos de 2 a 16; 88 de tamanho 2), 99 cadeias com alguma corrida encerrada. Uma solicitação pode estar em vários pares; pares não são duplicidades nem demandas independentes. 07/03: 214 cadeias (746 solicitações); 13/03: 242 cadeias (771).

**De 321 para 1.081.** Os 321 (07/03: 431; 13/03: 442) eram pares *consecutivos* do mesmo passageiro (vizinho imediato), no universo de 1.325, calculados na primeira versão; os 1.081 (07/03: 1.281; 13/03: 1.223) são *todos* os pares i<j não ordenados dentro de 10 min e 150 m, e as cadeias vêm de componentes conexos desses pares. Mesmo universo e critério; mudaram a contagem (consecutivo vs. todos os pares) e o tratamento de cadeias. Ambas as contagens são reproduzidas por `scripts/decompor_solicitacoes.py` (`pares_consecutivos_versao_1` e `pares`). Tolerâncias (10 min, 150 m) não foram alteradas.

**Nada foi removido.** A base original é preservada. `--deduplicar` (manter a primeira de cada cadeia consecutiva) é **sensibilidade**: 968 pedidos, 845 atendidos (87,3 %).

O desfecho futuro não decide retroativamente que um pedido nunca deveria existir. Três comportamentos ficam separados: (a) elegibilidade conhecida na chegada (origem, tipo, região); (b) cancelamento ou abandono posterior (hoje: paciência herdada de 180 s, sem cancelamento pós-atribuição); (c) novas tentativas da mesma demanda (sem modelo de comportamento). Limitação declarada: sem modelo defensável de (b) e (c), a demanda simulada depende dessas hipóteses; o universo original e a versão agrupada são **cenários de sensibilidade distintos**, não limites inferior/superior da demanda real.

## 8. Reconstrução × simulação (conferida)
A) Reconstrução histórica: status e viagens observadas descrevem a operação registrada. B) Simulação: depois da inicialização, ocupação e posição vêm das viagens que o simulador atribui; o status histórico "ocupado" não é aplicado ao veículo simulado, e posições posteriores não corrigem sua trajetória. Jornadas e compromissos externos são entradas comuns às políticas e não duplicam V1 (teste e contador `compromissos_que_sao_pedidos_v1_simulados`).

## 9. Inicialização, unicidade de recursos e planos de informação (revisão 3)
- **Presença no feed só delimita participação.** Para receber pedido o veículo também precisa estar livre no estado do simulador, com compromissos e pausas respeitados. `aparar_inicio_ocupado`: veículo cuja janela começa com evidência de ocupação (status 3 com solicitação) só entra quando a viagem histórica em andamento termina. Aproximação registrada: usa a duração observada (informação do avaliador, igual a todas as políticas). Em 07, 10 e 13/03: 30, 31 e 29 janelas (de 114, 160 e 160) começavam ocupadas; 29,2, 49,0 e 34,7 h aparadas. Depois da inicialização só viagens simuladas determinam ocupação.
- **Três planos de informação.** (1) Calendário de presença do ambiente: construído retrospectivamente (a presença contínua depende de observar o snapshot seguinte); (2) planejador D+1: só o feed de D com `event_time <= corte − atraso_base_s` (120 s) e a demanda de datas anteriores a D; nunca o fim de sessão reconstruído nem observação futura; (3) despacho: conhece apenas os motoristas elegíveis no instante, sem consultar o fim da sua janela. **O cenário J usa a jornada realizada e, portanto, não valida a capacidade de prever a disponibilidade em D+1.**
- **Unicidade (`resolver_unicidade`, `trocas_de_recurso`).** Sobreposição acima de 150 s na mesma placa entre motoristas diferentes, ou do mesmo motorista em duas placas, é recortada (trecho excluído e contado). Em 07, 10 e 13/03: 0 conflitos de placa, 0 de motorista, 0 h excluídas; trocas observadas de placa/motorista: 7 e 4, 1 e 1, 5 e 4; nenhuma com salto maior que 2 km (sem teleporte). Ausência de conflito dentro do dia não prova ausência entre sessões de outros dias; vínculos ambíguos não são resolvidos por inferência.
- **Hipótese D+1 do adaptador.** Repetir a presença de D em D+1 é hipótese de previsão (`escala_persistente`), não escala confirmada. Parâmetros do guloso: origem única `ARTICLE_GREEDY` (alpha 0,2; rho 2,5 km; max 3,0 km), hash do arquivo registrado por `proveniencia_parametros()`; não ajustados com dados de outubro.
