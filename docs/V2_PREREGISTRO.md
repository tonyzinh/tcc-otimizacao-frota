# Pré-registro da extensão v2 (inferência, controles, oráculo, baselines)

Data do registro: 2026-10-28. Branch `v2-extensoes`. Congelamento da v1: tag `v1-congelada` no commit
`de3865ce08446bf89663f6afc4fd3dbfd14448f3` (árvore `0a5483c1d4edcfa33a44eba5cfdc65142e21d2b6`).
Este arquivo é commitado **antes** de qualquer execução da v2. Depois dele, hipóteses, métricas e critérios
não mudam; qualquer mudança vira "desvio" na seção 10, com data e motivo.

Limite honesto: o carimbo é o histórico do Git local, sem carimbo externo. Ele prova a ordem dos commits para quem
confia no repositório, não para um terceiro (ver M-07 da auditoria). Nenhum desfecho é preferido: nulo confirmado,
efeito invertido e "inconclusivo por falta de poder" são resultados aceitáveis e serão reportados.

## 1. Congelamento da v1 (hashes)

SHA-256 dos arquivos de `reports/tcc_final/` na tag `v1-congelada`:

| Arquivo | SHA-256 |
|---|---|
| tab01_desfechos_tratamento.csv | 18ffba38fab8dba72870ec8bb2ff4b4c4ed89d088bd4c616467523f68142de91 |
| tab02_qualidade.csv | c61c12694788b8d3338cfe39a36a3c2c12f2fbae9e545b69008d04d4809423c3 |
| tab03_demanda_por_hora.csv | a748510df59529bbfde4d52d0bfa312f11740ba4db30892366756284cae6024e |
| tab04_faixas_nao_atendimento.csv | 74abb4ca17274435f596ab8a35ac125b1b85bd5079c059d3deab6f7515a7d886 |
| tab05_frota_descritivo.csv | 3579ca53cea97fefe000cb1b4bd3e30c3e188ac9aba77ca39d88019fbbbaa30a |
| tab06_calibracao_gold.csv | a215cec0d56ae74c2be43dffaa9c709a486d6d91bbb6f1be7554c5d1bce97298 |
| tab07_erros_previsao.csv | f797ea70a11c1961121cb9d87dfc8c8528fabb7540eac0ce02cb5cead16a5d77 |
| tab08_calibracao_simulador.csv | 1f3a003fffff30e7173db1d3bdf7df071440a43d3e193532f5a3c5f66bd1c1bc |
| tab09_ajuste_baseline.csv | e3f04ae4884787c140721c6dd894ed116f4207832c6f105c776e21782d899868 |
| tab10_selecao_parametros_calibracao.csv | e26b06380ae82eaed93850ed9b9e0c7dda865e8a68aeb8bd743d28f1ab536161 |
| tab11_principal.csv | 3b2a0017640650006132eca000e3de084f3134003766a0482eca5f379647d55d |
| tab12_por_faixa_horaria.csv | d14300859bf3208413c1d56f70a03f2bcb38cb77a8020ed4762d573139c11e8a |
| tab13_sensibilidade.csv | 8fe56c6482ed4496105cda4d3348666d58b685388b734e31eb66d5d18d7846e4 |
| tab14_ponto_equilibrio.csv | 57c0879cf0434f87d8b0fa4883fd9945ed78b94d4457ac314d0ad6ef36aa3f80 |
| tab15_escada_informacao.csv | f1d9f370dc7e7c92a79025009f8c902959ff6a789da798ae07b06ffcd0dd3688 |
| tab16_fronteira_pareto.csv | 07fa40d72ba6630e5f1d1e2d3ff2ec4ce8d4647743183008dbe6844b048513f2 |
| tab17_nao_atendidas_por_zona.csv | 532dce1ab204226d0c358ff02f5ce02a7f3bb265cb316f327dd5241d2e5c2763 |
| tab18_previsto_observado_diario.csv | a5d3fb969afa67375edf6de3b4da07d40901e3ca1fb64d13878851ed3e64c0e3 |
| result.json | 53324a67ecd7aab66e5172f9f3d14574c9144404567a6975b4170e97b0ede9e9 |

Linha de base de testes antes da v2: `179 passed, 1 skipped` (`python -m pytest`).

## 2. Regras de conduta

- A v1 não é alterada. Código novo em `src/tcc_frota/v3/`; resultados em `reports/tcc_v2/`; nada sobrescreve `reports/tcc_final/`.
- Sementes fixas, números aleatórios comuns, assinatura SHA-256 das entradas por par (padrão de `v2/sim.py`).
- Dados reais: sem impressão, cópia ou commit de dados brutos, IDs de motorista ou coordenadas individuais. Execuções que
  releiam `data/raw` exigem `TCC_REAL_DATA_AUTHORIZED=YES` e o sal local; sem eles, a fase é suspensa e pedida ao proponente.
- Tudo que use informação de D+1 é rotulado "oráculo" ou "regime B" e nunca é tratado como D+1 estrito.
- Pytest antes e depois de cada fase; toda função nova tem teste.

## 3. Unidade de análise, dados e desfechos

Unidade de análise e de reamostragem: **o dia** (par baseline × proposto no mesmo dia, mundo idêntico por assinatura).
Dados: 16 dias de teste em março/2026 e 15 em setembro/2026 (conferido nos arquivos por dia da v1). Janelas 04–07, 07–10, 04–11;
regimes A, B, C da v1. **Janela e regime primários: 04–11 e regime B** (regime sem informação futura de frota, o mais próximo do D+1 estrito).
Os demais são secundários e entram nas mesmas famílias apenas onde declarado.

Desfechos (por par de dias, depois agregados no período):
- **Primário (H1')**: variação percentual de KM vazio por corrida, `(Σ KM vazio_prop / Σ servidas_prop) / (Σ KM vazio_base / Σ servidas_base) − 1`,
  onde KM vazio = busca + reposicionamento (RN031).
- **Co-primário (H2')**: variação percentual de corridas atendidas, ΔN% = `Σ servidas_prop / Σ servidas_base − 1`.
- Secundários: Δ KM de busca por corrida; KM de reposicionamento por dia; corridas extras por dia; diferença de tempo até o passageiro;
  benefício líquido NB(e*) (seção 5); taxa de execução dos movimentos.

## 4. Hipóteses

- **H1'** (efeito no KM vazio por corrida): a alocação preventiva D+1 reduz o KM vazio por corrida em relação ao baseline.
  H0: efeito ≥ 0. Teste unilateral à esquerda no efeito, mas o relatório mostra o IC bilateral e declara aumento quando ele existir.
- **H2'** (efeito no atendimento): o plano não reduz o atendimento. Margem de não inferioridade: **ΔN% ≥ −1%** (primária; −2% como sensibilidade, desvio D1) (pré-registrada, escolhida
  como tolerância operacional pequena; não é política da empresa). Teste de não inferioridade pelo limite inferior do IC.

## 5. Estatística de decisão (Fase 1)

- IC e p por **bootstrap por dia**. Variantes: (a) iid por dia (v1, comparador); (b) estratificado por dia da semana; (c) em blocos de dias,
  circular e estacionário (`arch.bootstrap`), com blocos de **2, 3 e 7 dias**. Sem `MovingBlockBootstrap`. B = 10 000 reamostragens, sementes fixas.
- **Regra para não escolher o bloco mais conveniente:** o IC de decisão de cada linha é o **mais largo** entre as variantes (b) e (c)
  em todos os tamanhos de bloco. As demais aparecem como sensibilidade.
- **A razão `e` (KM vazio incremental por corrida extra) deixa de ser estatística de decisão.** Substituída por
  `NB(e*) = ΔN_dia − Δ(B+R)_dia / e*`, em corridas-equivalentes por dia, com `e*` ∈ {3, 5, 10, 20, 30, 50, 100} km (desvio D2; além da curva contínua) de KM vazio por corrida extra
  (equivale à razão custo marginal por km / margem por corrida; os valores monetários são privados e não entram). IC por bootstrap por dia.
  Reporta-se também: e pontual somente se o IC de ΔN excluir zero; intervalo de Fieller (se ilimitado, é escrito "ilimitado"); IC percentil
  antigo rotulado "não recomendado".
- Comparação v1 × v2-inferência lado a lado, linha a linha.
- **MDE** (poder 80%, nível 5% bilateral) para ΔN% e Δ KM/corrida% por mês, a partir da variância entre dias.
- Dispersão diária (média, desvio, mín., máx.) e por dia da semana.

## 6. Famílias de testes e correção de multiplicidade

Correção por família com **Holm** e **Romano–Wolf stepdown** (máximo das estatísticas sobre as mesmas reamostragens por dia). Reporta-se p bruto, p-Holm e p-RW.

| Família | Conteúdo | Tamanho |
|---|---|---|
| F1 | H1' em todas as linhas de `tab11_principal` (2 períodos × 3 janelas × 3 regimes × 9 cenários) | 162 |
| F2 | H2' (não inferioridade de ΔN%) nas mesmas 162 linhas | 162 |
| F1p | Subfamília **primária**: janela 04–11, regime B, 9 cenários × 2 períodos | 18 |
| F3 | Fase 3: H1' com oráculo, 9 algoritmos × 2 períodos, janela 04–11 | 18 |
| F4 | Fase 4: H1' de cada política contra cada baseline B0–B4 (9 × 5 × 2), ρ = 1 e conformidade = 1 | 90 |

A família **inferencial confirmatória é F1p** (a mais próxima da pergunta do TCC). F1 completa, F2, F3 e F4 são reportadas com correção, mas
rotuladas explicitamente como **exploratórias**, pois reutilizam os dias de teste já consultados na v1. As varreduras de ρ × conformidade
(Fase 4) e a escada de ruído (Fase 3) são **análises de sensibilidade descritivas**, sem p-valores e sem escolha de ponto favorável.

## 7. Regras de decisão (por linha, no nível 5%)

- **Evidência de redução do KM vazio por corrida:** p-RW (na família da linha) < 0,05 **e** limite superior do IC de decisão < 0 **e** ΔN% com limite inferior ≥ −1% (sensibilidade: −2%).
- **Evidência de aumento:** p-RW < 0,05 para o teste contrário **e** limite inferior do IC de decisão > 0.
- **Inconclusivo:** qualquer outro caso, em particular IC contendo zero. Se o MDE do período for maior que o menor efeito de interesse
  (|ΔKM/corrida| = 5%, ΔN% = 2%), o texto diz "inconclusivo por falta de poder", não "ausência de efeito".
- **Conclusão pré-definida da Fase 2:** se o poder para ΔN ≤ 2% for < 50%, registra-se "o protocolo não distingue o plano do ruído nesse nível; o nulo da v1 é inconclusivo, não evidência de ausência de efeito".
- **Calibração:** se a taxa de falso positivo dos controles negativos ficar fora de [2%, 9%] no nível de 5%, a inferência é declarada mal calibrada e as fases seguintes param.

## 8. Lista completa do que será rodado

- **Algoritmos (9 planejadores da v1, os mesmos parâmetros congelados):** proporcional; regra_limiar; guloso_marginal em três intensidades
  (α = 0,02, 0,1 e 0,5; as demais intensidades de `tab11` permanecem em F1); fluxo de custo mínimo; húngaro; busca local (LNS); recozimento; PSO.
  MILP, NSGA-II, robusto por cenários, MPC, combinado e despacho ficam fora da v2 (limitação declarada); entram só nas linhas de `tab11` já existentes (F1).
- **Baselines (Fase 4):** B0 estacionário; B1 retorno à zona de casa (posição inicial da sessão); B2 movimento observado nas fotos a cada 10 min
  (interpolação linear); B3 cruzeiro local (passeio aleatório em vizinhança 2×2 km); B4 reativo (alocação ótima de livres às origens de pedidos recentes
  não atendidos, `scipy.optimize.linear_sum_assignment`). B4 também é reportado como candidato.
- **Recuperabilidade:** ρ ∈ {0,25; 0,5; 0,75; 1,0}; conformidade ∈ {0,5; 0,75; 1,0}. Grade completa 4 × 3 × 5 baselines, sem seleção de ponto.
- **Cenários:** regimes A/B/C × janelas 04–07/07–10/04–11 × março/setembro, como na v1.
- **Oráculo (Fase 3):** regime O (demanda real de D+1 por zona-hora no lugar da previsão, escala de frota do regime B). Rótulo: "viola o corte; limite superior do que a previsão poderia dar".
  Escada de ruído com WAPE-alvo ≈ 0,1; 0,3; 0,5; 0,7; 0,9. Previsor melhorado (LightGBM Poisson ou GLM binomial negativa): opcional.
- **Controles (Fase 2):** negativos (vazio × vazio; mover cada veículo para onde já está; mesmos movimentos embaralhados entre dias) e positivos
  (k ∈ {0,25%, 0,5%, 1%, 2%, 5%} de ΔN real; cenário sintético "fácil" com pico de demanda numa zona sem veículo). Número de réplicas: 1 000 por efeito, sementes fixas.
- **Fase 5 (distâncias viárias) e Fase 6 (terceiro período):** condicionais (seção 9).

## 9. Condições, ordem e orçamento

Ordem: **0 → 1 → 3 → 4 → 2 → 5 → 6**, para garantir primeiro o mínimo (Fases 0, 1 e 3). Orçamentos declarados: F0 ~0,5 dia; F1 1–2 dias; F3 1–2; F4 3–5; F2 2–3; F5 2–4; F6 só se houver dados.

Dependência de dados: a Fase 1 usa somente as tabelas por dia já derivadas (`reports/runs/tcc_final/*/individual/dias_cenarios.csv`,
`resultados/*_dias.csv`), sem reler `data/raw`. As Fases 3 e 4, e os controles com dados reais da Fase 2, exigem rerodar o simulador e portanto
`TCC_REAL_DATA_AUTHORIZED=YES`. Se a variável não estiver definida, essas fases são suspensas e o fato é registrado, não contornado.
Antes da Fase 4: corrigir e testar a contabilização de KM de reposicionamento que ultrapassa o fim da sessão e a assimetria de posição noturna, e registrar como desvio.

## 10. O que será reportado mesmo se desfavorável

Todos os resultados das famílias acima, inclusive efeitos de sinal contrário, ICs ilimitados, falsos positivos acima do esperado, poder baixo,
linhas não significativas, resultados em que o baseline realista faça o reposicionamento parecer compensar (antes de publicar, repetir com outras sementes e
descartar artefato de contabilização) e fases não executadas por falta de dados ou autorização.

## 11. Desvios conhecidos da v1 (históricos, não reescritos)

Fonte: `reviews/DATA_SCIENCE_AUDIT.md` (25/10/2026; movido para `reports/thesis_audit/DATA_SCIENCE_AUDIT.md` na reorganização de 28/10/2026, conteúdo idêntico) e `docs/DECISOES_TECNICAS.md`.
1. O critério de H1/H2 por IC foi definido depois da execução da v1; o regime B foi corrigido depois de ver o teste (DT015); a bateria e o seletivo vieram depois de um `final-run` já adverso nos mesmos dias de teste; existiu um replay exploratório com efeitos maiores cujos arquivos não existem (M-07).
2. O conjunto de teste da v1 foi consultado muitas vezes; por isso as famílias exploratórias acima não são confirmatórias.
3. O WAPE por zona-hora do modelo usado é 0,88–1,04, equivalente a prever zero (C-02); não houve oráculo de demanda.
4. O texto da v1 diz "13 algoritmos", mas 6 mal moveram alguém; "trade de km por serviço" e "pré-registrado" excedem o que a evidência sustenta (M-07).
5. O p de Holm da v1 usa estatística diferente da do IC e é bilateral para hipótese unilateral (m-01, m-02 da auditoria); Holm cobriu só o KM vazio por corrida.
6. A estatística `e` (razão) tem IC instável quando o IC de ΔN contém zero (substituída nesta v2).
7. Baseline B0 (livres parados) não paga deslocamentos (tratado na Fase 4); há suspeita de reposicionamento que passa do fim da sessão e de assimetria de posição noturna na contabilização (a verificar antes da Fase 4).
8. Distâncias são Haversine × fator, não viárias (lacuna M4); setembro é replicação parcial, não independente.

### Esclarecimentos operacionais (2026-10-28, antes de qualquer execução da v2)

Não alteram hipóteses, desfechos nem critérios; fixam detalhes que o texto acima deixava em aberto, para impedir escolha posterior.
- E1. Entrada da Fase 1: `reports/runs/tcc_final/20261016T013428Z/individual/dias_cenarios.csv` (execução cujo `tab11` tem o mesmo SHA-256 da tag `v1-congelada`). Todo ponto recalculado deve reproduzir a `tab11` da v1 antes de ser usado.
- E2. p bootstrap: estatística centrada, `p = (1 + #{θ*−θ̂ ≤ θ̂}) / (B+1)` para redução (e `≥` para aumento). Para a não inferioridade de ΔN% (H0: ΔN% ≤ −1%; sensibilidade −2%), `p = (1 + #{θ*−θ̂ ≥ θ̂+1}) / (B+1)` com θ em pontos percentuais.
- E3. Romano–Wolf: estatísticas studentizadas por `θ̂/ep*` (erro-padrão do próprio bootstrap), mesmas reamostragens por dia em todas as linhas de um período e reamostragens independentes entre períodos; stepdown unilateral, separado por direção. Como há 8 variantes de bootstrap, **o p de decisão de cada linha é o máximo do p-RW entre as variantes** (mesma lógica do IC mais largo).
- E4. MDE (poder 80%, bilateral 5%) = `(1,96 + 0,8416) × ep`, com `ep` do bootstrap iid por dia e, em separado, da variante mais larga.
- E5. Fieller para `e` usa média das diferenças diárias com t de Student (n−1 g.l.); se o coeficiente quadrático for ≤ 0, o intervalo é escrito "ilimitado".
- E6. ΔKM/corrida% é calculado como razão de somas no período (igual à v1); NB(e*) é média diária.

## 12. Desvios do pré-registro (preencher aqui, nunca apagar)

| Data | Mudança | Motivo |
|---|---|---|
| — | nenhum até o commit deste arquivo | — |
| 2026-10-28 | (D1) Margem de não inferioridade de ΔN% passa de −2% para **−1% (primária)**, mantendo **−2% como sensibilidade**. As regras de decisão da §7 e o teste de H2' usam −1% como critério; −2% é reportado ao lado. | Decisão do proponente, tomada **depois** de ver a Fase 1 (que usou −2%). Na Fase 1 nenhuma linha atingiu "redução", logo a mudança não altera nenhuma decisão; a Fase 1 foi reexecutada com −1% e a versão com −2% permanece no histórico do Git (`2cdba6c`). |
| 2026-10-28 | (D2) Grade de e* ampliada para {3, 5, 10, 20, 30, 50, 100} km por corrida extra, **mais a curva contínua** de NB(e*) em e* de 2 a 200 (passo log). | Decisão do proponente, depois da Fase 1; inclui 3 e 30 por pedido. A grade original é subconjunto da nova. |
| 2026-10-28 | (D3) Autorização de dados: o proponente autorizou o processamento **somente local e somente agregados** (`TCC_REAL_DATA_AUTHORIZED=YES` definida só nos comandos desta sessão). Nenhum bruto, ID ou coordenada individual é impresso, copiado ou commitado; saídas versionadas são agregadas por dia ou mais. | Libera Fases 3, 4 e 2 com dados reais. |
| 2026-10-28 | (D4) Antes da Fase 4, serão corrigidos e testados dois pontos de contabilização: (m1) reposicionamento que ultrapassa o fim da sessão; (m2) assimetria de posição noturna. Detalhes na seção de desvios do `RELATORIO_V2.md` e em `docs/V2_CONTABILIZACAO.md`. | Descrição dada pelo proponente. |
| 2026-10-28 | (D5) Fase 3, escada de ruído: usa **mistura linear** `f = (1−w)·y + w·g` (y = demanda real de D+1, g = previsão do modelo congelado), não ruído multiplicativo. Com isso `WAPE(f) = w·WAPE(g)` exatamente; `w = alvo / WAPE(g)` por período, limitado a 1 (níveis acima do WAPE do modelo real não são extrapolados e são omitidos). | Ruído multiplicativo sobre contagens esparsas não cria demanda em células vazias e não reproduz o erro do modelo real (que é de localização). O WAPE realizado de cada nível é reportado. Calibrar `w` usa a verdade de D+1; isso é parte do desenho "oráculo". |
| 2026-10-28 | (D6) Fase 3, oráculo: demanda do plano = contagens reais de D+1 por (hora, zona) nas zonas que o plano conhece (com centróide de treino); a parcela da demanda real em zonas desconhecidas é reportada e excluída do plano. Planejadores baseados em pseudodias (busca local, recozimento, PSO) recebem **o próprio D+1 real como único cenário**. Frota = regime B. Só janela 04–11, ambos os meses. Algoritmos estocásticos: média de 5 sementes por dia (como na bateria). Algoritmos e parâmetros: os congelados em `resultados/finalistas.json` e `reports/tcc_final/result.json`. | Define o limite superior sem alterar nenhum algoritmo. |
| 2026-10-28 | (D7) Contabilização: a Fase 3 tem como **primária a contabilização da v1** (comparável com a tab11) e reporta a corrigida (m1+m2) como sensibilidade; a **Fase 4 tem a corrigida como primária**. | Preserva a comparação com a v1 e aplica a correção antes da Fase 4, como pedido. |
| 2026-10-28 | (D8) Interpretação de m1/m2 (ver `docs/V2_CONTABILIZACAO.md`): **m1** = reposicionamento em `inicio_turno` que terminaria depois do fim da sessão deixa de ser executado; **m2** = os dois braços passam a pagar o trecho noturno (última posição de D → posição de início de sessão, ou → alvo se movido). Medido: o trecho natural tem mediana 0,7 km e média 3,5 km (mar) e 5,6 km (set) por motorista-dia. | Descrição do proponente; interpretação operacionalizada por mim, sujeita a correção. |
| 2026-10-28 | (D9) Erro de contagem corrigido antes de rodar a Fase 3: os planejadores são **10** (proporcional, limiar, guloso ×3, fluxo, húngaro, busca local, recozimento, PSO), não 9. Logo **F3 = 10 × 2 = 20** e **F4 = 10 × 5 baselines × 2 = 100**. A F1 (162) não muda: refere-se às 9 linhas da tab11. | Erro aritmético no pré-registro; corrigido antes de qualquer execução das Fases 3 e 4. |
| 2026-10-28 | (D10) Revisão da operacionalização de m2, **antes de qualquer execução da Fase 4**. Diagnóstico (placebo: movimentos aleatórios com alvo a <= 3 km da última posição de D, 35% dos motoristas, 5 sementes por dia, janela 04–11, regime B): ΔKM = **+39,1 km/dia (mar) e +35,5 (set)** na contabilização da v1, mas **−20,9 e −31,5** em "pagar nos dois braços" (D8). Logo "pagar nos dois" gera economia espúria: o planejador parte da última posição de D e o mundo põe o baseline no ponto de login (média 3,5–5,6 km de distância). **Nova m2 primária (`start_at_origin`)**: os dois braços começam a sessão na última posição de D, como o regime B pressupõe ("motoristas dormem onde largam"). "Pagar nos dois" fica como sensibilidade rotulada (`empty_km_sim` do mundo `login`). A v1 (mundo `login`, bruta) fica como terceira contabilização. | Descoberta feita na checagem de artefato exigida pelo proponente; a mudança precede os resultados da Fase 4. A Fase 3 rodou antes e traz `empty_km_sim` = "pagar nos dois"; é sensibilidade, com o mesmo rótulo. |
| 2026-10-28 | (D11) Fase 4, parâmetros declarados antes de rodar: B1 = ao ficar livre, volta à posição de início da sessão (no braço do plano, o alvo reposicionado), continua despachável na posição interpolada; B2 = deslocamento observado do próprio motorista entre fotos consecutivas ambas ONLINE (<= 12 min, <= 80 km/h reta), interpolação linear; B3 = passeio aleatório em quadrado de 2×2 km em torno da posição inicial; B4 = a cada 5 min, alocação ótima (`linear_sum_assignment`) de livres às origens de pedidos perdidos nos últimos 15 min, reta <= 3 km. Baseline e plano usam a mesma política Bk; o KM de movimento (`drift_km`) entra no KM vazio dos dois braços. ρ: fração dos não aceitos observados que seria aceita (sorteio por hash, monótono em ρ; calibração do simulador corresponde a ρ = 1). Conformidade: probabilidade por motorista-dia de seguir o movimento (sorteio por hash). B4 como candidato: sem plano, contra Bk, só com ρ = 1, conformidade 1. Placebo de movimentos aleatórios (mesma quantidade, alvos a <= salto máximo da origem) roda em ρ = 1 e conformidade 1; **a decisão de redução na Fase 4 usa a diferença plano − placebo (pareada por dia) além do p-RW contra o baseline**. | Fixa regras antes dos resultados. O planejador não conhece o baseline Bk (limitação). |

| 2026-10-28 | (D12) **Controle positivo e controles negativos sintéticos**, declarados antes de rodar. Mundo 100% sintético (nenhum dado real, nenhuma autorização necessária), em `src/tcc_frota/v3/controle.py`. Geometria: frota ociosa de 12 motoristas agrupada na zona C (jitter 0,2 km), sessão 04–11, regime B (`fim_do_dia`); demanda concentrada na zona H, a 2,0 km em linha reta de C (≈2,6 km por rua, dentro do salto máximo de 3 km): 60 pedidos/dia em H e 10/dia em C, uniformes na janela, corrida de 600 s, 16 dias com sementes fixas. Previsão entregue aos planejadores = a taxa verdadeira (limite superior, como o oráculo); planejadores baseados em cenário recebem 5 pseudodias independentes do mesmo gerador. Sem deriva (baseline B0). Dois cenários: **alcançável** (raio de despacho 4,5 km, velocidade 16,1 km/h, fator 1,30, paciência 180 s, parâmetros de março): o baseline atende H com coleta longa; reposicionar encurta a coleta, logo o KM/corrida *deve* cair; **fora do raio** (raio 1,5 km): o baseline não atende H, logo ΔN *deve* subir. Planejadores: os 10 de `phase3_specs()`, parâmetros congelados. Inferência: o mesmo pipeline da Fase 1 (`analise.analyze`, 8 variantes, Romano–Wolf por família de 10 linhas por cenário). **Critério do controle (fixado agora):** o simulador é considerado capaz de registrar um ganho se, em cada cenário, pelo menos um planejador orientado a demanda (proporcional, guloso, limiar, fluxo ou húngaro) tiver decisão "redução" (alcançável) ou ΔN% com IC inferior > 0 (fora do raio). Se o critério falhar, **parar e investigar bug do simulador antes de qualquer conclusão** (não reescrever o texto). **Controles negativos** no mesmo mundo: (N1) baseline contra baseline (Δ = 0 exato); (N2) movimentos cujo alvo é a posição atual (`already_there`, Δ = 0 exato); (N3) o plano de um dia aplicado a outro dia em que a zona quente muda de lado (H' a 2,0 km de C em direção oposta, 50% dos dias), que não deve produzir "redução". A versão com dados reais de "movimentos embaralhados entre dias" não foi feita; o placebo aleatório da Fase 4 cobre essa função. Saídas: `reports/tcc_v2/fase2_controle_positivo_*.csv`. | Pendência registrada no RELATORIO_V2 §(c) e pedida pelo proponente: sem controle positivo, o nulo poderia ser atribuído a defeito do simulador. |
| 2026-10-28 | (D13) Correção do critério do D12, **antes da execução completa** (a única observação feita foi um teste de fumaça de 1 dia, sem inferência, para checar que o gerador roda). O teste mostrou que o critério "redução de KM/corrida no cenário alcançável" é **inatingível por construção** com movimentos `fim_do_dia`: o reposicionamento economiza no máximo uma coleta por motorista (a primeira) e custa um deslocamento do mesmo tamanho; depois disso o baseline também já está na zona quente (corridas terminam nela). Mudanças: (i) as corridas passam a terminar a ≤ 0,5 km da zona de origem (antes, 3 km); (ii) o cenário **alcançável** vira **controle neutro**: esperado ΔKM/corrida ≈ 0 ou levemente positivo e ΔN ≈ 0 (não é critério de sucesso do simulador, mostra que o ganho não vem sem restrição); (iii) o **critério positivo** passa a valer só para o cenário **fora do raio**: pelo menos um planejador orientado a demanda (proporcional, guloso, limiar, fluxo ou húngaro) com ΔN% com IC inferior > 0 (decisão do IC mais largo) e NB(e\*=30) com IC inferior > 0. O KM/corrida **não** é critério do controle positivo: mover o veículo soma KM vazio ao numerador por construção, justamente o motivo de NB(e\*) ser o desfecho primário. Busca local, recozimento e PSO otimizam KM/corrida com piso de atendimento e podem não se mover; isso é reportado, não corrigido. | Falha de desenho do meu critério D12, vista antes de rodar; corrigida de forma datada e antes dos resultados. |
