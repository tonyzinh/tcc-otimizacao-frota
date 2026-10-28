# Reformulação acadêmica do TCC (proposta, 28/10/2026)

Status: **proposta de texto**, não aplicada ao artigo nem ao PDF original. Qualquer número abaixo vem de um arquivo de `reports/tcc_v2/` (citado entre colchetes) ou de `docs/V2_PREREGISTRO.md`. O escopo acadêmico original (`docs/CONTEXTO_PROJETO.md`) muda de enfoque, não de tema: a pergunta deixa de ser "o reposicionamento reduz o KM vazio por corrida?" (já respondida: não) e passa a ser "sob que condições ele compensa, e como decidir isso com rigor?".

Nota de linguagem: o protocolo da v2 foi **registrado no Git antes da execução da v2** (`dc1057e`, 28/10/2026); partes dele (margem −1%, grade de e\*, critério do controle positivo) foram definidas ou corrigidas **depois** de resultados parciais e estão datadas como desvios D1, D2 e D13 em `docs/V2_PREREGISTRO.md` §12. Por isso não usamos "pré-registrado" no sentido forte.

## 1. Problema de pesquisa e pergunta falseável

**Problema.** Em aplicativos de transporte urbano, motoristas ociosos permanecem onde terminaram a última corrida. A literatura e a intuição operacional sugerem que reposicioná-los antes da demanda (alocação preventiva D+1) reduziria deslocamentos sem passageiro. Mover um veículo, porém, também é deslocamento sem passageiro: o ganho só existe se o movimento gerar atendimento adicional ou encurtar coletas futuras o bastante para compensar o seu custo.

**Quem arca com o custo e quem decide mover (decisão D-A do autor, 28/10/2026).** A empresa controla a frota e arca com o combustível e o custo operacional do KM vazio, inclusive o do reposicionamento; o motorista segue a recomendação de posicionamento com taxa de conformidade c (probabilidade, por motorista-dia, de executar o movimento recomendado). Portanto: (i) o custo de mover o veículo é **custo da empresa**, e e\* é o KM vazio extra que **a empresa** aceita pagar por uma corrida adicional atendida; (ii) c é o parâmetro que traduz a decisão do motorista de seguir ou não a recomendação, e quando c < 1 só a fração c dos movimentos é executada (e custa); (iii) a recuperabilidade ρ não depende dessa decisão: é a fração dos pedidos não aceitos observados que um motorista livre aceitaria (ver `docs/V2_PREREGISTRO.md`, D11). Nada disso foi verificado com a empresa: é a premissa de trabalho do autor, e os resultados são condicionais a ela.

**Pergunta.** Em simulação retrospectiva com dados reais da Grande Vitória (março e setembro de 2026), com os mesmos pedidos, frota, janela e método de distância em todos os cenários, existe algum planejador D+1 baseado em dados históricos cujo **benefício líquido** NB(e\*) seja positivo, com intervalo de confiança inteiramente acima de zero, para um custo aceitável e\* de quilômetros extra por corrida adicional atendida, em comparação com baselines operacionalmente realistas e com movimentos aleatórios (placebo)?

## 2. Desfecho primário: benefício líquido NB(e\*)

Por dia, com ΔN/dia a diferença de corridas atendidas entre plano e baseline e Δ(B+R)/dia a diferença de KM vazio (coleta B mais reposicionamento R):

NB(e\*) = ΔN/dia − [Δ(B+R)/dia] / e\*

Interpretação: corridas equivalentes por dia, descontado o KM vazio extra a e\* km por corrida. e\* é a quantidade de km vazio que a operação aceitaria gastar para obter uma corrida a mais. **e\* é um parâmetro de política da empresa e continua PENDENTE (D-C: sem valor de referência; manter grade e curva)**; por isso reportamos a grade {3, 5, 10, 20, 30, 50, 100} e a curva contínua (D2), sem escolher um valor [`fase1_nb.csv`, `fase1_nb_curva.csv`].

**Por que trocar o desfecho primário.** KM vazio por corrida é uma razão cujo numerador cresce por construção quando se move o veículo (o deslocamento entra como KM vazio) e cujo denominador só cresce se houver corrida extra. Um plano que atende mais passageiros a um custo marginal razoável pode piorar a razão e, ainda assim, ser operacionalmente melhor; um plano que não atende ninguém a mais só pode piorá-la. A razão também não separa "mais corridas" de "menos km". NB(e\*) não usa razão (sem o problema de IC ilimitado: o intervalo de Fieller para a razão `e` é ilimitado em 126 de 162 linhas [`fase1_e_fieller.csv`]) e torna explícito o preço que a empresa aceitaria pagar. **KM vazio por corrida permanece como desfecho secundário**, para comparação direta com a v1 e com a literatura.

O controle positivo sintético (D12/D13) mostra que NB(e\*) detecta o ganho quando ele existe: no cenário "fora do raio", ΔN sobe 165% a 226% e NB(30) tem IC inferior entre 32,1 e 43,1 corridas/dia nas sete variantes orientadas a demanda (proporcional, três guloso, limiar, fluxo, húngaro), enquanto a razão KM/corrida **sobe** de 18,6% a 86,2% no mesmo cenário [`fase2_controle_positivo_fora_do_raio_linhas.csv`, `..._nb.csv`]. Esse par de resultados é a justificativa empírica da troca.

## 3. Hipóteses reformuladas

Todas avaliadas por linha (planejador × período), nível de 5%, correção de Romano–Wolf por família, IC de decisão = o mais largo entre oito variantes de bootstrap por dia.

**H1′ (benefício líquido).** Para algum e\* ≤ 30 km por corrida extra, existe ao menos um planejador D+1 para o qual NB(e\*) tem IC inferior > 0 nos **dois** períodos, contra os baselines B1–B3 (deriva realista), e cuja diferença em relação ao placebo de movimentos aleatórios também é positiva.
*Seria refutada se:* em todas as combinações, o IC inferior de NB(e\*) for ≤ 0 para e\* ≤ 30, ou se o plano não superar o placebo.
*Observado:* refutada para e\* ≤ 30. Na F4 (contabilização primária, 100 linhas) o IC inferior de NB é > 0 em 0 linhas para e\* de 3 a 30, em 2 para e\* = 50 e em 5 para e\* = 100 [`fase4_F4_origem_nb.csv`]. Plano contra placebo: 5 reduções (todas do `proporcional`), 10 aumentos, 85 inconclusivas [`fase4_plano_vs_placebo_origem_linhas.csv`].

**H2′ (não inferioridade do atendimento).** Se um planejador reduz o KM vazio por corrida, a variação de corridas atendidas não é pior que −1% (sensibilidade −2%).
*Seria refutada se:* houver redução de KM/corrida com IC inferior de ΔN% < −1%.
*Observado:* não testável de forma substantiva: nenhuma linha atingiu redução de KM/corrida [`fase1_inferencia_linhas.csv`, `fase4_F4_origem_linhas.csv`].

**H3′ (suficiência de informação).** Informação perfeita de demanda (oráculo) é condição suficiente para reduzir KM vazio por corrida.
*Seria refutada se:* com o oráculo, nenhum planejador reduzir KM/corrida.
*Observado:* refutada: 0 reduções e 20 de 20 aumentos [`fase3_oraculo_v1_linhas.csv`]; na escada de ruído, 63 de 63 aumentos, sem inversão de sinal [`fase3_escada_v1_linhas.csv`].

**H4′ (limite do simulador, controle).** O simulador e o procedimento inferencial detectam ganho quando ele existe por construção.
*Seria refutada se:* nenhum planejador orientado a demanda mostrasse ΔN% com IC inferior > 0 e NB(30) com IC inferior > 0 no cenário "fora do raio" (critério D13).
*Observado:* **não refutada** (sete de sete variantes orientadas a demanda passam) [`fase2_controle_positivo_fora_do_raio_*.csv`].

## 3b. Premissa do regime B e condicionalidade do resultado

**Decisão D-B do autor (28/10/2026): confirmada** a contabilização principal `start_at_origin`: os dois braços (plano e baseline) começam a sessão na última posição de D, como o regime B pressupõe ("motoristas dormem onde largam"). **O nulo vale condicionado a essa contabilização.**

Por que "pagar nos dois braços" foi descartado como contabilização principal: nela, o plano parte da última posição de D e o baseline do ponto de login observado, e trocar um trecho noturno longo por um movimento curto "economiza" KM sem nenhuma informação de demanda. O placebo de movimentos aleatórios confirma o artefato: gera 18 de 100 "reduções" nessa contabilização (mediana −1,7%) [`fase4_placebo_pagar_nos_dois_linhas.csv`; D10 em `V2_PREREGISTRO.md`]. A contabilização é reportada como sensibilidade rotulada e nunca como resultado.

**O que esse descarte não responde.** Descartar a contabilização não responde se o plano poderia reduzir o trecho noturno que o motorista já faz sozinho: nos dias de teste (janela 04–11), a média desse trecho é de 3,5 km (março) e 5,6 km (setembro) por motorista-dia, com mediana de 0,7 km [`V2_CONTABILIZACAO.md`]. Se a empresa puder influenciar onde o motorista encerra o dia, esse trecho é uma alavanca que este trabalho não mediu.

## 4. Objetivo geral e objetivos específicos

**Objetivo geral.** Avaliar, por simulação retrospectiva com dados reais agregados, se a alocação preventiva D+1 gera benefício líquido positivo em relação a baselines realistas, e propor um protocolo de decisão baseado em NB(e\*).

**Objetivos específicos** (verbo mensurável; produto verificável):
1. **Construir** um simulador de eventos discretos calibrado nos dados, com regras de contabilização do KM vazio testadas por regressão contra a v1 (`tests/unit/test_v3_sim.py`).
2. **Definir** baselines de deriva dos motoristas livres (parado, retorno à origem, movimento observado, cruzeiro local, reativo) e um placebo de movimentos aleatórios, e **medir** o efeito de cada um sobre o KM vazio [`fase4_*`].
3. **Comparar** dez planejadores D+1 sob os mesmos pedidos, frota, janela e distância, com IC por bootstrap por dia e correção para múltiplos testes (famílias F1–F4) [`fase1_*`, `fase4_*`].
4. **Estimar** o poder e a taxa de falso positivo do protocolo com efeito injetado, e o efeito mínimo detectável [`fase2_falsos_positivos.csv`, `fase2_curva_poder.csv`, `fase1_mde.csv`].
5. **Verificar** o simulador com controle positivo, controles negativos e placebo, de modo que o nulo não possa ser atribuído a defeito de modelagem [`fase2_controle_*`, `fase4_placebo_*`].
6. **Quantificar** o limite superior de informação (oráculo de demanda e escada de ruído) [`fase3_*`].
7. **Propor** a regra de decisão NB(e\*) e **mapear** em que região de (e\*, recuperabilidade ρ, conformidade) o reposicionamento compensaria [`fase1_nb_curva.csv`, `fase4_grade_rho_conformidade*.csv`].

## 5. Justificativa

* **Mobilidade urbana:** quilometragem sem passageiro é congestionamento e emissões sem serviço prestado; sob D-A, é também custo direto da empresa, que controla a frota e arca com combustível e custo operacional.
* **KM morto:** a empresa ainda não homologou a definição corporativa (RN010, DT003); a v2 reporta o KM vazio simulado (coleta mais reposicionamento) sempre rotulado como estimativa por Haversine × fator de rua, nunca como odômetro.
* **Combustível e custo:** como a empresa arca com o KM vazio (D-A), o preço de uma corrida extra frente ao km vazio extra é exatamente e\*. Nenhum valor de referência de e\* foi definido (decisão D-C: não definido; mantém-se a grade e a curva): a empresa fornece o valor ou o trabalho entrega a curva.
* **Decisão baseada em dados:** a contribuição metodológica (baselines realistas, placebo, controle positivo, correção de múltiplos testes, poder) torna o resultado, inclusive o nulo, defensável e reutilizável por outras operações.

## 6. Escopo

**Dentro:** simulação retrospectiva D+1 para a janela 04–11 h (regime B: escala conhecida, motoristas partem da última posição de D); dez planejadores; cinco baselines; dados de março e setembro de 2026 da Grande Vitória, agregados e processados localmente (D3).
**Fora:** despacho em tempo real; qualquer integração operacional; precificação; política empresarial inventada; terceiro período (indisponível); distâncias viárias reais (Fase 5 não feita); dados individuais, IDs e coordenadas individuais em qualquer saída versionada.

## 7. Limitações e ameaças à validade

| Ameaça | Natureza | Mitigação / estado |
|---|---|---|
| Distância Haversine × fator de rua (lacuna M4) | Construto | Sensibilidade do fator na v1; Fase 5 (OSM/OSRM) **não feita** |
| Setembro é replicação **parcial**, não independente | Externa | Não há terceiro período independente; só março e setembro; as janelas de histórico são treino de previsão |
| B4 (reativo) com parâmetros fixos (5 min, 15 min, 3 km) | Construto | Sem varredura; B4 tratado como candidato exploratório |
| Planejadores não conhecem o baseline Bk | Construto | Declarado (D11); pode subestimar um plano que otimizasse contra a deriva |
| B1 e B3 gastam muito KM de deriva (diluem o efeito relativo) | Construto | Tabelas em km absolutos (`fase4_dias.csv`) |
| Premissa do regime B (`start_at_origin`: os dois braços começam na última posição de D) | Interna / construto | Confirmada pelo autor como contabilização principal (D-B, 28/10/2026; D8 e D10); o nulo é **condicional** a ela. O trecho noturno natural (média 3,5 km em março, 5,6 km em setembro) fica fora da comparação; "pagar nos dois braços" é sensibilidade e artefato |
| Contabilização "pagar nos dois braços" | Interna | **Artefato**: o placebo aleatório também gera reduções (18 de 100); **nunca citar como resultado** (D10) |
| 15–16 dias de teste por mês | Estatística | Poder 32–58% para ΔN = 1% e ≥ 83% para 2% (a depender do mês); não distingue 0,25–0,5% [`fase2_curva_poder.csv`] |
| Falso positivo 5,3–8,4% (iid) e 8,6–15% sob dependência serial artificial | Estatística | Dentro da faixa 2–9% só no mundo iid; declarado [`fase2_falsos_positivos.csv`] |
| e\* é política da empresa (PENDENTE) | Construto | D-C: sem valor de referência; grade e curva, sem escolher valor |
| Empresa controla a frota e o motorista segue a recomendação com conformidade c (D-A) | Construto | Premissa do autor, não verificada com a empresa; c é varrido em {0,5; 0,75; 1} na grade ρ × conformidade (descritiva) |
| Oráculo e regime B violam o corte D+1 estrito | Interna | Rotulados "oráculo" e "regime B", nunca D+1 estrito |
| Controle negativo N3 (previsão sem informação) não é um nulo válido em "fora do raio" | Interna | Ver `RELATORIO_V2.md` §(c); espalhar motoristas por 4 zonas cobre a geografia sem informação |
| Planejadores baseados em cenário (busca local, recozimento, PSO) não se movem no controle | Construto | O objetivo deles é KM/corrida com piso de atendimento; avaliaram e rejeitaram os movimentos (`J_busca_vazio` < `J_busca_inicial`) |
