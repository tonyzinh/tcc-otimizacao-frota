# 03 — Precificação

Fontes: `analises/dre_simulacoes_preco/docs/equacoes.md` e `dicionario_dados.md`, `analises/diagnostico_novo_preco_v1/`, `sql/DICIONARIO_BANCO.md`, `CLAUDE.md`, `sigma_api/`, e branches `fix/repos-restructuring` e `sigma` (reprodução do preço antigo).

## 1. A premissa central

Cada corrida consome a frota em **três pernas**: pickup (motorista vazio até o cliente), viagem (faturada) e retorno (vazio após largar). **A receita só olha a viagem.** Daí a tese: precificar por **margem operacional por hora de frota alocada**, não por tarifa.

Evidências do problema (C4, PF região 1, 23–29/jul/2026, n = 1.023):

| Medida | Valor |
|---|---|
| R$/hora de frota alocada | **60,59** (alvo 91,03, −33%); em mar/2026 era 62,59 (−31%) |
| km de frota ÷ km faturado | **2,03** |
| % do km rodado não faturado (mediana) | **52,1%** (76% em corridas ≤ 2 km) |
| R$/km faturado × R$/km de frota | 6,58 × **3,25** |
| Erro de tempo total (média) | **+5,21 min ≈ R$ 5,57 por corrida** |
| R$/h de frota por faixa de distância | **plano**, entre 58 e 65 — a curva não está torta, o **nível** está uniformemente abaixo do alvo |

## 2. Motor de preço v2 (equações do repositório)

Variáveis: `km_v, km_p, km_r` (viagem, pickup, retorno) e `t_v, t_p, t_r` (minutos).

**Premissas econômicas do estudo (`equacoes.md`):** `c_km = 1,10 R$/km` · `c_h = 20 R$/h` (= 0,333 R$/min) · `M_h_min = 30 R$/h` · `M_h_max = 40 R$/h` · markup `m = 50%` · dedução `d = 22%` · piso `P_piso = R$ 16`.

```text
Custo        C = (km_v+km_p+km_r)·c_km + (t_v+t_p+t_r)·c_h/60

Formulação A (MC02 absoluto por hora-frota):
  RB_min(A) = [ C + (t_v+t_p+t_r)/60 · M_h_min ] / (1 − d)         P*_A = max(P_piso, RB_min(A))
Formulação B (markup sobre custo):
  RB_min(B) = C·(1+m) / (1 − d)                                      P*_B = max(P_piso, RB_min(B))
Teto da banda de cupom (A com M_h_max):  RB_teto = [ C + t/60·M_h_max ] / (1 − d)
Banda de cupom: P*_A ≤ P_cobrado ≤ RB_teto ;  Δcupom = RB_teto − P*_A
```

- **A e B são regras concorrentes, não combinadas** num `max`. A domina em corrida longa em **tempo**; B em corrida longa em **km**.
- **Regra de ouro:** o valor pós-cupom **não pode cair abaixo de P*_A**. Evidência de que não está implementada: as 129 corridas PF de julho com MC02 negativo têm **todas** desconto (cupom em 62, parceria em 30, colaborador em 37) — ver [04](04_pessoa_fisica.md) §6.
- **Fallback do retorno:** a base financeira não traz retorno ao H3 mais próximo → o estudo adota `km_r = km_p` e `t_r = t_p` (simetria). **Premissa, não dado.** Em contexto PJ, o extrato por cliente **exclui** o retorno do custo (`dist_total = DV + DP`).
- **σ (fator de equilíbrio operacional):** `DE_FATOR_EQUILIBRIO_OPERACIONAL` / `DE_SIGMA`. A fórmula completa do σ está em `equacoes.md` (não reproduzida aqui); σ colado em 1,00 derrubaria a tese de preço por oferta. A hipótese "preço real não contém disponibilidade" é testada como checagem no diagnóstico.
- **Exemplo numérico do documento** (km_v=5, km_p=2, t_v=17, t_p=5, com retorno): C = R$ 18,90; P*_A = **R$ 41,54**; P*_B = **R$ 36,35**; teto R$ 47,31; Δcupom R$ 5,77 (13,9%); MC02/h = R$ 30,00; R$/km percebido = 8,31 contra R$/km da operação 4,62.
- **Calculadora:** `analises/dre_simulacoes_preco/modelos/calculadora_preco_didatica.xlsx` (gerada por `modelos/build_calculadora.py`).

### Parâmetros observados em produção (VERIFICADO, jul/2026)
`DE_VALOR_KM_VEICULO = 0,97 R$/km` e `DE_VALOR_HORA_MOTORISTA = 0,33 R$/min` — **valor único em 13.220 cotações PF**. São os **mesmos** do contexto PJ (0,969 / 0,33). Pergunta aberta: parâmetro global por decisão, ou PF nunca teve custo próprio? (ABERTO, FP&A.) Os de `equacoes.md` (1,10 / 20 R$/h = 0,333/min) divergem em R$/km — precisa confirmar quais rodam em produção.

Piso de R$ 16: ativo em 95 corridas (9,3%). Impostos: PIS 1,65 + COFINS 7,60 + ISS (0, 5, 7 ou 12).

## 3. O preço é congelado no aceite (VERIFICADO)

Inclinação empírica de **−0,02 R$/min** de erro de tempo contra **1,0684** teórico: o tempo realizado **não chega à fatura**. Logo:
- Não há surpresa para o cliente; erro de tempo é **margem perdida da V1** (≈ R$ 5,7 mil/semana só em PF região 1).
- **Aberto:** `valor_bruto − valor_cotado` dá média **−R$ 4,20** (só 12,1% das corridas têm os dois idênticos) com inclinação zero em relação ao tempo. Algo recalcula o valor entre cotação e fatura e **não é o tempo** (piso? arredondamento? σ recalculado? componente não documentado?). Se for fórmula diferente da documentada, **invalida simulações feitas a partir de `equacoes.md`**.

## 4. O evento de 13/06/2026 — o "preço real"

- Em ~**13/06/2026** a fórmula do preço real (custo/km + custo/tempo + margem por hora-frota + piso R$ 16) substituiu a tarifa anterior.
- **Quem tomou:** PF e PJ Padrão. **Quem não tomou:** PJ Customizado (tarifa contratada) e Prime → **grupo de controle** para diferença-em-diferenças com placebo.
- **Data e escopo exatos, rollout gradual e eventual rollback: ABERTO** (precisa do dev). O ponto de corte nos dados é detectado pela **assinatura do motor** (colunas `DE_MC2_ALVO`, `DE_CUSTO_*`, `DE_SIGMA`).
- **Efeito no funil PF** (30 dias antes × 30 depois): Est→Sol caiu **49,9% → 39,3% (−10,6 pp)** depois de corrigido (a medição original dava −22,4 pp). **53% da queda atribuída ao preço era artefato de mudança de fluxo**, porque o **modelo de preço fixo de PF foi desligado na mesma semana (08–14/06)**: o fixo era 19–24% das solicitações e **não tem cotação em `APP_ESTIMATIVA_PRECO`** — entrava no numerador do funil sem entrar no denominador. Efeito real: t = 6,33, p ≈ 5e-08.
- Aceite caiu de 61,7% → 39,4% (como medido originalmente); corridas/dia 240 → 173.
- **Redução de margem PF em 30/07/2026** (em produção para todas as corridas PF) **não moveu o funil**: aceite ficou em 37,8% (patamar de julho), conclusão em 37,3%, dentro de 1 desvio-padrão dos blocos Qui–Dom recentes (só 4 dias de janela — pouco).

### Hipóteses formais do diagnóstico (`hipoteses.md`)
| | Enunciado | Se vencer |
|---|---|---|
| H0 | A queda é real (dedup, data de corte correta, média diária) | — |
| H1 | Preço acima da disposição a pagar, de forma geral | Recuar o nível (caro) |
| H2 | Preço quebrou um **nicho** (corrida curta pelo piso; pico pelo tempo) | Reformar a curva no nicho (cirúrgico) |
| H3 | Queda **ambiental** (inverno/chuva/férias/concorrência) | Recalibrar expectativa |
| H4 | O preço está certo; queda é o **efeito pretendido** (perdeu-se volume de MC02/h negativo) | Comunicar e monitorar ocupação |

A matriz de decisão ficou **em branco** no documento (a preencher ao fim da execução). Regra de encerramento: soma dos pesos explica a queda de H0 com ±20%.

## 5. Fixo × dinâmico

| Fato | Evidência |
|---|---|
| `BL_PRECO_DINAMICO = 0` é Fixo; 0 nulos em 66.296 solicitações | C9 RS2 |
| Fixo = 23,6% das solicitações PF em abril; 20,5% maio; 7,3% junho; **0% julho** | C9 RS3 |
| Fixo era **a viagem longa**: acima de 10 km responde por 87–97% das corridas; abaixo, <0,5% | C9 RS4 |
| km médio: **16,4 km no Fixo contra 4,5 km no Dinâmico** | C9 RS5 |
| O corte de 10 km é **parâmetro do sistema**: `APP_ESTIMATIVA_PRECO_FIXO_PRINCIPAL.NU_KM_PRECO_FIXO = 10.000 m` em 100% das cotações fixas (refuta os 30 km do `dicionario_metricas.md`) | C10 RS1 |
| Cotações fixas convertidas por mês: abril 3.984 PF / 16.323 PJ; julho **0 PF** / 10.064 PJ; agosto 0 PF / 307 PJ | |

Conclusão: o Fixo **não** foi desligado na operação toda — só em PF. "O fim do preço fixo" como evento da operação inteira está errado.

## 6. Custos em camadas na base financeira (`Análise detalhada V1_III.xlsx`, aba BD, março/2026)

18.675 corridas × 105 colunas, recebida do financeiro (valores **hardcoded**, sem fórmula Excel; engenharia reversa fecha com <R$ 0,01):

```text
MC 0.1 = RL − C_viagem                              (MO Viagem + GG-Veículo_Viagem + MT-Veículo_Viagem)
MC 0.2 = MC 0.1 − C_pickup                          ← "Mg MC 02" das pivots  (MO/GG/MT Pickup)
MC 0.3 = MC 0.2 − C_tempo_improdutivo               (MO Pausas, MO s/ Apontamento, GG/MT Km Morto)
MC1    = MC 0.3 − C_indireto_rateado                (MO Backoffice, MO Rateio, GG-Demais, Outros)
```

Médias de março/2026: MC 0.1 R$ 27,18 · MC 0.2 R$ 14,50 · MC 0.3 R$ 1,43 · **MC1 −R$ 10,23** (operação consolidada em prejuízo após rateio cheio). Margem MC02: 42% PF, 27% PJ. `Fat/Hr` médio R$ 62,59; `MC/hr` R$ 23,75; km/h médio 23,7; pickup/viagem em km mediana ~0,50, em tempo ~0,32; KM Viagem médio 9,80, Pickup 5,64, Morto 3,46. Horários: 71,6% fora de rush, 17,3% rush da tarde, 11,0% manhã. Agendamento 37,2%. Aba "Referência de Custo Km vs Hr": custo/km R$ 1,00, custo/h R$ 20, margem mínima 46% (tabela âncora por velocidade, 8–60 km/h). Aba "Agendado vs Livre" traz a lista de "to do" do financeiro: revisar pickup, modelo por tempo, bloquear/encarecer agendamento no pico, limitar raio de pickup.

Distinção importante: o **MC02 da BD** é diagnóstico (9 buckets de custo, sem retorno); o **MC02 do motor v2** é prospectivo (1 bucket agregado, com retorno por fallback).

Planilha de custos operacionais: `analises/custos_operacao_v1/` — estrutura criada (`docs/definicao_colunas.md` existe), **mas o README informa que a planilha original e `src/transformacao.py` ainda são "próximos arquivos a criar"**.

## 7. Como o preço era antes (branches de 2025)

O README de `fix/repos-restructuring` (09/2025, "Precificação Dinâmica — V1") descreve o desenho de então:
- Objetivo: **reproduzir fielmente o preço atual**, modelar oferta × demanda (indicador de desequilíbrio/*imbalance* por região/tempo), propor política dinâmica `preço_base × multiplicador(imbalance)` com `cap_min ≤ multiplicador ≤ cap_max`, e **simular contrafactual** (março/2024).
- Preço então: função do valor por km, **bandeirada** e **minuto parado/espera**; premissa "motorista aceita todas as corridas".
- Código (branches `analise-engenharia`, `analise-ticket-km`, `analise-pf-cupom-elias` etc.): `src/etl/[01] csv_to_parquet.py`, `[02] transform_app_solicitacao_hist.py`, `[03] build_features_rides.py` (lista de ~40 colunas de `APP_SOLICITACAO_HIST`; `price_threshold` 20 R$) e `src/pricing/{current,dynamic,simulate}.py` — **os três arquivos de pricing aparecem vazios nas branches inspecionadas** (0 byte) e foram removidos de `feature/sigma` ("Remove obsolete ETL scripts and pricing modules"). Ou seja: o plano de simulação contrafactual de 2025 **não chegou a ser implementado em código** nesta árvore.
- Branch `sigma` (03/2026) tem `notebooks/preco-base/` (`analise_dinamico_vs_fixo`, `analise_novo_preco_base`, `preco_base.csv`) e `Avaliacao_final_ano/avaliacao_2025.ipynb`; `development` fundiu o PR "Preço base v1 viagens" (23/08/2026).

## 8. API Sigma — alavanca de preço dinâmico

`POST /sigma/altera-preco` com `{"novoValor": número >= 0}` altera manualmente o **valor de preço dinâmico em produção** (resposta: `Preço dinâmico processado com sucesso.`). O cliente (`SigmaClient.alterar_preco`) tem barreira dupla: `DRY_RUN=True` no script e `confirmar=True` obrigatório. **Ainda não há automação** ligando o motor de preço a essa chamada (próximo passo sugerido no README: "plugar o motor v2"). Ver [07](07_frota_e_operacao.md) §6.

## 9. Elasticidade e curva de aceite (C8)

`08_preco_km_elasticidade_pf.sql` muda a unidade de análise para a **cotação** (não a corrida encerrada, que só tem quem aceitou) e marca conversão por `e.CD_ESTIMATIVA = h.CD_ESTIMATIVA`. Saídas em `outputs/elasticidade_preco_pf.xlsx` (abas: Resumo, Dados_Faixa, Elasticidade, Simulacao_Preco, Recuperar_Aceite, Viagem_Longa, Serie_Diaria, Qualidade_do_Dado). O deploy de junho dá **um ponto** na curva, na direção errada; falta teste dimensionado antes de repetir cortes pequenos de margem.

## 10. Armadilhas de leitura (do diagnóstico)

1. **Viés de mix no ticket:** o ticket sobe sozinho quando a corrida barata some. Usar ticket *same-store*.
2. **Post hoc:** junho no ES tem inverno, chuva e férias; DiD + placebo transforma coincidência em evidência.
3. **Usuário interno** (`TX_LOGIN LIKE '%mobicity%'`) cota e não pede, derrubando conversão.
4. **Frota utilizada ≠ disponível:** `APP_SOLICITACAO_HIST` só vê o carro quando ele roda; usar `NaoAtendida`.
5. **Mês parcial:** média diária.
