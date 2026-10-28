# Capítulo 3: Trabalhos relacionados (rascunho, 28/10/2026)

Status: rascunho para revisão. Fontes lidas por mim: Pimentel (2025), Krohling (2025), Garcia, Oliveira e Lacerda (2024), o documento "Conhecimento" do projeto e a página de registro de Kontou, Garikapati e Hou (2020). As demais referências de reposicionamento (Miao, Zhang e Pavone, Alonso-Mora) foram confirmadas só por título e existência; **leia-as antes de citar o que cada uma faz** e confira volume e páginas (marcados com [CONFERIR]).

## 3.1 Roteamento de veículos e heurísticas de otimização

O Problema de Roteamento de Veículos (VRP) foi formulado por Dantzig e Ramser (1959) e é classificado como NP-difícil. Suas variantes (capacidade, janelas de tempo, frota heterogênea, versões dinâmicas) deram origem a uma literatura dominada por heurísticas e metaheurísticas, entre elas busca tabu, recozimento simulado e busca em vizinhança larga adaptativa (ALNS) (ROPKE; PISINGER, 2006; TOTH; VIGO, 2014).

Pimentel (2025) é um exemplo recente e local (UFES). O autor formaliza um VRP com carregamento tridimensional, janelas de tempo e **objetivos hierárquicos** (número de veículos, depois distância, depois tempo de espera) e o resolve com uma heurística de dois estágios: pré-empacotamento por recozimento simulado e roteamento por ALNS. Dois pontos dialogam com este trabalho: (i) a comparação sistemática de configurações com média e desvio-padrão em várias execuções, e não apenas do melhor resultado; (ii) a análise dos *trade-offs* entre objetivos (frota, distância, espera), em que o autor mostra que o melhor resultado e a média podem divergir, o que se relaciona com a troca do desfecho primário deste TCC, de KM vazio por corrida para benefício líquido NB(e\*).

Há uma diferença de natureza que deve ficar explícita. Esses métodos tratam de roteamento **estático**, com demanda conhecida antes da execução. O problema aqui é **antecipatório e dinâmico**: decidir onde posicionar veículos livres antes de a demanda aparecer.

A revisão de Garcia, Oliveira e Lacerda (2024) resume aplicações de IA em rotas de distribuição (algoritmos genéticos, redes neurais, enxames) e é útil como panorama geral. Deve ser usada com cautela: a seleção de artigos usa apenas o Periódicos CAPES, no período 2018–2023, e os resultados dos estudos citados são relatados sem análise crítica (por exemplo, "95,08% de melhoria" atribuída a Zhao, 2023). A revisão também cita um artigo marcado como **retratado** (Ma e Wang, 2022), que não deve ser citado neste trabalho.

## 3.2 Reposicionamento de frota e redução de KM vazio

Em mobilidade sob demanda, o KM vazio (deadheading) é o deslocamento de veículos sem passageiro. A literatura propõe duas famílias de estratégias: orientar o motorista a **esperar** onde a demanda é esperada, em vez de circular, e **reposicionar** veículos livres entre regiões antes que a demanda surja.

* Kontou, Garikapati e Hou (2020) usam um modelo de aprendizado de máquina para prever a demanda futura (por hora e por 10 minutos) e dois algoritmos, um que orienta motoristas a aguardar a próxima corrida e outro que pareia motoristas e passageiros para minimizar a distância vazia. Com dados do RideAustin (Austin) e da DiDi (Chengdu), reportam reduções de deadheading por corrida de **68% a 82%** e **53% a 60%**, respectivamente, **sob a hipótese de disponibilidade irrestrita de estacionamento de curto prazo**.
* Miao et al. (2016) formulam o despacho de táxis com controle por horizonte retrocedente (receding horizon) usando dados de sensoriamento em tempo real. [CONFERIR o que o artigo reporta sobre KM vazio.]
* Zhang e Pavone (2016) analisam, por teoria de filas, o rebalanceamento de sistemas de mobilidade sob demanda robotizados. [CONFERIR o resultado central e as hipóteses.]
* Alonso-Mora et al. (2017) propõem o pareamento dinâmico de viagens e veículos com compartilhamento de alta capacidade, com uma extensão de rebalanceamento. [CONFERIR.]

## 3.3 Previsão de posição e de demanda

Prever **onde** os veículos e a demanda estarão é um insumo dos planejadores antecipatórios. Krohling (2025) propõe o TRAJES, um arcabouço para gerar e avaliar modelos de predição de trajetórias veiculares apenas com dados de geolocalização. Usa bases de táxis do Porto e de São Francisco, modelos LSTM e transformer (PatchTST) e a métrica *Hit Rate Accuracy*, que avalia o acerto por células de um grid sobre a cidade. A revisão do autor mostra que a maior parte dos trabalhos se restringe a rodovias ou pequenas regiões urbanas e que predições de longo prazo são mais difíceis que as de curto prazo.

Para este TCC, o trabalho é relevante em dois sentidos. A avaliação por **células** é análoga à previsão por **zona e hora** usada aqui. E a dificuldade de previsão de longo prazo é coerente com o WAPE de 0,86 a 0,90 observado nos dias de teste [`RELATORIO_V2.md` §(e)]. Diferença importante: Krohling prevê trajetórias individuais; este trabalho prevê demanda agregada por zona.

## 3.4 Lacuna e posicionamento deste trabalho

| Eixo | Literatura revisada | Este trabalho |
|---|---|---|
| Problema | Roteamento estático (Pimentel; Garcia et al.) ou reposicionamento com ganho reportado (Kontou et al.) | Reposicionamento D+1 em frota controlada, com custo do deslocamento contabilizado |
| Desfecho | Distância total, número de veículos; deadheading por corrida | Benefício líquido NB(e\*) e KM vazio por corrida (secundário) |
| Comparação | Em geral um baseline estacionário ou sem reposicionamento | Cinco baselines com deriva, placebo de movimentos aleatórios e controle positivo |
| Inferência | Melhor resultado ou média de execuções | Bootstrap por dia, correção de múltiplos testes, poder e MDE |
| Resultado | Ganhos relevantes sob premissas favoráveis | Nenhum planejador reduz o KM vazio por corrida; o aumento é robusto |

**Sobre a diferença em relação a 53–82%.** Kontou et al. (2020) reportam reduções grandes sob estacionamento de curto prazo irrestrito e informação de demanda futura. As premissas aqui são diferentes: o motorista continua despachável, paga o KM de deriva e do reposicionamento, e a informação de demanda é histórica (o oráculo é apenas um limite superior). Não afirmo a causa da diferença. O teste que a decidiria é um baseline que contabilize só o KM com passageiro e estacione sem custo, listado como trabalho futuro.

**Lacuna.** Não encontrei, nas fontes lidas, uma avaliação que combine baselines com deriva realista, placebo, controle positivo e correção para múltiplos testes aplicada ao reposicionamento de frota. Antes de afirmar essa lacuna no texto final, é preciso uma busca sistemática (ver nota abaixo).

## Referências (ABNT, a conferir)

ALONSO-MORA, J.; SAMARANAYAKE, S.; WALLAR, A.; FRAZZOLI, E.; RUS, D. On-demand high-capacity ride-sharing via dynamic trip-vehicle assignment. **Proceedings of the National Academy of Sciences**, v. 114, n. 3, p. 462–467, 2017. [CONFERIR n. e páginas]

DANTZIG, G. B.; RAMSER, J. H. The truck dispatching problem. **Management Science**, v. 6, n. 1, p. 80–91, 1959.

GARCIA, H. B.; OLIVEIRA, F. C.; LACERDA, P. S. P. Aplicação de algoritmos de Inteligência Artificial na otimização de rotas de distribuição na Engenharia de Produção. **Plural – Revista Acadêmica**, v. 1, n. 5, maio 2024. ISSN 2965-5285. [CONFERIR nomes completos e paginação]

KONTOU, E.; GARIKAPATI, V.; HOU, Y. Reducing ridesourcing empty vehicle travel with future travel demand prediction. **Transportation Research Part C: Emerging Technologies**, v. 121, art. 102826, 2020. DOI: 10.1016/j.trc.2020.102826.

KROHLING, B. A. **TRAJES: um arcabouço para geração e avaliação de modelos de predição de trajetórias veiculares**. 2025. Dissertação (Mestrado em Informática) – Universidade Federal do Espírito Santo, Vitória, 2025. [CONFERIR ano: a capa indica 2025 e a ficha catalográfica 2024]

MIAO, F. et al. Taxi dispatch with real-time sensing data in metropolitan areas: a receding horizon control approach. **IEEE Transactions on Automation Science and Engineering**, v. 13, n. 2, p. 463–478, 2016. [CONFERIR]

PIMENTEL, W. P. **Heurística híbrida para o problema de roteamento de veículos com carregamento tridimensional, janelas de tempo e objetivos hierárquicos**. 2025. Dissertação (Mestrado em Informática) – Universidade Federal do Espírito Santo, Vitória, 2025.

ROPKE, S.; PISINGER, D. An adaptive large neighborhood search heuristic for the pickup and delivery problem with time windows. **Transportation Science**, v. 40, p. 455–472, 2006.

TOTH, P.; VIGO, D. **Vehicle routing: problems, methods, and applications**. 2. ed. Philadelphia: SIAM, 2014.

ZHANG, R.; PAVONE, M. Control of robotic mobility-on-demand systems: a queueing-theoretical perspective. **The International Journal of Robotics Research**, v. 35, n. 1–3, p. 186–203, 2016. [CONFERIR]

## Notas de uso das fontes

1. **Relevância das fontes do projeto.** Pimentel (2025), Garcia et al. (2024) e Krohling (2025) tratam de roteamento estático, panorama de IA em rotas e predição de trajetórias, respectivamente. Nenhuma trata de reposicionamento de frota em mobilidade sob demanda. Servem para contexto, métodos e previsão, não como base do argumento central. O argumento central depende de Kontou et al. (2020) e de outras fontes de reposicionamento que ainda faltam.
2. **Artigo retratado.** Não citar Ma e Wang (2022); o próprio título aparece como "Retracted" na revisão de Garcia et al.
3. **Documento "Conhecimento".** É uma compilação feita por busca na web, com estatísticas sem verificação (por exemplo, "ILS superior ao GRASP em 98% das instâncias" e "transporte representa 40–70% do custo logístico"). Cite as fontes primárias, não o documento.
4. **Busca sistemática pendente.** Para sustentar a afirmação de lacuna, faça uma busca registrada (bases, termos, período, critérios) sobre "vehicle repositioning", "empty vehicle travel" e "deadheading" em ride-hailing e táxis, e inclua os resultados nesta seção.
