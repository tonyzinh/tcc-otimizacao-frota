# Metodologia

> Documento consolidado em 09/11/2026 na reestruturação do repositório. Cada parte abaixo é o documento de origem, com o conteúdo preservado; só os caminhos de arquivos foram atualizados para a estrutura nova (mapa em `reports/manifests/repository_restructure/path_map.csv`). Datas e afirmações são as da origem.
> Caminhos marcados com † são de arquivos retirados da árvore ativa nas reorganizações de 09/11/2026 (código e documentos do estudo anterior, scripts substituídos pelo pacote). As cópias estão na pasta de preservação `../tcc-otimizacao-frota_preservacao_2026-11-09/` (`arvore_antiga/`, `rodada4_arquivamento/`, `copia_completa_pre_migracao/`). Nos trechos anteriores a 09/11/2026, `data/raw/` designa a pasta de extrato bruto antiga, apagada em 08/11; desde a reestruturação, `data/raw/` é a antiga `data/extraido/`.


## Metodologia

_Origem: `docs/methodology.md`._

### Pergunta e hipótese

A atribuição **conjunta** de pedidos a veículos em lotes de 60 s (algoritmo Húngaro) reduz o km vazio (aproximação do veículo ao passageiro) em relação ao despacho pelo mais próximo livre, **sem piorar o atendimento**? É uma hipótese a testar; resultado nulo ou negativo é resultado. Escopo: simulação com km **estimado**; não mede efeito operacional.

### Políticas

| Id | Política | Papel |
|---|---|---|
| A | mais próximo livre, despacho imediato | referência (baseline simplificado calibrado; **não** é a operação manual) |
| B | mais próximo livre, lotes de 60 s (FIFO por chegada, id) | isola o efeito do lote |
| C | Húngaro, lotes de 60 s | método principal |

Contraste principal **C × A**; complementar **C × B** (efeito da atribuição com o lote fixo) e B × A (efeito do lote).

### Formulação do lote (política C)

Em cada instante `t` múltiplo de 60 s: pedidos pendentes `R_t` (já chegados, não atendidos, não expirados), veículos `V_t` online; par `(r, v)` **elegível** se o veículo está livre, sem conflito de compromisso e a distância de aproximação está no raio. Objetivo lexicográfico: (1) maximizar pares; (2) minimizar a soma das distâncias. Matriz ampliada com colunas "não atribuído" de custo 0 e custo `c − M` nos pares elegíveis (M maior que qualquer soma); custo inteiro (metros × 10⁵ + índice) para desempate determinístico. Solver: Kuhn–Munkres com potenciais (implementação própria, O(n²m)); `scipy.optimize.linear_sum_assignment` é só oráculo de teste. O ótimo é **do lote**, não do dia.

### Simulador

Eventos discretos; jornadas e compromissos externos respeitados; sem teletransporte; sem atendimento duplicado; a política vê só o estado do instante. Espera do pedido = do chegada até o embarque (inclui a espera até a fronteira do lote e o deslocamento de aproximação) e é calculada **só entre os atendidos**: políticas diferentes atendem conjuntos diferentes, então comparações de espera podem refletir seleção e não são melhoria garantida.

Linha **histórica**: distância = Haversine × 1,3012, 16,079 km/h, raio 4,5 km em linha reta, paciência 180 s (parâmetros da calibração de março, não reajustados). Sem roteamento viário: pontes e a baía **não** são modeladas e a aproximação pode ser subestimada onde o caminho real exige desvio.

Linha **sintética**: caminho mínimo (Dijkstra) sobre a rede viária OpenStreetMap (Overpass, instantâneo de 08/11/2026, API 0.7.62.11, ODbL); 25 km/h; raio de 8 km por via; paciência 600 s; 100 veículos; jornadas de 9 h; pontos H3 res. 8 e zonas res. 7; recorte a até 20 km por via do Centro de Vitória. Verificações estruturais (testes): o grafo do recorte é conexo (368 pontos, distâncias finitas), a distância por via nunca é menor que a reta, e a razão via/reta ilha–continente (Vitória→Vila Velha, mediana 1,45) é comparável à dentro do mesmo município (Vila Velha, 1,34), de modo que há travessia(s) mapeada(s) (o arquivo tem 521 trechos com `bridge=*`, entre eles a Terceira Ponte, a Segunda Ponte, a Ponte do Príncipe e a Ponte Florentino Avidos). **Não** se verificou ponte a ponte nem se validaram tempos de percurso; congestionamento e pedágio não são modelados.

### Critérios de serviço

* Histórico: **E1** nenhuma violação de compromisso causada pela política; **E2** atendidos(C) ≥ atendidos(referência), sem tolerância; **E3** P90 agregado da espera ≤ o da referência.
* Sintético: razão média pareada de atendidos ≥ 0,995 **e** razão das médias de P90 ≤ 1,05. É **mais frouxo** que E2 (tolera 0,5% de perda média por semente). Os critérios não foram alterados retroativamente.

### Estatística

O **dia** (histórico) ou a **semente** (sintético) é a unidade. Histórico: IC95% por bootstrap de blocos móveis de 7 dias (10.000 reamostragens, semente 20261108). Sintético: IC95% percentil por bootstrap de sementes; Holm nos testes confirmatórios (política em lote × A nos cenários S1–S5; no resumo congelado são 20 testes, pois entram as variantes de lote de 30 s e o método de fluxo preservado nos dados; p mínimo ajustado 0,002 = 20 × 1/10.000). Um IC que inclui zero **não** é equivalência.

### Resultados vigentes (arquivos citáveis)

| Resultado | Arquivo |
|---|---|
| Setembro/outubro, totais e contrastes | `reports/historical/frozen_evaluation/analise/` |
| Congelamento, hashes | `docs/methodology.md`, `reports/historical/frozen_evaluation/CONGELAMENTO.json` |
| Verificação de otimalidade (2.628 lotes) | `reports/historical/frozen_evaluation/verificacoes_desenvolvimento.json` |
| Sintético | `reports/synthetic/dispatch_evaluation/analise/resumo_contrastes.csv` |

C × A em outubro: −5,04% de km vazio, mas **−85 atendidos** (14.466 vs 14.551 de 23.523): −0,36 p.p. do universo elegível, ≈ −0,58% dos atendidos de A; **E2 não foi cumprido**.

### Limitações

Simulação, não operação; km estimado; baseline simplificado; disponibilidade reconstruída retrospectivamente (jornada realizada); parâmetros herdados de março; atendimento simulado de 62–66%; uma empresa e região; sem deduplicação de tentativas; ótimo por lote ≠ ótimo diário; sintético não independente entre cenários e com sementes finais já vistas.


## Congelamento da atribuição conjunta com janela de 60 s (09/11/2026)

_Origem: `docs/methodology.md`._

Escrito **antes** de qualquer execução em 16–30/09 e 01–25/10 (nenhuma política foi simulada nesses dias; só foram contadas linhas e conferidos manifestos). Autorização do proprietário em 09/11/2026: congelar e executar replicação e avaliação final; **não** alterar o TCC; **não** fazer commit nem stage.

### 1. Identidade do método (verificação pedida)

- **C** é o algoritmo **húngaro** (Kuhn–Munkres com potenciais e caminho aumentante, O(n²m)), implementação própria `comparacao/despacho.py::kuhn_munkres`, com formulação lexicográfica: maximiza o número de pedidos atendidos no lote e, entre as soluções com esse máximo, minimiza a soma das distâncias de busca (custo inteiro em metros + índice para desempate determinístico). O nome está correto. `scipy.optimize.linear_sum_assignment` (busca de caminho aumentante, estilo Jonker–Volgenant) **não** é usado como política; só como oráculo.
- Verificação (`scripts/verificar_despacho_lote.py`†, 4 dias de desenvolvimento: 10/02, 04/03, 17/03, 25/03): em **2.628 lotes** o conjunto devolvido tem o mesmo número de pares e a mesma soma de distâncias (resolução de 1 m) que o ótimo do oráculo; diferença máxima na soma exata: 0,0015 km, só por arredondamento.
- O fluxo de custo mínimo (não usado aqui) também atinge o ótimo, mas em 37 de 1.291 lotes (2 dias) devolveu **outro** conjunto de pares de custo igual (ótimos alternativos); por isso Húngaro e fluxo não são sempre idênticos nos agregados. Isso não é erro de nenhum dos dois.

### 2. Verificações em dados de desenvolvimento (resultado: todas aprovadas)

`reports/historical/frozen_evaluation/verificacoes_desenvolvimento.json` (agregado; sem IDs nem coordenadas):

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

### 3. Políticas e ordem de B

| Código | Política | Implementação |
|---|---|---|
| A | mais próximo livre, despacho imediato | `B0_imediato_atual` (motorista elegível mais próximo no instante do pedido; fila FIFO se nenhum) |
| B | mais próximo livre, lotes de 60 s | `B_lote60s_guloso_fifo`: pedidos pendentes ordenados por **(instante de chegada, id)**, cada um recebe o motorista elegível mais próximo ainda livre. Essa ordem é a mesma do despacho atual e foi definida antes de qualquer resultado; não depende de C |
| C | atribuição conjunta, lotes de 60 s | `B_lote60s_hungaro` |

Lotes: instantes múltiplos de 60 s desde 00:00; pedido espera até o próximo instante; motorista liberado espera o próximo lote; paciência de 180 s; cancelamento e fila como no simulador comum. A e B/C compartilham pedidos, frota, jornadas, compromissos, parâmetros (raio 4,5 km; 16,079 km/h; fator 1,3012; paciência 180 s, herdados da calibração de março), posição inicial `primeira_posicao_observada` e cenário J.

**Contraste principal (fixado antes dos resultados): C × A**, em cada período. Complementares: **C × B** (isola a atribuição conjunta do efeito do lote) e **B × A**. Nenhum outro contraste é calculado.

### 4. Origem da escolha (o que foi consultado)

- **Janelas experimentadas:** 30 s e 60 s (candidatas fixadas em `docs/PLANO_COMPARACAO_ALGORITMOS.md`†, escrito em 08/11 às 10:49, antes da primeira execução do grupo B às 10:50).
- **Como o 60 s foi escolhido:** regra do plano (§5–6), no **treino real 01/02–15/03 (43 dias)**: entre as políticas elegíveis (E1–E3) com IC95% de bloco superior < 0, a de menor km foi o fluxo de 60 s (−5,44%); o desempate por simplicidade (IC da diferença pareada contra o Húngaro de 60 s contém 0: −0,17; 17,09 km/dia) escolheu o **Húngaro de 60 s** (−5,02%). O Húngaro de 30 s (−4,02%) ficou pior que o fluxo de 60 s com IC excluindo 0 (13,4; 49,5), logo 60 s > 30 s. Fluxo × Húngaro: preferiu-se o Húngaro por simplicidade e tempo (3 s × 24 s por 16 dias).
- **O que mais foi visto antes desta decisão de adotá-lo:**
  - Validação real 16–31/03 (16 dias): confirmou 60 s e Húngaro (−4,76%; IC −139 a −70 km/dia; +111 atendidos). A validação não participou da escolha de W; participou da decisão do proprietário de adotá-lo.
  - Sintético, fatia de desenvolvimento S1–S5 × sementes 101–110 (D com Húngaro/fluxo ≈ −6,4%).
  - Sintético, avaliação final 22 cenários × sementes **20001–20040**: executada uma vez, conforme o plano, com as quatro políticas D (30 s e 60 s) como confirmatórias, **mas seus resultados foram vistos antes da decisão de adoção**. Elas não escolheram W nem o algoritmo (a escolha já vinha do treino real), porém não podem ser descritas como evidência independente da decisão de adotar. **Reclassificação:** evidência sintética de D = confirmatória do protocolo, **já conhecida na adoção**.
  - Sementes 9001–9040: não usadas para D.
- **Períodos já examinados para atribuição:** 01/02–15/03 e 16–31/03. **Nunca examinados:** 16–30/09 e 01–25/10.
- Reposicionamento (grupo R) foi estudado nos mesmos períodos de fev–mar; resultado negativo preservado (§9).

### 5. Independência dos períodos de setembro e outubro

São futuros em relação ao período de seleção (**out-of-time**), nunca simulados sob nenhuma política antes desta execução, e o método **não** será ajustado entre eles. Limites da independência: mesma empresa, região e simulador; parâmetros de simulação herdados de março; o cadastro de veículos é uma única foto (extraída em 08/11/2026) usada para todos os dias; o autor viu fev–mar. Setembro e outubro respondem "o resultado se repete em outros meses?", não "o resultado vale na operação real". Se surgir erro de implementação que exija correção, será registrado e a independência reavaliada; não se repete e seleciona a melhor execução.

### 6. Dias, entradas e elegibilidade

Regra fixada aqui antes de executar (igual à do desenvolvimento, sem o critério de 28 dias de histórico, que existia só para o planejador D+1): entidades do dia presentes (`solicitacao`, `jornada_motorista`, `compromissos_externos`, `veiculo_condutor`, `posicao_ofertas`) e cadastro `veiculo`; ≥ 300 instantes de posição; ≥ 200 pedidos TempoReal. Resultado, só com contagens (`reports/historical/frozen_evaluation/elegibilidade_*.json`): **replicação 15/15 dias elegíveis; final 25/25**; mínimo de 702 instantes por dia e de 459 pedidos. Nenhum dado ausente foi substituído. `telemetria_cobli` só existe em fev–mar, mas não é usada por esta linha. Pedidos agendados ficam fora (recorte por tipo, contado); cancelados permanecem como demanda; novas tentativas do mesmo passageiro **não** foram deduplicadas (limitação).

### 7. Critérios de serviço, métricas e estatística (fixados)

- E1 nenhuma violação de compromisso causada pela política; E2 atendidos(política) ≥ atendidos(referência) no período; E3 P90 agregado da espera ≤ o da referência. Sem SLA da empresa: critérios experimentais.
- Métricas por política e período: km vazio absoluto (busca; sem reposicionamento nesta linha), pedidos elegíveis, atendidos, não atendidos, atendimento em %, km por atendido, espera média e P90 dos atendidos, violações, tempo computacional (inclui a simulação do dia).
- Contrastes: variação absoluta e percentual (negativo = redução), diferença pareada por dia com IC95% por bootstrap de blocos móveis de 7 dias (10.000; semente 20261108), dias com melhora/piora, diferença de atendidos e de pontos percentuais, diferença de espera média e P90.
- Classe: `reducao_com_servico_preservado` se limite superior do IC < 0 e E1–E3.
- Períodos reportados separadamente; **nunca somados**, nem com o sintético.

### 8. Procedimento e falhas

`scripts/executar_atribuicao_final.py† --congelar` grava `reports/historical/frozen_evaluation/CONGELAMENTO.json`; `--executar` roda setembro e depois outubro, só com as três políticas, e recusa se o hash do código mudou, se não houver congelamento ou sem `TCC_COMPARACAO_VENCEDOR_CONGELADO=SIM`. Execução idempotente por dia; falhas técnicas vão para `reports/historical/frozen_evaluation/falhas.jsonl` (criado só se houver falha; não houve) e o dia é retomado sem alteração de código; não há reexecução seletiva. Saídas: `reports/historical/frozen_evaluation/execucao/`; análise: `scripts/analisar_atribuicao_final.py`† → `reports/historical/frozen_evaluation/analise/`.

### 9. O que esta avaliação não responde

- É **simulação com entradas históricas**, não economia observada na empresa. Km é estimado (reta × fator), não odômetro.
- A referência A é um despacho "mais próximo livre" simples, **não** uma reprodução validada da operação manual; a comparação mede a diferença entre políticas de despacho **sob este simulador**, não a diferença entre a operação real e o húngaro.
- Hipótese de reposicionamento D+1: **resultado negativo preservado** (nenhum método de reposicionamento reduziu km vazio com evidência nos períodos de desenvolvimento, e o guloso original piorou o km no sintético). O resultado de despacho não o invalida; são perguntas diferentes (posicionar antes × atribuir durante a operação).
- Adotar a atribuição muda o escopo do TCC (decisão durante a operação, com pedidos já chegados). Isso depende de decisão do proprietário.

### 10. Retrato congelado

Preenchido ao final (após testes, lint e formatação): ver `reports/historical/frozen_evaluation/CONGELAMENTO.json` e a seção abaixo.

**Congelado em 09/11/2026** (antes de executar setembro/outubro; `reports/historical/frozen_evaluation/CONGELAMENTO.json`):
- Código: SHA-256 de 151 arquivos (`src/tcc_frota/**/*.py` + scripts e configs da avaliação) = `480a98a15cc88ea4e502dc72492c2472ecd31a794d74490985d42ea9d8e93f87`; commit base `3e77cb9e013918b9a4325dd9e43acdd5fc0ec659`; `git diff HEAD` = `2193740d9edc4a248cce492481376644bf9dd11efea7bf815e03477218d70578` (alterações não commitadas por instrução). Python 3.12.14; `pip freeze` no JSON.
- Dados: 201 manifestos (5 entidades × 40 dias + cadastro de veículos) com SHA-256 registrado; o SHA-256 de cada Parquet confere com o do seu manifesto (0 divergências).
- Qualidade: pytest 535 aprovados, 1 pulado (110,8 s); ruff check limpo; ruff format limpo (353 arquivos); `verificar_despacho_lote.py` OK.


## Plano do experimento sintético (Grande Vitória)

_Origem: `docs/methodology.md`._

Origem: mudança de escopo de 08/11/2026 (`docs/decisions.md`, R-23). Este plano vale para a fase sintética; os planos de extração e de comparação de vários algoritmos estão arquivados.

### 1. Pergunta e escopo

**Pergunta:** em quais condições de distribuição espacial e temporal da demanda um algoritmo guloso de reposicionamento preventivo reduz os quilômetros sem passageiros em uma frota simulada na Grande Vitória, em comparação com uma política de espera no destino?

- Só dados operacionais sintéticos. Geografia pública (IBGE, OpenStreetMap/ODbL); demanda, frota e jornadas são hipóteses experimentais. Nenhuma estatística de dado privado.
- Políticas: **A** espera no destino (sem reposicionamento); **B** guloso (`GulosoMarginal`, α=0,2, ρ=2,5 km, salto máximo do cenário) com previsão do histórico sintético, decisão única antes da operação (D+1), "não reposicionar" admitido, reposicionamento integralmente no custo. Mesmo despacho, raio e regra de espera em A e B.
- Fora de escopo: outros algoritmos, otimização em tempo real, dados reais, reposicionamento contínuo.

### 2. Geografia

Municípios: Vitória, Vila Velha, Serra, Cariacica (parte da Grande Vitória). Recorte operacional: pontos a ≤ 20 km por via (ida e volta) do Centro de Vitória. Pontos de parada = um nó de via por célula H3 r8 (≥ 20 nós, centro a ≤ 350 m de via), na maior componente fortemente conexa; distâncias = menor caminho pela rede (Dijkstra), sem linha reta sobre a água. Zonas de planejamento H3 r7 (sensibilidade: r6 e r8). Fontes, URLs, licenças e SHA-256: `data/geographic/manifesto_geografia.json` (gerado por `scripts/download_geography.py`).

Limites assumidos: rede OSM como proxy de acessibilidade; sem sentido de tráfego dinâmico; velocidade constante.

### 3. Gerador e parâmetros

`src/tcc_frota/scenarios/generator.py` (versão 1.0.0). Cada parâmetro com nome, unidade, valor, justificativa e classe (hipótese experimental ou informação geográfica) em `tabela_parametros`, exportada a cada execução em `parametros.csv`. Frota homogênea de 100 veículos, jornadas de 9 h iniciando em {6, 8, 10, 12} h, veículos parados onde terminaram a jornada anterior, escala de D+1 conhecida no corte. Previsão e realização são objetos separados (`previsao` ≠ `pedidos`); histórico de 28 dias gerado com canais de semente independentes do dia avaliado. κ (corridas/veículo-hora) é calibrado simulando a referência nos 3 últimos dias do histórico, não suposto.

### 4. Matriz de cenários (congelada)

Definida em `src/tcc_frota/scenarios/catalog.py` antes de qualquer resultado do guloso; hash da matriz + parâmetros operacionais + versão do gerador: ver §9. S1 uniforme; S2 concentrada e previsível; S3 frota inicialmente desequilibrada; S4 mudança inesperada de demanda; S5 demanda que migra de região ao longo do dia; S6 relação frota/demanda baixa/intermediária/alta (variantes `*_frota_abundante` e `*_frota_escassa` de S2 e S3, 4/8/14 pedidos por veículo). Sensibilidades: salto máximo 6 e 10 km; resolução H3 6 e 8; erro de previsão controlado (σ=0,5); previsão perfeita (**diagnóstico idealizado**, nunca resultado principal).

As concentrações são hipóteses sintéticas localizadas no mapa; não representam fluxos reais.

### 5. Contabilidade

KM vazio = busca (aproximação até o embarque) + reposicionamento. Retorno e outros vazios: não modelados (zero, declarado). Movimentos ocorrem no início da jornada do veículo e entram integralmente no custo, inclusive antes da primeira solicitação. Pedidos não atendidos no encerramento são contados como não atendidos; serviços em curso terminam sem truncar o custo (o simulador contabiliza a corrida iniciada). A e B têm a mesma assinatura de entrada (SHA-256), verificada a cada par.

### 6. Repetições e fases

| Fase | Sementes | Uso |
|---|---|---|
| Piloto | 1–5 | calibrar mundo (só a referência A) e dimensionar n |
| Desenvolvimento | 101–120 (20) | explorar, diagnosticar mecanismo, corrigir o guloso se houver erro |
| Avaliação | 9001–9040 (40, **reservadas**) | única rodada da configuração congelada |

Piloto (n=5): desvio-padrão do Δkm entre ≈ 37 e 82 km por execução; meia-largura do IC95% com n=40 ≈ 25 km (≈ 1% do km vazio de A). Sementes independentes; nenhuma escolhida. O comando `scripts/executar_sintetico.py† --fase avaliacao` recusa rodar se o plano não contiver o hash da configuração (§9).

Cenário que parecer favorável só no desenvolvimento é **hipótese exploratória** e precisa se confirmar na avaliação reservada.

### 7. Métricas e regra de classificação

Principal: km vazio total (diferença pareada B − A por semente). Complementares: km de busca, de reposicionamento, atendidos (quantidade e proporção), espera média e P90, km por atendimento, tempo do algoritmo, movimentos planejados e executados.

**Atendimento preservado** (critério experimental, definido antes das execuções; não é SLA): razão média pareada de atendidos B/A ≥ 0,995 **e** P90 de espera médio de B ≤ 1,05 × o de A.

Classes por cenário (IC95% bootstrap sobre sementes, 10.000 reamostragens, semente 20261108):
- `reducao`: limite superior do IC < 0 e atendimento preservado.
- `reducao_com_perda`: limite superior < 0, atendimento não preservado (não conta como redução).
- `piora`: limite inferior > 0.
- `sem_diferenca_detectavel`: demais casos; reportar a meia-largura do IC (poder).

Relato: média, dp, IC, frequência de melhora e piora, por cenário (`scripts/analisar_sintetico.py`†). Sem correção formal de múltiplas comparações entre os 5 cenários principais além de reportar todos; as variantes são sensibilidades, não hipóteses independentes.

### 8. Linguagem de conclusão

Permitido: "Nas condições sintéticas especificadas, o algoritmo apresentou (ou não) redução de km vazio em relação à referência." Proibido: concluir sobre a operação real da V1 Viagens.

### 9. Congelamento

Congelado em 08/11/2026, após o desenvolvimento (sementes 101–120, `reports/synthetic/repositioning_greedy_study/development/`).

- Hash (matriz + parâmetros operacionais + versão do gerador): `716adc2ed3563281c50eb504c6d9a7d12790bef7369521fe5cdbb4b06957ad63` (igual ao do piloto: a matriz não foi alterada após ver resultados).
- Alterações no guloso após o desenvolvimento: **nenhuma**. O desenvolvimento não revelou erro de implementação: o km de reposicionamento planejado (`km_modelo`) coincide com o simulado (ex.: 49,3 km em S2/101), todos os movimentos planejados foram executados, A e B têm a mesma assinatura. Os resultados de desenvolvimento (B pior que A em 21 de 22 cenários; ver `analise/`) não motivaram ajuste de α, ρ, salto ou previsão: não se reexecuta variando algo até "dar certo".
- Mecanismo observado (desenvolvimento, exploratório): o reposicionamento custa ≈ 30–60 km por dia e a redução de km de busca é de apenas ≈ 0–9 km; o objetivo do guloso é cobertura esperada − α·km, não km vazio. Detalhes e limites em `docs/decisions.md` (R-24).
- Próximo passo: rodar uma única vez `python scripts/executar_sintetico.py† --fase avaliacao` (sementes 9001–9040).
