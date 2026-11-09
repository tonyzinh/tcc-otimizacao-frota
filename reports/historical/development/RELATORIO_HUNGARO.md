# Relatório: atribuição em lote pelo algoritmo húngaro (09/11/2026)

Decisão do proprietário: adotar o húngaro (lote de 60 s) como método a apresentar. Este relatório registra o que foi medido, em duas linhas **que não se somam**, e o que a medição **não** autoriza afirmar. Não reescreve o TCC.

## 1. O que é e o que não é

- **O que é.** Grupo D (atribuição de pedidos a veículos): pedidos que chegam são acumulados por 60 s e atribuídos juntos por uma atribuição ótima (Kuhn–Munkres, implementação própria; lexicográfico: maximiza atendidos, depois minimiza km de busca). O `linear_sum_assignment` do scipy só serve de oráculo em teste (é do tipo Jonker–Volgenant, não o húngaro clássico). Fluxo de custo mínimo dá resultado equivalente.
- **O que não é.** Não é reposicionamento D+1. A hipótese original (alocação preventiva reduz km vazio) **não** foi confirmada em nenhuma das linhas (seção 4). O húngaro muda o **despacho**, que ocorre durante a operação com os pedidos já chegados. Adotá-lo muda o escopo do TCC de "posicionar antes" para "atribuir melhor depois".

## 2. Avaliação contrafactual por simulação com entradas históricas (V1 Viagens, dados reais)

Mesmos pedidos, frota, janela e distância nas políticas. Referência: despacho atual simplificado (cenário J, `primeira_posicao_observada`, raio 4,5 km, 16,079 km/h, fator 1,3012, paciência 180 s). Dias são a unidade; IC95% por bootstrap em blocos de 7 dias.

| Período | Dias | km vazio referência | km vazio húngaro 60 s | Variação | km/dia (IC95%) | Atendidos a mais | P90 espera (s) ref → húngaro |
|---|---|---|---|---|---|---|---|
| Treino 01/02–15/03 | 43 | 87.862 | 83.355 | −5,02% | −102,5 (−137,0; −62,4) | +98 | |
| Validação 16–31/03 | 16 | 36.078 | 34.360 | −4,76% | −107,4 (−139,5; −69,6) | +111 | 1.151 → 1.136 |

- Melhor em 38 de 43 dias (treino) e 14 de 16 (validação). Atendimento e P90 não pioraram. Tempo de planejamento: ~3 s por 16 dias.
- Contraste de mecanismo (validação): o guloso FIFO na mesma janela de 60 s reduz 3,0% do km, mas atende 97 pedidos a menos; o húngaro reduz 4,8% **com** mais atendimentos. Parte do ganho vem do lote, outra da atribuição. Janela de 30 s: húngaro −3,8%, FIFO −1,0%.
- Húngaro × fluxo: no treino o fluxo 60 s foi nominalmente melhor (−5,4%), na validação o húngaro (−4,8% × −4,7%). Diferença dentro do ruído; escolheu-se o húngaro por simplicidade e custo (3 s × 24 s).
- Regra de escolha (pré-registrada) aplicada na validação: vencedor do grupo D = húngaro 60 s. Grupo R (reposicionamento): nenhum método elegível com evidência, **referência mantida**.

## 3. Avaliação em cenários sintéticos (22 cenários, sementes reservadas 20001–20040, uma execução)

Húngaro 60 s contra a referência:

- Redução de km vazio com serviço preservado nos **22 de 22** cenários (mediana −8,4%; faixa −2,1% a −14,0%). Razão de atendidos ≥ 0,996, razão de P90 ≤ 1,0003.
- Confirmatório (S1–S5, Holm): p ajustado = 0,002 em todos os testes de D. Efeito menor em S1 (−2,1%) e maior com frota escassa (−12% a −14%), menor com frota abundante (−3% a −4%).
- Húngaro e fluxo: sem diferença detectável na maioria dos cenários (exploratório).

## 4. Resultados que não favorecem a hipótese original (mantidos)

- Reposicionamento real (R1–R6), validação: nenhum com redução detectável; os que movem veículos tendem a aumentar km (A2: +1,0%). O guloso atual: +0,04%.
- Sintético: o guloso original piorou o km vazio em 21–22 de 22 cenários; o guloso de benefício líquido (N1/N2) quase sempre decide não mover e não reduz.

## 5. Limitações (obrigatórias junto de qualquer número acima)

1. **Linha base fraca.** O despacho de referência é "mais próximo livre", simplificado e calibrado, **não** a operação manual real. Parte do ganho pode ser de uma referência subótima. Km é estimado (distância×fator), não odômetro.
2. **Escopo.** O húngaro usa pedidos já chegados no instante; não é D+1. Implantação exige despacho em lote na operação real, que não foi avaliada.
3. **Sem teste independente real.** Treino e validação já foram examinados (inclusive no diagnóstico do guloso). A replicação 16–30/09 e a final 01–25/10 têm dados extraídos, mas **não foram executadas** (exigem congelamento e `TCC_COMPARACAO_VENCEDOR_CONGELADO=SIM`). Os números reais acima são, portanto, de desenvolvimento/validação.
4. Linha real: 59 dias de um único recorte (fev–mar), velocidade e fator constantes herdados de março; o cenário J usa a jornada realizada, não a escala conhecida na véspera.
5. Linha sintética mede generalização para novas realizações do mesmo gerador, não validade operacional.
6. Linhas real e sintética **não são somadas**.

## 6. Interrompido ou não feito

- Fase `avaliacao_busca` (tabu e recozimento sintéticos sobre N1): interrompida a pedido; saída parcial em `reports/sintetico_v2/metodos_avaliacao_busca/` (sem manifesto, **não analisar**). Na fatia de desenvolvimento os dois ficaram ≈ N1 ou piores.
- R5 (fluxo regional) sintético: não implementado. Replicação e final reais: não executadas.

## 7. Reprodução

- Real: `scripts/executar_comparacao.py --grupo B --fase {treino|validacao}`; `scripts/analisar_comparacao.py --fase {treino|validacao}` → `reports/comparacao/analise_{treino,validacao}/`.
- Sintético: `scripts/executar_metodos_sinteticos.py --fase avaliacao_D`; `scripts/analisar_liquido.py --entrada reports/sintetico_v2/metodos_avaliacao_D` (hash da fase em `docs/PLANO_GULOSO_LIQUIDO.md` §10).
- Integridade das bases: `scripts/verificar_bases_reais.py` (0 problemas após corrigir o verificador).

## 8. Próximo passo sugerido (aguarda decisão)

Congelar o húngaro 60 s e executar a replicação (16–30/09) e a final (01–25/10) uma única vez, para obter o único número com algum grau de independência. Sem isso, o texto do TCC deve dizer "validação", não "teste".
