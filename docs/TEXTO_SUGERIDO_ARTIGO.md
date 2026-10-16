# Texto sugerido para o artigo (bateria de algoritmos)

**Desfecho que se aplica: A — nenhum algoritmo superou o baseline.** O desfecho B fica como modelo, sem números, porque nenhum algoritmo passou nos critérios; não deve ser usado. Números de `docs/BATERIA_ALGORITMOS.md` e `resultados/` (execuções registradas de 16/10/2026). O texto do artigo não foi editado; isto é sugestão.

## Desfecho A — nenhum algoritmo superou o baseline (aplica-se)

**Métodos (parágrafo curto).** Para verificar se o resultado negativo dependia do algoritmo, comparamos treze planejadores D+1 sob o mesmo protocolo: as cinco configurações do artigo e oito famílias de otimização (fluxo de custo mínimo entre zonas H3, atribuição pelo método húngaro, programação inteira mista que minimiza o KM de busca mais o de reposicionamento com piso de atendimento, busca local em vizinhança grande, recozimento simulado, NSGA-II, programação inteira robusta por cenários de demanda e enxame de partículas). Os hiperparâmetros foram escolhidos apenas nos dias 2 a 15 de março, com orçamento de até doze configurações por família, declarado antes da execução, pela regra de menor KM vazio total por corrida com corridas atendidas de, no mínimo, 99% das do baseline. Os finalistas foram congelados e avaliados nos dias 16 a 31 de março e 16 a 30 de setembro, com os mesmos pedidos, frota, simulador e método de distância. Os algoritmos que avaliam planos no simulador usaram apenas dias históricos anteriores ao corte. Um algoritmo seria considerado superior se reduzisse o KM vazio total por corrida com intervalo de confiança de 95% inteiramente abaixo de zero nos dois meses, após correção de Holm, sem perder mais de 1% das corridas.

**Resultados.** Nenhum dos treze algoritmos reduziu o KM vazio total por corrida (busca mais reposicionamento) em relação ao baseline simulado. No regime de escala conhecida, as variações estimadas ficaram entre +0,01% e +28,6% em março e entre +0,01% e +35,8% em setembro, sem nenhum intervalo de confiança abaixo de zero. Todos mantiveram o atendimento dentro da margem de 1%. As famílias de programação matemática estática moveram veículos em excesso quando a capacidade suposta passava de uma corrida por veículo (de +24% a +30% de KM vazio por corrida na calibração) e não moveram nenhum veículo com capacidade de uma corrida. As famílias que avaliam planos no simulador convergiram para planos com pouquíssimos movimentos: o resultado delas ficou entre +0,01% e +1,3% em março e entre +0,01% e +0,6% em setembro. Uma reexecução com novas sementes e um recálculo independente das estatísticas confirmaram esses valores.

**Discussão.** O resultado é coerente com a desigualdade triangular: antecipar o deslocamento não encurta o percurso até o passageiro, e o reposicionamento só reduz o total quando cada corrida adicional custa menos KM vazio que a busca média, de cerca de 2,6 km por corrida. Nas configurações testadas, cada corrida adicional custou de 10 a 115 km vazios. Um despacho em lotes de 30 segundos, avaliado à parte como medida do mesmo dia, reduziu o KM vazio por corrida (−3,9% em março), mas porque deixou de atender 2,4% das corridas. Não se trata, portanto, de uma melhoria. Com os dados e as premissas deste estudo, a alocação preventiva D+1 não reduziu o KM vazio estimado por corrida com nenhum dos algoritmos avaliados.

## Desfecho B — "o algoritmo X superou o baseline" (não se aplica)

> Modelo a preencher apenas se uma execução futura registrada aprovar os cinco critérios: "O algoritmo X reduziu o KM vazio total por corrida em [valor]% (IC 95% [..; ..]) em março e [valor]% (IC 95% [..; ..]) em setembro, com p ajustado por Holm de [..] e [..], sem reduzir as corridas atendidas além de 1% (limite inferior do IC: [..]%). A redução ocorreu em [..] de [..] dias e manteve o sinal no regime de escala prevista. A parcela de busca caiu [..] km por corrida e a de reposicionamento acrescentou [..] km por corrida."

Não preencha com números desta rodada: nenhum algoritmo passou.

---

# Guloso seletivo por economia líquida (16/10/2026)

**Desfecho que se aplica: "C2 não move".** Números de `docs/RESULTADO_SELETIVO.md` e `resultados/seletivo/`. Os outros dois desfechos ficam como modelo e não devem ser usados.

## Desfecho "C2 não move" (aplica-se)

**Métodos.** Como última tentativa, o guloso foi reformulado para adotar "permanecer onde está" como decisão padrão. Um reposicionamento só era aceito se reduzisse o KM vazio da frota inteira (busca evitada menos o próprio deslocamento) em cenários de demanda construídos apenas com dias anteriores ao corte. A economia precisava ser positiva e superior a τ erros padrão em dois conjuntos de dias disjuntos, de seleção e de validação, sem reduzir as corridas esperadas. Doze configurações (salto máximo, número de cenários e τ) foram calibradas em 2 a 15 de março, e o finalista foi congelado antes dos dias de teste.

**Resultados.** Nas condições estudadas, o reposicionamento preventivo não encontrou oportunidades que compensassem o seu custo. Na calibração, nove das doze configurações não executaram nenhum movimento, e as demais executaram, em média, menos de um movimento em 14 dias. O finalista não moveu nenhum motorista nos dias de teste de março e de setembro: as corridas atendidas e o KM vazio total por corrida (busca mais reposicionamento) ficaram idênticos aos do cenário sem reposicionamento. Em cerca de três quartos das decisões, não havia destino com ganho esperado ao alcance; nas demais, a economia líquida simulada não era positiva ou não superava o ruído entre cenários. O guloso de valor marginal do artigo, no mesmo protocolo, aumentou o KM vazio por corrida em 9,88% (março) e 7,83% (setembro).

**Discussão.** O resultado converge com o da bateria de algoritmos: quando o critério de decisão exige economia líquida robusta medida em simulação, a melhor decisão é quase sempre não mover. Isso não demonstra que o reposicionamento nunca compense. Indica que, nesta operação, nesta janela e com um baseline em que os motoristas livres ficam parados, ele não reduz o KM vazio estimado.

## Desfecho "C2 aumenta o KM vazio" (não se aplica)

> Modelo: "O guloso seletivo moveu [n] motoristas e aumentou o KM vazio total por corrida em [x]% (IC 95% [..; ..]) em março e [y]% em setembro; a busca caiu [..] km por corrida e o reposicionamento acrescentou [..] km por corrida."

## Desfecho "C2 reduz o KM vazio" (não se aplica)

> Modelo: "O guloso seletivo reduziu o KM vazio total por corrida em [x]% (IC 95% [..; ..], p de Holm [..]) em março e [y]% em setembro, sem perda de atendimento além de 1%, em [..] de [..] dias."
