# Resultados executados: cenário sintético

**Execução local:** 14/10/2026, semente `20261014`, 28 dias de treino sintético, teste em 15/10/2026, corte às 20:00 UTC do dia anterior. Código em `src/tcc_frota/`, artefato [JSON](../reports/examples/synthetic_run.json) e [gráfico SVG](../reports/examples/synthetic_comparison.svg). `run_id`: `d8a9b4d0f2e7`. Os números abaixo são do replay sintético com Haversine, **não da empresa**.

| Indicador | Baseline simplificado | Plano preventivo |
|---|---:|---:|
| Pedidos do teste | 10 | 10 |
| Atendidos | 10 | 10 |
| Cobertura | 100% | 100% |
| Pickup vazio estimado | 14,757861 km | 11,331330 km |
| Reposicionamento estimado | 0 km | 3,426531 km |
| KM vazio estimado total | 14,757861 km | 14,757861 km |

**Redução relativa medida:** **0,0%**. O plano reduziu pickup na mesma quantidade de quilômetros que adicionou como reposicionamento. Isso demonstra por que RN031 é indispensável: olhar só o pickup produziria um ganho artificial. A cobertura não piorou. Não houve KM observado, retorno validado, custo marginal, dado real ou validação operacional.

O mesmo procedimento foi repetido em **três dias sintéticos consecutivos** (15–17/10/2026), cada um com 28 dias anteriores e corte D+1 próprio. O total foi 44,273583 km estimados em cada cenário e 30 pedidos atendidos em cada um; redução agregada de 0,0%. Datas, sementes e identificadores das três execuções constam em `multiple_periods` no JSON. Os três dias usam o mesmo desenho espacial simples, então não representam validação em padrões reais variados.

A análise de sensibilidade [registrada no JSON](../reports/examples/synthetic_run.json) variou frota, cobertura experimental, concentração de demanda de treino/teste, distribuição inicial, limite de reposicionamento e adesão hipotética. Nesse conjunto simples, a redução de KM permaneceu em 0,0% nas execuções comparáveis; com frota de três, a cobertura simulada foi 80%. O resultado não prova impossibilidade de ganho em outros padrões; mostra que a estratégia não gerou redução neste desenho.

| Gate | Sintético | Real |
|---|---|---|
| A dados | aprovado pelo pipeline e auditoria local | pendente |
| B métrica | definição acadêmica provisória explícita | pendente DT003 |
| C disponibilidade | estados/intervalos sintéticos testados | pendente |
| D baseline | simplificado e documentado | política observada pendente |
| E comparabilidade | assinatura das entradas e testes | pendente |
| F resultado | semente, parâmetros e relatório reproduzíveis | pendente |

**Próximo experimento científico:** depois de acordar a definição do KPI e obter dados autorizados, auditar criação de pedido, jornada, posição e política de referência. Não extrapole este resultado sintético a qualquer frota real.
