# Indicadores e interpretação

| Indicador | Cálculo no MVP | Rótulo obrigatório |
|---|---|---|
| Pickup vazio | soma Haversine entre posição livre e origem de pedido atendido | km geodésico estimado |
| Reposicionamento | soma Haversine dos movimentos aplicados | km geodésico estimado, mesmo se não houver ganho |
| Retorno | não calculado | ausente, não zero observado |
| KM morto total acadêmico | pickup + reposicionamento + retorno validado, se houver | provisório sintético, RN010/DT003 |
| Redução relativa | `(baseline - proposto) / baseline × 100` | somente com denominador positivo e cobertura não inferior |
| Cobertura | pedidos atendidos / pedidos do teste | métrica de controle; `None` sem pedidos |
| KM por atendimento | KM total / pedidos atendidos | `None` sem atendidos |
| Espera | média do tempo estimado de deslocamento ao pickup | velocidade constante, não tempo observado |
| Exclusões | contagem por motivo | ausência nunca vira zero |

`observed_km` permanece nulo nos relatórios sintéticos. Valores de `NU_DISTPERCORRIDA` e `NU_DISTANCIA_ACEITE_CHEGUEI` têm conversores separados e não entram automaticamente no replay. `NU_DP`/`NU_DR_REAL` não podem entrar como realizados. Rodagem mensal menos DV não é chamada de KM morto. Ganho em R$ fica fora do relatório até custo marginal validado (RN022/RN029).
