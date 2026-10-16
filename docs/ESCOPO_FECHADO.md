# Escopo fechado: três blocos de resultado

**Registrado em 16/10/2026, no commit `ba68324`, antes de executar qualquer um dos blocos.** O estudo avalia se um algoritmo D+1 de reposicionamento de veículos livres reduz o KM vazio por corrida sem reduzir o atendimento. Dados reais de março e setembro de 2026 (PF, imediatas, 04–10h59, região 1, não Prime); só o simulador é simulação. Os blocos usam o que já existe: nenhum algoritmo, configuração de reposicionamento ou C0 novo; simulador, `resultados/` e `finalistas.json` não mudam. **Tudo abaixo é exploratório** (fora do pré-registro de `ORCAMENTO_CONFIGURACOES.md`), exceto o que reutiliza resultados pré-registrados, que são citados como tais.

Calendário (o mesmo do estudo): calibração 2–15/03; teste 16–31/03; setembro 16–30/09 com tudo congelado de março. Cada previsão de um dia usa só dias anteriores ao dia do corte (D = alvo − 1, excluído por estar incompleto às 20h), sem o Carnaval, como no pipeline.

## Bloco 1 — Demanda por zona e hora (exploratório)

- **Unidade:** célula H3 r7 × hora cheia (4 a 10) × dia, a mesma discretização do simulador (`gold.demanda_zona_hora`, `v2/forecast.py`). Demanda = solicitações imediatas de demanda com origem na caixa da Grande Vitória, **atendidas ou não** (o extrato v2 traz as não atendidas com origem). Não inclui agendadas nem demanda suprimida.
- **Modelos:** M0 = média das duas últimas ocorrências do mesmo dia da semana (alvo − 7 e alvo − 14), por célula e hora (linha de base ingênua). M1 = média por célula × hora × tipo de dia (útil: seg–sex; fim de semana: sáb–dom) nos 56 dias anteriores ao corte. M2 = `sklearn.linear_model.PoissonRegressor` com efeitos (one-hot) de célula, hora e dia da semana, treinado nos 56 dias anteriores ao corte; penalidade α ∈ {0,01; 0,1; 1,0} escolhida só na calibração de março pelo menor WAPE agregado e congelada. Referência: o modelo que o simulador usa (média do mesmo dia da semana em 56 dias, `media_dia_semana`).
- **Universo de células por dia:** células vistas nos dias de treino ∪ células com demanda no dia previsto (previsão 0 para as não vistas).
- **Métricas (teste de março e setembro):** WAPE agregado = Σ|ŷ − y| / Σy. Reportado **por hora cheia e agregado em 04–07, 07–10 e 10–11 (só a hora 10), sempre a partir dos erros por hora**, somando os erros absolutos e as solicitações das horas que compõem a faixa, sem refazer a previsão por faixa. O global soma todas as horas. Viés = Σŷ / Σy − 1. Estratos: células com ≥ 1 solicitação por dia em média na janela 04–11h dos dias de treino (definido antes do dia previsto) e as demais. IC 95% por bootstrap de dias (2.000 reamostragens, semente 20261016).
- **Conferência:** o WAPE médio diário por zona-hora do modelo do simulador tem de reproduzir `reports/tcc_final/tab07_erros_previsao.csv` (0,9668 na calibração de março; 0,9566 no teste de março; 0,8816 no teste de setembro). Se não reproduzir, a execução para.
- **Cobertura:** % das solicitações do universo com célula H3.
- **Saídas:** `resultados/demanda/wape.csv`, `tabelas/tab_demanda_wape.tex`, figura previsto × real por hora (um painel por mês).

## Bloco 2 — Pickup e atendimento (exploratório)

- **Cenários:** os já executados no teste, regime B, janela 04–11h: as referências do artigo, os finalistas da bateria (`resultados/finalistas.json`) e C1/C2 do seletivo (`resultados/seletivo/finalistas.json`), com as mesmas sementes. Reexecutados com o rastro (`trace`) do simulador para obter o pickup simulado **por corrida**, sem alterar código nem resultados. Antes de usar o rastro, as somas reexecutadas (corridas e KM de busca por dia) têm de bater com os CSV diários existentes.
- **Corridas extras:** atendidas no cenário e não no baseline (C0) do mesmo dia e semente; comuns: atendidas nos dois. Para extras, comuns (no cenário) e o baseline: média, mediana, p90 e n do pickup simulado (km), por cenário e mês.
- **e e decomposição:** e = ΔKM vazio / Δcorridas, de `resultados/seletivo/km_vazio_por_corrida_extra.csv`; decomposição em ΔB/Δcorridas e ΔR/Δcorridas a partir das somas dos CSV de teste; conferência B + R = total.
- **Dados reais:** decis do pickup realizado (`distMotorista`, metros → km) das solicitações aceitas imediatas de 04–11h nos dias de teste, por mês, com a cobertura (≈ 24% das aceitas têm o campo; ausente não é zero), ao lado dos decis do pickup simulado do C0 nos mesmos dias.
- **Não atendimento por distância:** taxa de não aceite por faixa de distância (em linha reta) ao motorista livre mais próximo na última foto da frota (até 10 min antes do pedido), faixas [0,1), [1,2), [2,3), [3,5), [5,8), ≥ 8 km e "sem livre na foto", janela 04–11h, dias de teste, com a cobertura.
- **Saídas:** `resultados/pickup/` (CSV agregados), `tabelas/tab_pickup_corridas_extras.tex`, histograma sobreposto (extras × comuns).

## Bloco 3 — Ponto de equilíbrio (grade hipotética dos autores)

- **Grade:** seção 3 de `docs/PREMISSAS_E_LIMITACOES.md`: margem ∈ {10, 15, 20, 25, 30} R$; r_km ∈ {0,5; 1,0; 1,5} R$/km; r_min ∈ {0,15; 0,30; 0,45} R$/min; v ∈ {14, 17, 20} km/h; c_v = r_km + r_min × 60 / v; e\* = margem / c_v (135 células). Valores hipotéticos definidos pelos autores; não são da empresa.
- **Comparação:** e de cada cenário (estimativa pontual) contra e\* de cada célula; número de células com e < e\* (compensa) e classificação: em toda a grade / em parte / em nenhuma; "não se aplica" quando o cenário não tem corridas extras. Coluna adicional, exploratória: células em que o limite superior do IC de e fica abaixo de e\*.
- **Saídas:** `tabelas/tab_equilibrio_grade.tex`, `tabelas/tab_equilibrio_cenarios.tex`, `resultados/equilibrio/equilibrio_cenarios.csv`. Os valores de `config/custos_privado.yaml` não entram em nenhum arquivo versionado.

## Regras de contenção

Assunto que não responde H1, H2 ou H3 vai para trabalhos futuros em uma linha. Nenhum algoritmo novo depois do teste. Número fora do pré-registro aparece rotulado como exploratório.
