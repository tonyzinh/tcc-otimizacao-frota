# Metodologia do MVP sintético

1. Gere 28 dias históricos e um dia de teste com semente explícita. O conjunto sintético tem timestamps UTC com offset, zonas fictícias aproximadas e IDs artificiais.
2. Audite chaves, nulos, duplicatas, datas e coordenadas. Bronze preserva as linhas geradas; Silver remove registros inválidos e registra contagens; Gold agrega por região/hora/split.
3. Faça o corte às 20:00 UTC do dia anterior. A média por zona/hora usa apenas pedidos anteriores ao corte, com preferência pelo mesmo dia da semana e fallback para todos os dias anteriores. O alvo de teste nunca alimenta a previsão (RN020).
4. Planeje às 07:00 UTC do dia D+1. O guloso avalia ganho projetado de pickup, custo de reposicionamento e cobertura mínima experimental. O plano fica congelado durante o replay.
5. Simule baseline simplificado sem reposicionamento e cenário preventivo com os mesmos pedidos, frota, compromissos, velocidade, espera máxima e distância. Atribuição nos dois cenários usa veículo livre elegível mais próximo.
6. Some pickup geodésico estimado e reposicionamento geodésico estimado. Retorno permanece não mensurado. Compare apenas se entradas forem idênticas e cobertura proposta não piorar; registre ausências e motivos.
7. Varie uma dimensão sintética por vez para sensibilidade. Relate ganhos, perdas e zeros; não ajuste o cenário para obter sinal favorável.

O baseline não é a política da empresa. A amostra sintética não prova impacto operacional. O experimento não simula resposta de passageiros, despacho humano, congestionamento, aderência real ou trajetos viários. A formulação está em [algoritmo.md](algoritmo.md); os resultados executados estão em [resultados.md](resultados.md).
