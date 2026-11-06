# Auditoria antes da bateria de algoritmos (Fase A)

**Data:** 16/10/2026. **Código auditado:** `7c3b9ff` (árvore limpa). Leitura somente: nada foi alterado nesta fase. O objetivo é saber o que já existe e o que pode ser reaproveitado antes de implementar a bateria de algoritmos de reposicionamento D+1 (`docs_antigos/BATERIA_ALGORITMOS.md`, quando existir).

## 1. Documentos lidos

| Documento | O que importa para a bateria |
|---|---|
| `docs/ESTADO_PROJETO.md` (local, fora do Git) | Rodada final v2 executada (`final-run 20261016T013428Z`, código `69b8647`). H1 rejeitada: nenhuma configuração reduziu o KM vazio por corrida. Suíte: 129 aprovados e 1 pulado na época. |
| `docs/DECISOES_TECNICAS.md` (local) | DT003 (KPI corporativo de KM morto em aberto), DT013 (H1/H2/H3), DT014 (protocolo pré-especificado), DT015 (regime B: plano e execução no fim de D, correção feita depois de ver o teste e documentada), DT010-v2 (pseudonimização com sal; coordenadas com 3 casas da Silver em diante). |
| `docs_antigos/comparacao_algoritmos.md` | Comparação **legada** (setembro, base DT011, janela 07–10h): proporcional, húngaro, *simulated annealing* sobre o objetivo aproximado e guloso avaliado por simulação. Todos pioraram o KM vazio, exceto o guloso simulado (−0,2%, quase não move). Achado: o objetivo aproximado promete de 55 a 89 vezes a economia de busca que o replay entrega. Não usa a v2. |
| `docs_antigos/experimento_real.md` | Desenho legado DT011 (corte às 20h, frota prevista, tolerância de 30 min). Substituído pela v2 para o artigo. |
| `docs/databricks_medalhao.md` (removido em 06/11/2026) | Medalhão v2 no workspace (16 notebooks executados duas vezes); previsão, algoritmos e simulação rodam **só no Python local**, que reproduz a Gold com contagens idênticas. |
| `docs_antigos/resultados_reais.md` | Texto de resultados v2: Tabela 6 (regime B, 04–11h) e discussão: desigualdade triangular, rampa limitada por oferta, A anula o efeito, C não é limite superior. |

## 2. Código existente reaproveitável (`src/tcc_frota/v2/`)

| Peça | Arquivo | Uso na bateria |
|---|---|---|
| Simulador de eventos discretos com fila, paciência, raio de despacho, compromissos externos e reposicionamento (`inicio_turno` ou `fim_do_dia`) | `sim.py` (`simulate`, `SimParams`, `SimRequest`, `SimDriver`) | Avaliador único de todos os algoritmos. Assinatura SHA-256 do mundo garante entradas idênticas entre cenários (RN028). **Determinístico**: não há gerador aleatório. |
| Baseline | `simulate(..., moves=None)` | Despacho do motorista livre mais próximo dentro do raio, sem reposicionar. |
| Guloso de valor marginal S = ΔV − α·d | `policy.marginal_greedy` | Referência obrigatória (α = 0,05; 0,2; 0,5; ρ = 2,5 km; limite 3 km, selecionados na calibração do artigo). |
| Regra proporcional | `policy.proportional` (usa `optimization.alternatives.target_slots`) | Referência (limite 3 km). |
| Regra de limiar | `policy.threshold_rule` | Referência (θ = 0,1; ρ = 1,5 km; limite 3 km). |
| Regimes de informação A/B/C | `fleet.planned_fleet` | A: escala prevista, posição às 20h, execução no início do turno; B: escala conhecida, última posição de D, execução no fim de D; C: oráculo (diagnóstico, **não** será usado como limite superior). |
| Mundo D+1 observado | `fleet.build_world` | Pedidos imediatos de demanda na caixa (inclusive não atendidos), sessões reais, compromissos (agendadas e corridas fora do universo). |
| Entradas do plano no corte | `experiment.Study.plan_inputs` | Previsão por zona H3 r7 × hora (média do mesmo dia da semana, 56 dias, sem Carnaval), centróides das zonas no treino, κ (corridas por motorista-hora, 28 dias), frota do regime. |
| Execução de um dia | `experiment.run_day` | Roda baseline e planos com o mesmo mundo; confere assinatura. |
| Estatística pareada por dia | `stats.compare`, `bootstrap`, `sign_flip_pvalue` | IC 95% por bootstrap de dias (2.000 reamostragens, semente 20261016) e permutação por troca de sinal (exata até 16 dias). Razões agregadas (Σ km / Σ corridas). |
| Orquestração reprodutível | `final_run.final_run` | Calibração do simulador, seleção na calibração de março, teste, sensibilidades, ponto de equilíbrio. |

**Interface de planejador:** não existe uma interface única. Há um despachante por nome (`experiment.make_plan(algoritmo, inputs, params)`) que devolve `policy.Plan` com `moves: dict[motorista, (lat, lon)]`, sem o km por movimento. A bateria cria `Planner.plan(contexto) -> dict[motorista, (lat, lng, km)]` em `src/tcc_frota/algoritmos/base.py`, com adaptadores para os três planejadores existentes, sem mudar o comportamento deles. O teste de regressão compara os adaptadores com as funções originais e, com os dados reais presentes, reproduz os números diários da execução `20261016T013428Z`.

## 3. Dados e parâmetros calibrados

- **Lotes** em `data/raw/` (fora do Git, não serão tocados): `dados_mar2026` (42.578 solicitações, 17.022 históricos, 4.467 fotos da frota, 22.310 sumários), `dados_historico56` (67.561 solicitações de 04/01 a 28/02), `dados_set2026` (35.425; 16.647; 4.326; 21.599) e `dados_historico56_set` (60.419, 07/07 a 31/08). Formato: páginas JSON do Elasticsearch (`hits.hits[]._source`) com manifesto por lote. `prepare_raw` confere manifestos; Silver e Gold locais são reconstruídas em ~30 s.
- **Universo:** 117.309 solicitações imediatas de demanda com origem na caixa da Grande Vitória. As fotos da frota (a cada 10 min) só existem nos lotes de março e setembro.
- **Calibração do simulador (dias 2–15 de cada mês, janela 04–11h), reexecutada nesta auditoria com os mesmos valores do `result.json`:**

| Parâmetro | Março | Setembro | Como foi obtido |
|---|---:|---:|---:|
| Razão rua/reta da busca | 1,301 (n = 466) | 1,384 (n = 369) | medida (`distMotorista` / reta) |
| Velocidade de busca | 16,08 km/h (n = 570) | 16,57 km/h (n = 450) | medida (aceite → chegada) |
| Razão rua/reta e velocidade da viagem | 1,482; 22,3 km/h | 1,499; 23,3 km/h | medidas (`nU_DISTPERCORRIDA`, duração) |
| Raio de despacho | 4,5 km | 4,0 km | ajuste de aceite e busca mediana |
| Paciência | 180 s | 120 s | idem |
| Janela principal | 04–11h | 04–11h | DT014 |

- **Custo computacional medido:** uma simulação de dia × janela 04–11h leva ~16 ms (241 pedidos e 96 motoristas no dia 02/03); `plan_inputs` ~15 ms. Simular dentro do laço de otimização é viável.

## 4. Testes

`python -m pytest`: **130 aprovados, 1 pulado** (pulo preexistente da suíte legada), 2,4 s. Os testes da v2 cobrem regras da Silver, previsão sem vazamento, regimes de frota, simulador (sem ocupação simultânea, compromissos, limite do movimento, assinatura, rastro sem efeito), propriedades dos planejadores (invariante do guloso, limite de distância, determinismo) e estatística.

## 5. Evidência exploratória

A pasta `referencia_exploratoria/` (variants.py, milp.py, run_v1..v4, run_m1/m2) citada no pedido **não existe** neste repositório nem em `Documentos/` (busca até 4 níveis). Os números exploratórios do pedido ficam como orientação **não citável e não reproduzida**. Não bloqueia: as lições (viés de seleção, desigualdade triangular, hipótese da primeira corrida) estão no pedido e entram no desenho.

## 6. Decisões de preferência tomadas (sem bloqueio)

1. **Sementes.** O simulador é determinístico, então as sementes não alteram o mundo; variáveis aleatórias comuns valem por construção. As 5 sementes por dia valem para os algoritmos estocásticos (LNS, recozimento, NSGA-II, PSO, sorteio de cenários); as métricas de cada dia são a média das sementes antes do pareamento. Algoritmos determinísticos rodam uma vez por dia; um teste confirma que sementes diferentes dão o mesmo plano.
2. **Simulação no laço sem vazar D+1.** Os planejadores que avaliam vizinhos "no simulador" (LNS, recozimento, PSO) **nunca** simulam o próprio dia D+1. Eles simulam pseudodias históricos disponíveis no corte: pedidos dos dias de treino do mesmo dia da semana (anteriores a D), com a frota que o regime enxerga (posição e horário previstos). Busca e aceitação usam subconjuntos disjuntos desses dias (o equivalente às "sementes diferentes para aceitar o finalista"). O simulador real do dia só mede o resultado.
3. **NSGA-II** busca parâmetros de um planejador paramétrico (alvo misto demanda/valor marginal, *share*, salto, teto por zona, km mínimo por movimento) nos dias de calibração; a fronteira de Pareto é a da calibração e o finalista sai pela regra da seção 4 do pedido.
4. **Sem dependências novas.** Fluxo de custo mínimo por programação linear de rede com `scipy.optimize.linprog` (HiGHS; a matriz de incidência é totalmente unimodular, então a solução é inteira), MILP com `scipy.optimize.milp` (HiGHS), húngaro com `scipy.optimize.linear_sum_assignment`. NSGA-II, recozimento e PSO são implementações próprias e curtas (pymoo, networkx e OR-Tools não estão instalados).
5. **Setembro:** parâmetros congelados de março; simulador de setembro com a calibração própria já existente (dias 2–15, que não tocam os algoritmos); avaliação nos dias 16–30, como no artigo (15 dias).
6. **Múltiplas comparações:** Holm sobre os p de permutação (KM vazio por corrida, por dia) dos finalistas, por mês; IC de Bonferroni (nível 1 − 0,05/m) ao lado do IC 95%.
7. **Critérios 4 e 5** operacionalizados em `docs_antigos/ORCAMENTO_CONFIGURACOES.md` antes de qualquer execução.

## 7. Dúvidas bloqueantes

Nenhuma. A execução é local, sobre dados já autorizados para processamento local (DT010-v2); nada será enviado ao Databricks nem a serviço externo.
