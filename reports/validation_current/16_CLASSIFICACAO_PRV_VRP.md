# 16 — Classificação PRV/VRP e auditoria matemática

Data: 28/10/2026. Base: ramo `v2-extensoes`, commit `abf4c5c` + alterações locais. Somente leitura do código e do manuscrito; nada foi alterado no código, nos experimentos pré-registrados ou no artigo. Fontes inspecionadas: `src/tcc_frota/algoritmos/` (base, alvos, fluxo_custo_minimo, hungaro, milp, busca_local, recozimento, nsga2, pso, guloso_seletivo, mpc, extras, sim_estendido, cenarios), `v2/policy.py`, `v2/sim.py`, `v3/deriva.py`, `optimization/greedy.py`, e `tcc-artigo-latex/sections/*.tex`. **Limite:** li docstrings e trechos centrais, não cada linha dos 21 módulos de `algoritmos/`; `robusto.py`, `v3/sim.py` e `simulation/engine.py` foram apenas conferidos por cabeçalho/docstring. As formulações abaixo vêm das docstrings (que descrevem o código) e dos trechos lidos. Referências: ver seção 14 (parte delas não foi verificada).

## 1. Conclusão executiva

**O TCC não formula nem resolve um PRV/VRP.** O problema efetivamente otimizado é o de **reposicionamento preventivo de veículos (rebalanceamento antecipatório de frota)**: antes do dia D+1, escolher, para cada veículo livre, *uma* zona de destino (ou permanecer), com base em demanda prevista, para reduzir o KM vazio líquido. Nenhum planejador constrói rotas (sequências ordenadas de paradas); nenhum tem variáveis de arco, continuidade de rota, eliminação de subciclos ou precedência coleta-entrega. Algumas peças têm **estruturas relacionadas** (transporte/fluxo de custo mínimo, atribuição, localização-alocação), e o simulador faz **despacho** (veículo livre mais próximo; em D+0, casamento bipartido em lote). Chamar o trabalho de “PRV” seria incorreto; citar o PRV como **contexto** é aceitável e o artigo já o faz de forma correta.

## 2. Definição formal de PRV (referência)

Dado um grafo G=(N,A) com depósito 0, clientes C, custos c_ij e frota de K veículos, o PRV clássico escolhe, para cada veículo, uma **rota** (ciclo que parte e volta ao depósito) de modo que cada cliente seja visitado exatamente uma vez, minimizando o custo total. Formulação de três índices: x_ijk ∈ {0,1} (veículo k percorre i→j), com conservação de fluxo Σ_j x_ijk = Σ_j x_jik, atendimento Σ_k Σ_j x_ijk = 1 (∀ cliente i), saída única do depósito e **eliminação de subciclos** (DFJ ou MTZ). Variantes: CVRP (capacidade Q), VRPTW (janelas [a_i, b_i]), DVRP (pedidos revelados durante a execução, com replanejamento), PDP/DPDP (pares coleta-entrega com precedência), DARP (PDP de pessoas com tempo máximo de viagem e janelas). É NP-difícil (generaliza o TSP; Lenstra e Rinnooy Kan, 1981). *O elemento definidor é a **rota ordenada com várias paradas**.*

## 3. Problema efetivamente resolvido pelo TCC

Conjuntos: V veículos livres do plano (regime A/B), Z zonas H3 r7 com centróide, H horas da janela (p.ex. 04–11h), S pseudodias históricos (anteriores a D). Parâmetros: λ_zh demanda prevista no corte, κ corridas por veículo-hora, d_iz = Haversine(i, z)·fator rua/reta, H_max salto máximo (`max_km`), α/μ/β preços e pisos. **A decisão, em todos os planejadores D+1, é `Moves = {motorista: (lat, lng, km)}`** (`algoritmos/base.py`, contrato `Planner.plan`): um destino por veículo, no máximo um movimento por veículo.

Forma genérica recuperada: min R(plano) + B(plano) − λ_N·N(plano), com destino z(i) ∈ {o_i} ∪ {z : d_iz ≤ H_max}, onde R = Σ_i d_{i,z(i)}·[z(i) ≠ o_i], e B (KM de busca) e N (corridas atendidas) são medidos pelo simulador; o proxy interno é ΔV = min(λ, κ·n). Cada veículo contribui com **um arco** origem→destino: o “percurso” tem um só trecho e não há ordem a otimizar.

Em termos do enunciado: o ótimo é **A (destino)** e **B (atribuição)**; **C (fluxo entre zonas)** só no 5.1; **F (política dependente do tempo)** só no MPC intradiário, fora do D+1; **D (rota completa) e E (sequência coleta/entrega) não ocorrem em nenhum planejador**.

## 4. Classificação algoritmo por algoritmo

| Algoritmo | Problema matemático | PRV? | Evidência no código | Confiança |
|---|---|---|---|---|
| Guloso marginal (α) | Cobertura/localização gulosa: escolhe pares motorista→zona por ΔV−α·km até saldo ≤ 0 (A+B) | Não | `v2/policy.py: marginal_greedy`; adaptador `GulosoMarginal` | Alta |
| Proporcional | Atribuição a vagas proporcionais à demanda, par mais próximo (B) | Não | `v2/policy.py: proportional` | Alta |
| Regra de limiar | Decisão independente por veículo (A), sem interação | Não | `threshold_rule`; docstring “isoladamente” | Alta |
| 5.1 Fluxo de custo mínimo | **Problema de transporte** (LP, matriz TU) entre excedentes e déficits de zona (C); depois conversão heurística em movimentos individuais | Não (estrutura de rebalanceamento/transporte) | docstring de `fluxo_custo_minimo.py`; `solve_transport`, `linprog`; Σf≤s_u, Σf+ω=d_v | Alta |
| 5.2 Húngaro | **Atribuição linear** veículo→vaga (B), vagas fixadas antes | Não | `linear_sum_assignment`; matriz c_ij com coluna “livre” | Alta |
| 5.3 MILP min(B+R) | **Localização-alocação** capacitada: y_ip (posição do veículo i), g_pz (corridas esperadas), Σ_z g_pz ≤ cap·Σ_i y_ip. “cap” é corridas por veículo, **não** carga | Não | docstring de `milp.py` (Σ_p y_ip = 1; piso β·S0); `scipy.optimize.milp` | Alta |
| 5.7 Robusto por cenários | O mesmo MILP com S cenários e CVaR (Rockafellar–Uryasev) | Não | docstring de `milp.py`; `robusto.py` (só cabeçalho) | Média–alta |
| 5.4 LNS | Busca local sobre planos {motorista→zona}; J avaliado **no simulador** (otimização via simulação) | Não; usa técnica comum em PRV | `busca_local.py`: operadores remover/trocar/reconstruir/acrescentar; `zone_plan` | Alta |
| 5.5 Recozimento | Idem, aceitação de Metropolis | Não; idem | `recozimento.py` herda `BuscaLocalLNS` | Alta |
| 5.8 PSO | Mesma representação (índice de destino por veículo) | Não; idem | `pso.py`: x_i ∈ [0, K_i+1), decodificação ⌊x_i⌋ | Alta |
| 5.6 NSGA-II | **Ajuste multiobjetivo de 5 parâmetros** do planejador de fluxo paramétrico; f₁ = KM vazio, f₂ = −corridas | Não | `nsga2.py`: `BOUNDS`, `FluxoParametrico`; o NSGA-II **não** decide por veículo | Alta |
| Guloso seletivo C0–C3 | Guloso por economia líquida estimada por simulação em cenários; “permanecer” padrão (A+B) | Não | `guloso_seletivo.py`: S_s(m) = ΔB − ΔR − λΔN; “cada motorista se move no máximo uma vez” | Alta |
| 5.9 MPC intradiário | Horizonte deslizante: repete o guloso marginal a cada 30 min nos livres (F) | Não; é reposicionamento dinâmico, **fora do D+1** | `mpc.py`: `EPOCH_S = 1800`, mesmo ΔV − α·km | Alta |
| 5.11 Despacho D+0 | **Casamento bipartido de custo mínimo** em lote (pedidos × livres) no simulador (B) | Não (despacho; sem sequências) | `sim_estendido.py`: `dispatch="lote"`, `linear_sum_assignment` | Alta |
| Baselines B1–B4 (deriva) | Movimento exógeno dos livres; não é otimização | Não | `v3/deriva.py` (cabeçalho) | Média |

MILP, LNS, recozimento, NSGA-II e PSO são **técnicas de otimização**; sua presença não indica PRV.

## 5. Simulador × otimizador

- **Planejador (D+1):** decide destino por veículo. Distâncias: Haversine × fator rua/reta calibrado (`with_km`, `reta_km`). Não há grafo viário nem caminho mínimo (roteador/OSRM consta como **PENDENTE** em `docs/REGRAS_NEGOCIO_TCC.md`).
- **Simulador (`v2/sim.py`, cópias em `v3/sim.py` e `sim_estendido.py`):** eventos discretos (sessão, pedido, fim de corrida). Despacha o **veículo livre elegível mais próximo** no instante do pedido, com fila e paciência; executa o reposicionamento na primeira disponibilidade (`inicio_turno`) ou no fim de D (`fim_do_dia`), com não adesão se o deslocamento excede `max_move_km`; soma `pickup_km` e `reposition_km`. A viagem do passageiro é origem→destino em reta × fator.
- Conclusão: o projeto **avalia custos de deslocamento estimados**; não otimiza caminhos nem sequências. A construção de “rota” não ocorre no planejador nem no simulador.

## 6. Qual classe descreve melhor a contribuição

| Enquadramento | Avaliação |
|---|---|
| Roteamento de veículos | **Incorreto** como classificação do problema |
| Reposicionamento de veículos / rebalanceamento preventivo de frota | **Preciso** (principal) |
| Alocação preditiva de frota; otimização de frota orientada à demanda | Preciso, descritivo |
| Atribuição espaço-temporal de veículos | Aceitável |
| Gestão dinâmica de frota | **Enganoso** para o D+1; adequado só ao MPC/D+0 |
| Híbrido despacho + reposicionamento | Só nos experimentos D+0 e D+1+D+0 (fora da tabela principal) |

*Nota sobre “dinâmico”:* o plano D+1 é decidido **uma vez** no corte, com informação fixa; não há revelação sequencial de pedidos nem replanejamento. É um problema **antecipatório/estático sob incerteza de demanda**, não um DVRP no sentido de Psaraftis et al. (2016). O rascunho `docs_antigos/TCC_CAP3_TRABALHOS_RELACIONADOS.md` escreve “antecipatório e dinâmico”; recomenda-se “antecipatório (planejamento prévio sob demanda incerta)”, reservando “dinâmico” para a avaliação por simulação de eventos.

## 7. Comparação com o PRV clássico e variantes

| Propriedade | PRV clássico | TCC implementado | Consequência |
|---|---|---|---|
| Veículos | Frota K | Motoristas livres com posição e turno | Compatível em espírito |
| Clientes | Visitados pela rota | Pedidos fora da decisão; atendidos depois pelo despacho | Decisão desacoplada do atendimento |
| Sequência | Núcleo do problema | Inexistente (um arco por veículo) | Sem espaço combinatório de rotas |
| Horizonte | Um ciclo de rota | Plano D+1 único; MPC intradiário fora do escopo | Não é DVRP |
| Depósito | Obrigatório no PRV clássico | Não há | Sua ausência, sozinha, não excluiria variantes; a ausência de rotas exclui |
| Capacidade | Carga Q | κ / “cap” = corridas por veículo (proxy) | Homônimo, conceito diferente |
| Janelas | [a, b] por cliente | Janela de planejamento 04–11h; paciência na fila | Não são janelas de visita |
| Incerteza | Determinístico, ou revelado (DVRP) | Demanda prevista; avaliação no replay real | Próximo de reposicionamento com previsão |
| Objetivo | Custo de rota/nº de veículos | KM vazio = pickup + reposicionamento, com atendimento como controle | Objetivo próprio da pergunta |
| Entrada | Matriz de custos/grafo | Previsão por zona-hora, frota, simulador calibrado | — |
| Saída | Rotas | Mapa veículo→zona | Não é rota |
| Rede | Grafo viário ou métrico | Haversine × fator | Sem caminho mínimo |
| PDP/DARP | Pares coleta-entrega, precedência, compartilhamento | Uma corrida por vez, coleta e entrega fixas | Rota trivial de 2 paradas, definida pelo pedido e não otimizada |

## 8. Complexidade

- **5.1 Fluxo:** LP de transporte com matriz totalmente unimodular: polinomial e inteiro. Mas a conversão do fluxo em movimentos por veículo é heurística (mais próximo do centróide), então o plano final não é o ótimo do problema original.
- **5.2 Húngaro:** atribuição linear, O(n³), exata para a matriz dada; as vagas (alvos) vêm de heurística (`alvos.targets`).
- **5.3/5.7 MILP:** localização-alocação com binárias e acoplamento por capacidade, da família de localização capacitada, em geral NP-difícil. *Não há prova no repositório; é inferência por analogia, a confirmar.* O HiGHS dá garantia só do **modelo** (status e gap em `info`); o ótimo do modelo não é o do simulador (a docstring registra). Não se deve transferir a NP-dificuldade do PRV ao MILP nem ao fluxo.
- **LNS, recozimento, PSO, NSGA-II:** heurísticas sem garantia; objetivo é caixa-preta de simulação. O repositório mede tempo de plano por dia (C5: PSO ≈ 29 s/dia) para um tamanho de instância, o que não demonstra escalabilidade.
- **Guloso e seletivo:** nenhuma razão de aproximação provada aqui.
- **D+0 em lote:** atribuição polinomial por lote; o problema online completo não tem garantias.
- A incerteza de demanda e o acoplamento temporal (cobertura futura depende do despacho) fazem o problema real maior que cada subproblema; por isso todo plano é avaliado no simulador.

## 9. Auditoria de terminologia (`tcc-artigo-latex` e docs)

| Local | Trecho | Avaliação | Correção sugerida |
|---|---|---|---|
| `sections/02-referencial-teorico.tex` §sec:guloso (≈ l. 132–136) | VRP “exemplo clássico”; “o problema deste trabalho é diferente: não consiste em definir rotas, mas em decidir em qual zona cada veículo livre deve aguardar, por isso as formulações do VRP não são usadas” | **Correto e conservador**; falta nomear a classe | Acrescentar: “trata-se de um problema de reposicionamento de veículos, com sub-estruturas de transporte e atribuição” |
| `sections/02-referencial-teorico.tex` (≈ l. 63–70) | “reposicionamento ou rebalanceamento de frota (vehicle repositioning…)” | Correto | — |
| `sections/03-metodologia.tex` (≈ l. 272–274) | “método húngaro resolve de forma exata a atribuição entre veículos e vagas fixadas, mas não o reposicionamento como um todo” | Correto | — |
| `sections/01-introducao.tex` | “literatura sobre reposicionamento de frotas” | Correto | — |
| `references/referencias.bib` `toth2002` | *The vehicle routing problem*, 2002 | Correto, mas o rascunho do Cap. 3 usa Toth e Vigo (2014, 2.ª ed.) | Unificar edição; citar Dantzig e Ramser (1959) se o PRV for definido |
| `docs_antigos/TCC_CAP3_TRABALHOS_RELACIONADOS.md` §3.1 | “roteamento estático… O problema aqui é antecipatório e dinâmico” | “Dinâmico” impreciso (seção 6) | “antecipatório, decidido uma vez no corte” |
| Idem, Pimentel (2025) | PRV com carregamento 3D e janelas | **Apenas contextual**; a relevância é metodológica (comparação de execuções, *trade-offs*), não do problema | Dizer isso explicitamente |
| `docs/REGRAS_NEGOCIO_TCC.md` l. 149 | “despacho em tempo real e roteamento dinâmico… fora do escopo” | Consistente | — |

Não encontrei no manuscrito: “PRV” como abreviatura, afirmação de que o trabalho resolve VRP, nem comparação com benchmarks de PRV. Não alterei o manuscrito.

## 10. Classificação cientificamente defensável

> Problema de **reposicionamento preventivo de veículos (rebalanceamento antecipatório de frota)** com horizonte D+1, em que a decisão é a atribuição de cada veículo livre a uma zona de destino (ou à permanência), avaliada por simulação de eventos com despacho do veículo mais próximo. Alguns planejadores exploram sub-estruturas de transporte (fluxo de custo mínimo), atribuição (húngaro) e localização-alocação (MILP). Não é um problema de roteamento: não há rotas de várias paradas.

## 11. Redação acadêmica sugerida

1. “Este trabalho trata o reposicionamento preventivo de veículos livres como um problema de atribuição espaço-temporal: para cada veículo, decide-se uma zona de destino com base na demanda prevista até o corte D+1.”
2. “Embora o Problema de Roteamento de Veículos (PRV) seja a referência clássica em otimização de frotas (DANTZIG; RAMSER, 1959; TOTH; VIGO, 2014), ele determina rotas de várias paradas. Aqui cada veículo recebe um único destino; a formulação aproxima-se, portanto, de problemas de transporte e atribuição, e não do PRV.”
3. “Metaheurísticas como busca em vizinhança larga e recozimento simulado, frequentes na literatura de PRV, são usadas aqui apenas como técnicas de busca sobre planos de reposicionamento.”
4. “A avaliação é feita por simulação de eventos discretos com despacho do veículo livre mais próximo; as distâncias são estimativas (Haversine × fator rua/reta), sem cálculo de caminhos em malha viária.”

## 12. Direções futuras (propostas; **não** implementadas, **não** alteram o pré-registro)

| Extensão | Valor | Mudança matemática | Dados | Custo | Cabe no D+1? |
|---|---|---|---|---|---|
| Reposicionamento multi-parada | Baixo a médio: com desigualdade triangular, mover em etapas dificilmente reduz km | x_ijk, continuidade, MTZ/DFJ | posições temporais | Alto (NP-difícil) | Não: muda a pergunta |
| Despacho + reposicionamento conjunto (DPDP) | Médio | Problema online com pares coleta-entrega | log de pedidos com tempo | Alto | Há protótipo D+0/MPC, fora do D+1 |
| Janelas e turnos | Médio | restrições de disponibilidade | escala (parcial no regime B) | Médio | Parcialmente |
| Distância por malha viária | Alto para validade externa | caminhos mínimos | grafo viário | Médio | Sim, como sensibilidade (RN “PENDENTE”) |
| Multi-período | Médio | MDP / horizonte deslizante | — | Alto | Não |

Qualquer uma exigiria novo pré-registro e não deve ser misturada aos resultados existentes.

## 13. Evidência de código

`algoritmos/base.py` (`Moves`, `Planner.plan`); `v2/policy.py` (`marginal_greedy`, `threshold_rule`, `proportional`); `fluxo_custo_minimo.py` (`solve_transport`, `linprog`); `hungaro.py` (`linear_sum_assignment`); `milp.py` (`milp`; y_ip, g_pz); `busca_local.py`, `recozimento.py`, `pso.py` (`zone_plan`, destino por motorista); `nsga2.py` (`BOUNDS` de 5 parâmetros); `guloso_seletivo.py` (“cada motorista se move no máximo uma vez”); `mpc.py` (`EPOCH_S`); `sim_estendido.py` (`dispatch="lote"`); `v2/sim.py` (despacho do mais próximo; `reta_km × road_factor`).

**Busca por indícios de PRV:** `grep -rniE "subtour|MTZ|precedence|depot|dep[oó]sito" src --include=*.py` não retornou nenhuma ocorrência em `src/`. Isso confirma a ausência de depósito, subciclos e precedência no código, mas não substitui a leitura integral dos módulos que só conferi por cabeçalho.

## 14. Referências

**Já no repositório (`tcc-artigo-latex/references/referencias.bib`):** Toth e Vigo (eds.), *The vehicle routing problem*, SIAM, 2002 (`toth2002`); Pavone, Smith, Frazzoli e Rus (2012), *Robotic load balancing for mobility-on-demand systems*, IJRR 31(7), 839–854, doi:10.1177/0278364912444766 (`pavone2012`); Kuhn (1955) (`kuhn1955`); Alonso-Mora et al. (2017) (`alonsomora2017`); Garcia et al. (2024) (`garcia2024`); Cormen et al. (`cormen2012`).

**Citadas de memória, NÃO verificadas nesta sessão (conferir autores, volume, páginas e DOI antes de usar):** Dantzig e Ramser (1959), *The truck dispatching problem*, Management Science 6(1); Lenstra e Rinnooy Kan (1981), *Complexity of vehicle routing and scheduling problems*, Networks 11(2); Toth e Vigo (2014), 2.ª ed., SIAM; Psaraftis, Wen e Kontovas (2016), *Dynamic vehicle routing problems: three decades and counting*, Networks 67(1); Berbeglia, Cordeau e Laporte (2010), *Dynamic pickup and delivery problems*, EJOR 202(1); Cordeau e Laporte (2007), *The dial-a-ride problem*, Annals of Operations Research 153; Zhang e Pavone (2016), IJRR 35; Rockafellar e Uryasev (2000), CVaR; Deb et al. (2002), NSGA-II, IEEE TEVC 6(2); Ahuja, Magnanti e Orlin (1993), *Network Flows*. A documentação do Google OR-Tools (guia de roteamento) não foi consultada.

## 15. Veredito obrigatório

**O TCC implementa realmente o Problema de Roteamento de Veículos (PRV/VRP), uma variante reconhecida, um problema de reposicionamento de veículos ou um problema matemático diferente?**

**Resposta:** O TCC implementa um **problema de reposicionamento de veículos** (rebalanceamento preventivo de frota, horizonte D+1), no qual a decisão é um destino por veículo, avaliado por simulação. **Não** implementa PRV nem variante reconhecida (CVRP, VRPTW, DVRP, DPDP, DARP): não há rotas ordenadas de várias paradas, variáveis de arco, continuidade, subciclos ou precedência coleta-entrega. Sub-componentes têm estrutura de transporte (5.1), atribuição (5.2 e despacho D+0) e localização-alocação (5.3/5.7); LNS, recozimento, PSO e NSGA-II são apenas técnicas de busca. A frase do artigo, de que o problema “não consiste em definir rotas”, está **correta**. Limite da evidência: baseio-me em docstrings e trechos centrais; para fechar com rigor total faltam a leitura integral de `cenarios.py`, `robusto.py` e `v3/deriva.py` e a verificação das referências marcadas como não verificadas.
