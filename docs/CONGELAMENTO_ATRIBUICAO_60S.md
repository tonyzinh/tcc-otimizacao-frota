# Congelamento da atribuição conjunta com janela de 60 s (09/11/2026)

Escrito **antes** de qualquer execução em 16–30/09 e 01–25/10 (nenhuma política foi simulada nesses dias; só foram contadas linhas e conferidos manifestos). Autorização do proprietário em 09/11/2026: congelar e executar replicação e avaliação final; **não** alterar o TCC; **não** fazer commit nem stage.

## 1. Identidade do método (verificação pedida)

- **C** é o algoritmo **húngaro** (Kuhn–Munkres com potenciais e caminho aumentante, O(n²m)), implementação própria `comparacao/despacho.py::kuhn_munkres`, com formulação lexicográfica: maximiza o número de pedidos atendidos no lote e, entre as soluções com esse máximo, minimiza a soma das distâncias de busca (custo inteiro em metros + índice para desempate determinístico). O nome está correto. `scipy.optimize.linear_sum_assignment` (busca de caminho aumentante, estilo Jonker–Volgenant) **não** é usado como política; só como oráculo.
- Verificação (`scripts/verificar_despacho_lote.py`, 4 dias de desenvolvimento: 10/02, 04/03, 17/03, 25/03): em **2.628 lotes** o conjunto devolvido tem o mesmo número de pares e a mesma soma de distâncias (resolução de 1 m) que o ótimo do oráculo; diferença máxima na soma exata: 0,0015 km, só por arredondamento.
- O fluxo de custo mínimo (não usado aqui) também atinge o ótimo, mas em 37 de 1.291 lotes (2 dias) devolveu **outro** conjunto de pares de custo igual (ótimos alternativos); por isso Húngaro e fluxo não são sempre idênticos nos agregados. Isso não é erro de nenhum dos dois.

## 2. Verificações em dados de desenvolvimento (resultado: todas aprovadas)

`reports/atribuicao_final/verificacoes_desenvolvimento.json` (agregado; sem IDs nem coordenadas):

| Verificação | Resultado |
|---|---|
| Todos os pedidos do lote já chegaram na decisão (`r.t ≤ t`) | sim, em todos os lotes de B e C |
| Decisões só em múltiplos de 60 s; despachos de B e C só em instantes de lote | sim |
| Espera = (instante do despacho − chegada) + tempo de deslocamento até a origem | confere com o rastro de eventos (atraso médio do lote: B 45 s, C 40 s) |
| Candidatos elegíveis no instante (online, livre, raio em **linha reta** ≤ 4,5 km, sem conflito de compromisso) | sim (a elegibilidade é calculada pelo simulador com o estado do instante; o simulador aborta se a política devolver par inelegível ou duplicado) |
| Pares únicos por pedido e por motorista | sim |
| Nenhum despacho antes da chegada; busca dentro do raio | sim |
| Informação futura | nenhuma: a política recebe apenas pedidos já chegados e candidatos do instante |
| Sobreposição de serviços por motorista | 0 nas três políticas |
| Violações de compromisso causadas pela política | 0 nas três; "entrada inconsistente" (posição inicial incompatível, independe da política): A 4, B 4, C 5 nos 4 dias; reportado por período |
| Entradas idênticas (assinatura SHA-256 por dia) entre A, B e C | sim |
| B = FIFO independente reimplementado no teste | sim |

Observação: o raio de despacho (4,5 km) é medido em linha reta; o km de busca é reta × fator 1,3012. Como o fator é constante, minimizar a soma da distância reta é equivalente a minimizar o km de busca.

## 3. Políticas e ordem de B

| Código | Política | Implementação |
|---|---|---|
| A | mais próximo livre, despacho imediato | `B0_imediato_atual` (motorista elegível mais próximo no instante do pedido; fila FIFO se nenhum) |
| B | mais próximo livre, lotes de 60 s | `B_lote60s_guloso_fifo`: pedidos pendentes ordenados por **(instante de chegada, id)**, cada um recebe o motorista elegível mais próximo ainda livre. Essa ordem é a mesma do despacho atual e foi definida antes de qualquer resultado; não depende de C |
| C | atribuição conjunta, lotes de 60 s | `B_lote60s_hungaro` |

Lotes: instantes múltiplos de 60 s desde 00:00; pedido espera até o próximo instante; motorista liberado espera o próximo lote; paciência de 180 s; cancelamento e fila como no simulador comum. A e B/C compartilham pedidos, frota, jornadas, compromissos, parâmetros (raio 4,5 km; 16,079 km/h; fator 1,3012; paciência 180 s, herdados da calibração de março), posição inicial `primeira_posicao_observada` e cenário J.

**Contraste principal (fixado antes dos resultados): C × A**, em cada período. Complementares: **C × B** (isola a atribuição conjunta do efeito do lote) e **B × A**. Nenhum outro contraste é calculado.

## 4. Origem da escolha (o que foi consultado)

- **Janelas experimentadas:** 30 s e 60 s (candidatas fixadas em `docs/PLANO_COMPARACAO_ALGORITMOS.md`, escrito em 08/11 às 10:49, antes da primeira execução do grupo B às 10:50).
- **Como o 60 s foi escolhido:** regra do plano (§5–6), no **treino real 01/02–15/03 (43 dias)**: entre as políticas elegíveis (E1–E3) com IC95% de bloco superior < 0, a de menor km foi o fluxo de 60 s (−5,44%); o desempate por simplicidade (IC da diferença pareada contra o Húngaro de 60 s contém 0: −0,17; 17,09 km/dia) escolheu o **Húngaro de 60 s** (−5,02%). O Húngaro de 30 s (−4,02%) ficou pior que o fluxo de 60 s com IC excluindo 0 (13,4; 49,5), logo 60 s > 30 s. Fluxo × Húngaro: preferiu-se o Húngaro por simplicidade e tempo (3 s × 24 s por 16 dias).
- **O que mais foi visto antes desta decisão de adotá-lo:**
  - Validação real 16–31/03 (16 dias): confirmou 60 s e Húngaro (−4,76%; IC −139 a −70 km/dia; +111 atendidos). A validação não participou da escolha de W; participou da decisão do proprietário de adotá-lo.
  - Sintético, fatia de desenvolvimento S1–S5 × sementes 101–110 (D com Húngaro/fluxo ≈ −6,4%).
  - Sintético, avaliação final 22 cenários × sementes **20001–20040**: executada uma vez, conforme o plano, com as quatro políticas D (30 s e 60 s) como confirmatórias, **mas seus resultados foram vistos antes da decisão de adoção**. Elas não escolheram W nem o algoritmo (a escolha já vinha do treino real), porém não podem ser descritas como evidência independente da decisão de adotar. **Reclassificação:** evidência sintética de D = confirmatória do protocolo, **já conhecida na adoção**.
  - Sementes 9001–9040: não usadas para D.
- **Períodos já examinados para atribuição:** 01/02–15/03 e 16–31/03. **Nunca examinados:** 16–30/09 e 01–25/10.
- Reposicionamento (grupo R) foi estudado nos mesmos períodos de fev–mar; resultado negativo preservado (§9).

## 5. Independência dos períodos de setembro e outubro

São futuros em relação ao período de seleção (**out-of-time**), nunca simulados sob nenhuma política antes desta execução, e o método **não** será ajustado entre eles. Limites da independência: mesma empresa, região e simulador; parâmetros de simulação herdados de março; o cadastro de veículos é uma única foto (extraída em 08/11/2026) usada para todos os dias; o autor viu fev–mar. Setembro e outubro respondem "o resultado se repete em outros meses?", não "o resultado vale na operação real". Se surgir erro de implementação que exija correção, será registrado e a independência reavaliada; não se repete e seleciona a melhor execução.

## 6. Dias, entradas e elegibilidade

Regra fixada aqui antes de executar (igual à do desenvolvimento, sem o critério de 28 dias de histórico, que existia só para o planejador D+1): entidades do dia presentes (`solicitacao`, `jornada_motorista`, `compromissos_externos`, `veiculo_condutor`, `posicao_ofertas`) e cadastro `veiculo`; ≥ 300 instantes de posição; ≥ 200 pedidos TempoReal. Resultado, só com contagens (`reports/atribuicao_final/elegibilidade_*.json`): **replicação 15/15 dias elegíveis; final 25/25**; mínimo de 702 instantes por dia e de 459 pedidos. Nenhum dado ausente foi substituído. `telemetria_cobli` só existe em fev–mar, mas não é usada por esta linha. Pedidos agendados ficam fora (recorte por tipo, contado); cancelados permanecem como demanda; novas tentativas do mesmo passageiro **não** foram deduplicadas (limitação).

## 7. Critérios de serviço, métricas e estatística (fixados)

- E1 nenhuma violação de compromisso causada pela política; E2 atendidos(política) ≥ atendidos(referência) no período; E3 P90 agregado da espera ≤ o da referência. Sem SLA da empresa: critérios experimentais.
- Métricas por política e período: km vazio absoluto (busca; sem reposicionamento nesta linha), pedidos elegíveis, atendidos, não atendidos, atendimento em %, km por atendido, espera média e P90 dos atendidos, violações, tempo computacional (inclui a simulação do dia).
- Contrastes: variação absoluta e percentual (negativo = redução), diferença pareada por dia com IC95% por bootstrap de blocos móveis de 7 dias (10.000; semente 20261108), dias com melhora/piora, diferença de atendidos e de pontos percentuais, diferença de espera média e P90.
- Classe: `reducao_com_servico_preservado` se limite superior do IC < 0 e E1–E3.
- Períodos reportados separadamente; **nunca somados**, nem com o sintético.

## 8. Procedimento e falhas

`scripts/executar_atribuicao_final.py --congelar` grava `reports/atribuicao_final/CONGELAMENTO.json`; `--executar` roda setembro e depois outubro, só com as três políticas, e recusa se o hash do código mudou, se não houver congelamento ou sem `TCC_COMPARACAO_VENCEDOR_CONGELADO=SIM`. Execução idempotente por dia; falhas técnicas vão para `reports/atribuicao_final/falhas.jsonl` e o dia é retomado sem alteração de código; não há reexecução seletiva. Saídas: `reports/atribuicao_final/execucao/`; análise: `scripts/analisar_atribuicao_final.py` → `reports/atribuicao_final/analise/`.

## 9. O que esta avaliação não responde

- É **simulação com entradas históricas**, não economia observada na empresa. Km é estimado (reta × fator), não odômetro.
- A referência A é um despacho "mais próximo livre" simples, **não** uma reprodução validada da operação manual; a comparação mede a diferença entre políticas de despacho **sob este simulador**, não a diferença entre a operação real e o húngaro.
- Hipótese de reposicionamento D+1: **resultado negativo preservado** (nenhum método de reposicionamento reduziu km vazio com evidência nos períodos de desenvolvimento, e o guloso original piorou o km no sintético). O resultado de despacho não o invalida; são perguntas diferentes (posicionar antes × atribuir durante a operação).
- Adotar a atribuição muda o escopo do TCC (decisão durante a operação, com pedidos já chegados). Isso depende de decisão do proprietário.

## 10. Retrato congelado

Preenchido ao final (após testes, lint e formatação): ver `reports/atribuicao_final/CONGELAMENTO.json` e a seção abaixo.

**Congelado em 09/11/2026** (antes de executar setembro/outubro; `reports/atribuicao_final/CONGELAMENTO.json`):
- Código: SHA-256 de 151 arquivos (`src/tcc_frota/**/*.py` + scripts e configs da avaliação) = `480a98a15cc88ea4e502dc72492c2472ecd31a794d74490985d42ea9d8e93f87`; commit base `3e77cb9e013918b9a4325dd9e43acdd5fc0ec659`; `git diff HEAD` = `2193740d9edc4a248cce492481376644bf9dd11efea7bf815e03477218d70578` (alterações não commitadas por instrução). Python 3.12.14; `pip freeze` no JSON.
- Dados: 201 manifestos (5 entidades × 40 dias + cadastro de veículos) com SHA-256 registrado; o SHA-256 de cada Parquet confere com o do seu manifesto (0 divergências).
- Qualidade: pytest 535 aprovados, 1 pulado (110,8 s); ruff check limpo; ruff format limpo (353 arquivos); `verificar_despacho_lote.py` OK.
