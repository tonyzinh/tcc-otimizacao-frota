# Metodologia

## Pergunta e hipótese

A atribuição **conjunta** de pedidos a veículos em lotes de 60 s (algoritmo Húngaro) reduz o km vazio (aproximação do veículo ao passageiro) em relação ao despacho pelo mais próximo livre, **sem piorar o atendimento**? É uma hipótese a testar; resultado nulo ou negativo é resultado. Escopo: simulação com km **estimado**; não mede efeito operacional.

## Políticas

| Id | Política | Papel |
|---|---|---|
| A | mais próximo livre, despacho imediato | referência (baseline simplificado calibrado; **não** é a operação manual) |
| B | mais próximo livre, lotes de 60 s (FIFO por chegada, id) | isola o efeito do lote |
| C | Húngaro, lotes de 60 s | método principal |

Contraste principal **C × A**; complementar **C × B** (efeito da atribuição com o lote fixo) e B × A (efeito do lote).

## Formulação do lote (política C)

Em cada instante `t` múltiplo de 60 s: pedidos pendentes `R_t` (já chegados, não atendidos, não expirados), veículos `V_t` online; par `(r, v)` **elegível** se o veículo está livre, sem conflito de compromisso e a distância de aproximação está no raio. Objetivo lexicográfico: (1) maximizar pares; (2) minimizar a soma das distâncias. Matriz ampliada com colunas "não atribuído" de custo 0 e custo `c − M` nos pares elegíveis (M maior que qualquer soma); custo inteiro (metros × 10⁵ + índice) para desempate determinístico. Solver: Kuhn–Munkres com potenciais (implementação própria, O(n²m)); `scipy.optimize.linear_sum_assignment` é só oráculo de teste. O ótimo é **do lote**, não do dia.

## Simulador

Eventos discretos; jornadas e compromissos externos respeitados; sem teletransporte; sem atendimento duplicado; a política vê só o estado do instante. Espera do pedido = do chegada até o embarque (inclui a espera até a fronteira do lote e o deslocamento de aproximação) e é calculada **só entre os atendidos**: políticas diferentes atendem conjuntos diferentes, então comparações de espera podem refletir seleção e não são melhoria garantida.

Linha **histórica**: distância = Haversine × 1,3012, 16,079 km/h, raio 4,5 km em linha reta, paciência 180 s (parâmetros da calibração de março, não reajustados). Sem roteamento viário: pontes e a baía **não** são modeladas e a aproximação pode ser subestimada onde o caminho real exige desvio.

Linha **sintética**: caminho mínimo (Dijkstra) sobre a rede viária OpenStreetMap (Overpass, instantâneo de 08/11/2026, API 0.7.62.11, ODbL); 25 km/h; raio de 8 km por via; paciência 600 s; 100 veículos; jornadas de 9 h; pontos H3 res. 8 e zonas res. 7; recorte a até 20 km por via do Centro de Vitória. Verificações estruturais (testes): o grafo do recorte é conexo (368 pontos, distâncias finitas), a distância por via nunca é menor que a reta, e a razão via/reta ilha–continente (Vitória→Vila Velha, mediana 1,45) é comparável à dentro do mesmo município (Vila Velha, 1,34), de modo que há travessia(s) mapeada(s) (o arquivo tem 521 trechos com `bridge=*`, entre eles a Terceira Ponte, a Segunda Ponte, a Ponte do Príncipe e a Ponte Florentino Avidos). **Não** se verificou ponte a ponte nem se validaram tempos de percurso; congestionamento e pedágio não são modelados.

## Critérios de serviço

* Histórico: **E1** nenhuma violação de compromisso causada pela política; **E2** atendidos(C) ≥ atendidos(referência), sem tolerância; **E3** P90 agregado da espera ≤ o da referência.
* Sintético: razão média pareada de atendidos ≥ 0,995 **e** razão das médias de P90 ≤ 1,05. É **mais frouxo** que E2 (tolera 0,5% de perda média por semente). Os critérios não foram alterados retroativamente.

## Estatística

O **dia** (histórico) ou a **semente** (sintético) é a unidade. Histórico: IC95% por bootstrap de blocos móveis de 7 dias (10.000 reamostragens, semente 20261108). Sintético: IC95% percentil por bootstrap de sementes; Holm nos testes confirmatórios (política em lote × A nos cenários S1–S5; no resumo congelado são 20 testes, pois entram as variantes de lote de 30 s e o método de fluxo preservado nos dados; p mínimo ajustado 0,002 = 20 × 1/10.000). Um IC que inclui zero **não** é equivalência.

## Resultados vigentes (arquivos citáveis)

| Resultado | Arquivo |
|---|---|
| Setembro/outubro, totais e contrastes | `reports/atribuicao_final/analise/` |
| Congelamento, hashes | `docs/CONGELAMENTO_ATRIBUICAO_60S.md`, `reports/atribuicao_final/CONGELAMENTO.json` |
| Verificação de otimalidade (2.628 lotes) | `reports/atribuicao_final/verificacoes_desenvolvimento.json` |
| Sintético | `reports/sintetico_v2/metodos_avaliacao_D/analise/resumo_contrastes.csv` |

C × A em outubro: −5,04% de km vazio, mas **−85 atendidos** (14.466 vs 14.551 de 23.523): −0,36 p.p. do universo elegível, ≈ −0,58% dos atendidos de A; **E2 não foi cumprido**.

## Limitações

Simulação, não operação; km estimado; baseline simplificado; disponibilidade reconstruída retrospectivamente (jornada realizada); parâmetros herdados de março; atendimento simulado de 62–66%; uma empresa e região; sem deduplicação de tentativas; ótimo por lote ≠ ótimo diário; sintético não independente entre cenários e com sementes finais já vistas.
