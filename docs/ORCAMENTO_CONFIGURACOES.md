# Orçamento de configurações e critérios da bateria (pré-registro)

**Registrado em 16/10/2026, antes de executar qualquer algoritmo novo** (commit deste arquivo anterior a todo resultado de calibração). Toda configuração executada vai para `resultados/registro_configuracoes.csv`. Mudanças posteriores neste arquivo precisam aparecer no histórico do Git e ser justificadas em `docs/BATERIA_ALGORITMOS.md`.

## 1. Protocolo comum

- **Pergunta:** existe um algoritmo de reposicionamento D+1 que reduza o KM vazio total por corrida, (KM de busca + KM de reposicionamento) / corridas atendidas, em relação ao baseline, mantendo o atendimento, em março e em setembro?
- **Mundo, simulador e baseline:** os da v2 (`src/tcc_frota/v2/`), sem alteração: mesmos pedidos, frota, compromissos, raio, paciência, fator rua/reta e velocidade por período; baseline = despacho do motorista livre mais próximo, sem reposicionar. Assinatura SHA-256 conferida em cada par.
- **Janela:** 04–11h. **Regime principal:** B (escala conhecida, plano e execução no fim de D). **Robustez:** regime A (escala prevista, corte às 20h, execução no início do turno). O regime C não entra em nenhuma tabela.
- **Dias:** calibração = 2–15/03 (único lugar onde se escolhem hiperparâmetros); teste = 16–31/03; setembro = 16–30/09 com tudo congelado de março (o simulador de setembro usa a calibração própria de 2–15/09, que não toca nos algoritmos).
- **Previsão:** média do mesmo dia da semana (56 dias, sem Carnaval), congelada da rodada do artigo.
- **Sementes:** 11, 23, 37, 41, 53. O simulador é determinístico; algoritmos determinísticos rodam uma vez por dia (o mesmo plano para qualquer semente, verificado por teste); os estocásticos rodam as 5 sementes e as métricas do dia são a média das sementes antes do pareamento.
- **Simulação no laço:** quando um algoritmo avalia planos no simulador, usa **pseudodias anteriores a D** (pedidos dos dias de treino do mesmo dia da semana, com a frota prevista pelo regime). Metade mais recente dos pseudodias para a busca e a outra metade para aceitar o resultado final (entre plano inicial, plano final e plano vazio). O dia D+1 real nunca é simulado pelo planejador.
- **Regra de escolha do finalista de cada família (calibração, regime B):** menor KM vazio total por corrida (razão agregada nos 14 dias) entre as configurações com corridas ≥ 0,99 × corridas do baseline. Se nenhuma satisfizer o piso, o finalista é a de maior razão de corridas (registrado como "sem configuração viável").
- **Estatística:** unidade = dia; IC 95% por bootstrap pareado de dias (2.000 reamostragens, semente 20261016); teste de permutação por troca de sinal (exato até 16 dias) como robustez. Correção de Holm sobre os p de KM vazio por corrida de **todos** os algoritmos da tabela principal (finalistas e referências), por mês; IC de Bonferroni (nível 1 − 0,05/m) reportado ao lado.

## 2. Critérios de "algoritmo superior" (todos, regime B, nos dois meses)

1. **KM vazio total por corrida menor:** IC 95% da variação inteiramente abaixo de zero em março e em setembro. "Confirmado" exige também p de Holm < 0,05 nos dois meses; sem isso, "indício, não confirmado".
2. **Não inferioridade em atendimento:** limite inferior do IC 95% de corridas_otimizado / corridas_baseline − 1 ≥ −1% (δ = 1%) nos dois meses.
3. **Redução no simulador:** o critério 1 é medido no simulador; a promessa do modelo (objetivo do otimizador) é reportada ao lado e não conta.
4. **Consistência:** proporção de dias com redução do KM vazio por corrida ≥ 50% em cada mês (regime B) **e** estimativa pontual da variação no regime A ≤ 0 nos dois meses.
5. **Tempo:** tempo médio de plano ≤ 900 s por dia e máximo ≤ 3.600 s (o plano é gerado de um dia para o outro).

Métricas reportadas para todos: KM vazio total por corrida (primária) e decomposição B/R por corrida (B + R = total, conferido), corridas atendidas (nível e variação), tempo médio até o passageiro, KM vazio adicional por corrida extra (*e*, ponto de equilíbrio do artigo: margem > *e* × custo por km), fração de reposicionamento "não incremental" que anularia o custo (*f*\* = 1 − (N_p · B_b/N_b − B_p)/R_p; *f*\* > 1 significa que nem com todo o reposicionamento gratuito o total cairia), fração de motoristas movidos, km médio por movimento, tempo de solução por dia.

## 3. Grades por família (máximo de ~12 configurações cada)

Notação: H = salto máximo (km por rua estimado, também limite de execução); λ_z = demanda prevista da zona na janela; N = motoristas do plano.

| Família (seção) | Configurações | Grade | Fixos |
|---|---:|---|---|
| 5.1 Fluxo de custo mínimo | 12 | alvo ∈ {demanda, valor marginal, demanda com teto 2 por zona} × H ∈ {3; 4} × share ∈ {1,0; 1,3} | penalidade de déficit não atendido 1.000 km (preenche todo déficit alcançável) |
| 5.2 Húngaro com posições de espera | 12 | a mesma grade de 5.1 | posições = vagas-alvo nos centróides; motorista que já está na zona preenche a vaga sem mover |
| 5.3 MILP min(B+R) com piso | 12 | cap ∈ {1; 1,5; 3} corridas por veículo × β ∈ {1,00; 0,99} × penalidade por mover μ ∈ {0; 0,5 km} | H = 4 km; raio de busca = raio do simulador do período; limite de 30 s por instância (status e gap registrados) |
| 5.4 Busca local / LNS | 8 | início ∈ {guloso do artigo α = 0,2; finalista 5.1} × orçamento ∈ {100; 300} avaliações × tamanho da reconstrução k ∈ {2; 4} | H = 4 km; operadores: remover, trocar destinos, reconstruir k, acrescentar; aceita só melhoria |
| 5.5 Recozimento simulado | 4 | T₀ ∈ {0,005; 0,02} km/corrida × resfriamento r ∈ {0,98; 0,995} por avaliação | início = guloso α = 0,2; 300 avaliações; H = 4 km; mesma vizinhança do LNS |
| 5.6 NSGA-II | 1 (× 5 sementes) | população 20 × 15 gerações = 300 avaliações de calibração por semente | espaço: peso do alvo w ∈ [0, 1] (demanda ↔ valor marginal), share ∈ [0,3; 1,6], H ∈ [1,5; 6] km, teto por zona ∈ {1…5, sem teto}, km mínimo por movimento ∈ [0; 2]; objetivos: KM vazio total e −corridas nos 14 dias de calibração; finalista pela regra comum aplicada à fronteira |
| 5.7 Robusto por cenários | 6 | S ∈ {5; 10; 20} cenários × objetivo ∈ {valor esperado; CVaR₀,₈} | cap, β e μ do finalista 5.3; cenários = reamostragem com reposição dos dias de treino do mesmo dia da semana; 60 s por instância |
| 5.8 PSO | 4 | probabilidade inicial de ficar ∈ {0,8; 0,95} × inércia w ∈ {0,5; 0,8} | 15 partículas × 20 iterações = 300 avaliações; c₁ = c₂ = 1,5; até 8 destinos por motorista (H = 4 km) |
| 5.9 MPC intradiário (tabela própria) | 4 | horizonte ∈ {1; 2} h × α ∈ {0,2; 0,5} | replanejamento a cada 30 min com motoristas livres; guloso de valor marginal sobre a previsão D+1 das próximas horas; H = 3 km |
| 5.11 Despacho D+0 (tabela própria) | 4 | janela de lote ∈ {30; 60} s × raio ∈ {raio calibrado; raio − 1 km} | atribuição de custo mínimo por lote; combinação com o melhor reposicionamento em tabela própria |
| 5.10 Aprendizado por reforço | 0 | só se sobrar tempo, com *timebox* de 4 h | caso contrário: "não testado" com o motivo |

**Referências obrigatórias** (parâmetros congelados do artigo, sem nova seleção): baseline; guloso de valor marginal α ∈ {0,05; 0,2; 0,5} com ρ = 2,5 km e limite de 3 km; proporcional com limite de 3 km; regra de limiar com θ = 0,1, ρ = 1,5 km e limite de 3 km.

## 4. Conferências finais previstas

`pytest`; recalibração de uma família do zero com os mesmos números; nenhum finalista escolhido com dias de teste ou setembro (o arquivo de finalistas é gravado e commitado antes do teste); B + R = total em toda tabela; segunda checagem independente do resultado principal antes de declará-lo.
