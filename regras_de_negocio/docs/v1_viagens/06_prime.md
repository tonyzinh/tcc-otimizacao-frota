# 06 — V1 Prime

**O que é:** produto de **assinatura de horas com frota dedicada** (Grande Vitória). O cliente contrata um plano com franquia de minutos por ciclo mensal; cada corrida debita minutos. Tratado nas análises como "pessoa física" para fins de transbordo, e **excluído** (`TX_MODELO_SOLICITACAO = 'Prime'`) das análises de preço PF/PJ.

Pastas: `analises/prime_corridas_seguidas_v1/`, `analises/prime_monetizacao_v1/`, `analises/frota_dedicada_pj_v1/capacidade_prime/` e `ocupacao_frota/` (no HEAD); `planos_prime_v1`, `ociosidade_frota_prime_v1` (branch `analise-v1-prime`); `simultaneidade_prime_v1` (branch `painel-simultaneidade`).

## 1. Modelo de dados Prime (VERIFICADO, rodada de exploração de 28/09 e 06/10/2026)

39 tabelas e 5 views com "PRIME" no nome (44 na contagem da branch de planos).

```text
APP_PLANO_PRIME (147 → catálogo; franquia, qtd dependentes, valor)
  └─ APP_PLANO_USUARIO_PRIME (693 contratos)  ── CD_USUARIO_PRIME ──> SEG_USUARIO_PRIME (456 titulares)
       ├─ APP_PLANO_DEPENDENTE_PRIME (430) ── CD_USUARIO_PRIME_DEPENDENTE ──> SEG_USUARIO_PRIME_DEPENDENTE (185)
       ├─ APP_CICLO_PRIME (2.122, período mensal de franquia; ciclos futuros pré-gerados até 2028, status 'Pendente' 14,5%)
       │    └─ APP_CONSUMO_CICLO_PRIME (28.404) ← uma linha de débito por corrida
       └─ LOG_PLANO_USUARIO_PRIME (195; troca/pausa de plano)
APP_SOLICITACAO_HIST: TX_TIPO_PRIME, CD_ESTIMATIVA_PRIME → APP_ESTIMATIVA_PRIME (32.679)
Cobranças extras: APP_DESPESA_ADICIONAL_PRIME (516), APP_SERVICO_ADICIONAL_PRIME (99)
Views: VW_GESTAO_CONSUMO_PRIME, VW_GESTAO_CONSUMO_PRIME_PASSAGEIROS, VW_RELATORIO_FATURAMENTO_PRIME, VW_CONTRATO_PLANO_PRIME
```

Fatos:
- `CD_USUARIO_PRIME` → `SEG_USUARIO_PRIME`, **não** `SEG_USUARIO` (não casa com `h.CD_PASSAGEIRO`; os "casamentos" de 4,4% da rodada 1 eram colisão — RS7 inválido).
- **Renovação cria contrato novo** (693 contratos para 311 titulares); `CD_PLANO_USUARIO_PRIME_INICIAL` preenchido em 27,3%.
- Status de contrato: Encerrado 57,1% · Desativado 31,7% · **Ativo 10,7% (74)** · AguardandoPagamento 0,4%. 41,4% têm ≥1 dependente (máx. 10). Registro de teste: contrato 701, R$ 0,01.
- Franquia do ciclo (`NU_MINUTO_CICLO`): 60 a 3.000 min; moda 600 (31,8%).
- Na janela 28/08–27/09/2026, corridas `Prime` na HIST: 1.976 corridas, 137 passageiros.

### Como a cobrança funciona (set/2026, 2.012 corridas Prime encerradas)
- Toda corrida Prime encerrada tem **exatamente 1 linha de consumo ativa** (`TX_TIPO='Debito'`); 2.012/2.012.
- **A cobrança vai de `CorridaIniciada` a `CorridaEncerrada`**: o cliente paga só o tempo com passageiro (início/fim batem com o log em 100%).
- `NU_MINUTO_CONSUMIDO` = minutos de viagem arredondados (igual a `round(Min_Viagem)` em 98,6%).
- **Débito real** = `CONSUMIDO + ESPERA_EMBARQUE + FORA_REGIAO_ORIGEM + FORA_REGIAO_DESTINO + CANCELAMENTO` = `NU_SALDO_ATUAL − NU_SALDO_FINAL` (100% das 2.041 linhas de débito; mesma soma da view `VW_GESTAO_CONSUMO_PRIME`).
- `NU_MINUTO_TOTAL_FORA_REGIAO_DESTINO` **não** é debitado (≈ 2 × FORA_REGIAO_DESTINO + 1).
- Espera cobrada em 109 corridas (5,4%); cobrado < medido sempre (mediana 44 min a menos). **Pickup pago pelo cliente = 2,6% do pickup medido** (38,7 h de 1.472 h) — o pickup é custo quase todo da V1.
- Cancelamento só aparece em solicitação não encerrada (24 linhas, 217 min). `Credito` (14 linhas) = horas compradas.
- Em R$: ciclo (`APP_CICLO_PRIME.DE_VALOR_CICLO`; excedente `NU_MINUTO_EXCEDENTE`, `DE_VALOR_HORA_EXCEDENTE_TOTAL`, `DE_VALOR_MULTA`) + `APP_DESPESA_ADICIONAL_PRIME` (HoraAdicional, HoraExcedente, CancelamentoPlano, MultaCancelamento).
- **42,3% dos contratos são pagos com cartão corporativo.** Maior saldo herdado por um ciclo: 7.896 min (2,6 franquias máximas).

## 2. Catálogo de planos (branch `analise-v1-prime`, 17/09/2026)

- `APP_PLANO_PRIME`: 150+ linhas históricas; **60 com `DT_DESATIVACAO IS NULL`; 32 com contrato ativo**. Muitos são negociações pontuais, a maioria desativada numa limpeza em massa de **13/05/2026**; reorganização de catálogo em **02/04/2026**.
- **Cota está no nome:** Start 5 h = 300 min · Individual 10 h = 600 · Essencial 15 h = 900 · Plus 20 h = 1.200 · Familiar 30 h = 1.800 · Corporativo 40–50 h = 2.400–3.000.
- **74 contratos ativos**, concentrados na entrada: 10 h = 39,2%, 15 h = 29,7%, 5 h = 17,6%; 30 h+ quase inexistente. 29 dos 74 (39,2%) já estão nos planos novos.
- **Planos públicos hoje** (confirmado no site em 17/09/2026): Individual (cód. 116, 10 h, 1 dep., 11 contratos), Essencial (124, 15 h, 2 dep., 5), Plus (132 [6 meses] / 134 [12 meses], 20 h, 3 dep., 2+1), Familiar (138, 30 h, 4 dep., 1). Outros: variantes de prazo (3/6/12 meses), legados (14, 2, 71, 85), internos (24 "Embaixador", 25 "Operação Prime" — R$ 0,00, não pagante).
- `APP_PARAMETRO_PRIME` é **regra operacional global** (1 versão vigente, histórico de 8), com **antecedência mínima de agendamento = 45 min**; 0,81% das corridas ficam abaixo de 30 min (portanto abaixo do mínimo oficial — ABERTO).
- **Gap aberto:** 74 contratos ativos × 171 usuários com corrida Prime encerrada em 01/05–14/09 (dependente anda sob contrato de outro; contrato encerrado no meio do período; causa não investigada).
- **Carros simultâneos do Familiar:** 3 (material de vendas), "Ilimitado" (site), "até 2" (FAQ) — **conflito a resolver com o comercial** antes de qualquer desenvolvimento.

## 3. Corridas seguidas (`prime_corridas_seguidas_v1`, em andamento)

Pergunta: quantas vezes uma corrida de um plano Prime foi **seguida de outra do mesmo plano em até 30 min**. `N = Σ_p Σ_i 1[g_i ≤ 30]` com `g_i = ini_{i+1} − fim_i` (par consecutivo). Decisões em aberto D1–D6 (início do intervalo [fim→início recomendado], qual corrida é "do plano", vigência [na data da corrida], unidade [par], sobreposição `g<0` [separar], "mesmo plano" [cadeia de renovação/titular]). **A consulta final `sql/02_corridas_seguidas_plano.sql` ainda não existe.** Viés de exposição: plano com mais membros gera mais pares → reportar `N_p/(n_p−1)`. Há ainda `docs/regra_simultaneidade/` (PDF/DOCX `regra_simultaneidade_prime_v1`) e painel `prime_preco_hora_set2026.html`.

## 4. Simultaneidade (branch `painel-simultaneidade` / `analise-v1-prime`)

Casos em que titular **e dependente do mesmo plano** tiveram 2+ carros ao mesmo tempo (modo *Simultaneidade*) e casos da **mesma pessoa em 2 carros ao mesmo tempo** (*Auto-sobreposição*; perto de 100% de sobreposição cheira a registro duplicado, parcial cheira a conta compartilhada). Mede por **ocupação de frota** (não só viagem real). Janela de exemplo 15/07–24/09/2026, 3.930 corridas Prime, cobertura de coordenada 100%; **100 ocasiões** de simultaneidade familiar (2 com 3 carros) e **85 grupos** de auto-sobreposição (valores da branch `analise-v1-prime`, 22/09). HTML autocontido com Leaflet 1.9.4 e basemap CARTO (chave gratuita; sem chave, marca d'água). Autor: Marcelo Passamai Marques.

## 5. Monetização (`prime_monetizacao_v1`, rascunho v0 de 28/09/2026 — consultas escritas e **não executadas**)

Ideias: horário ocioso, franquia e acúmulo, anual pré-pago, dependente/simultaneidade, plano corporativo, aquisição e retenção. Entregas: `monetizacao_prime_v0.pdf` (11 págs), `acumulo_horas_prime_v0.pdf` (5 págs), consultas `01_ocupacao_prime_hora_dia`, `02_uso_franquia_excedente_saldo` (rodar o RS0 primeiro: confere a semântica de minutos), `03_retencao_safra`, `04_catalogo_planos_precos`, `05_top_pj_perfil_prime`; simulador `src/acumulo.py`.
- **Ociosidade (existente):** 15.012 hora-motorista com presença a hora inteira (01/05–25/08/2026); **3.086 sem corrida (20,6%)**; ocioso no pico da manhã útil (6–9 h) 10,3%; no meio do dia útil (10–15 h) **19,3% = 11,9 hora-motorista/dia**.
- **Decisões em aberto:** carros simultâneos do Familiar; regra de acúmulo (recomendação: 1 ciclo com 60 dias, saldo usado primeiro, com pausa e aviso); ocupar o vale 13–16 h (testar primeiro o ajuste de escala, mais barato que vender a hora); anual pré-pago (com renovação automática, desconto abaixo do equilíbrio, oferta controlada para medir viés de seleção).

## 6. Ociosidade da frota Prime (branch `analise-v1-prime`, pergunta de 18/09/2026)

"Se num intervalo de 1 h eu tenho 15 h de frota por conta de 15 motoristas, quantas horas foram utilizadas e não utilizadas?" Entregável: heatmap hora × dia da semana (HTML). Período 01/05–14/09/2026 (138 dias): **17.742 horas de frota, 12.784 utilizadas (72,1%), 4.958 não utilizadas (27,9%)**. Mais ocioso: 00–02 h (66–79% em dia útil) e 22–23 h (45–49%); menos: 07–08 h e 17–18 h (8–16%). Ocupação conta de `CondutorACaminho` ao fim da corrida. A definição alternativa de **"minuto ocupado"** dá **53,5%** de ociosidade (isolada à mesma população: 27,9% → 52,1%) — responde outra pergunta ("quantos minutos rodou com passageiro?"), por isso é filtro opcional. Fonte da verdade continua `capacidade_prime/presenca_ociosos.py` (já corrigiu 3 bugs: ocupação a partir do embarque dobrava a ociosidade; "toca a hora" × "cobre a hora inteira"; namespaces de `CD_MOTORISTA`). Risco registrado: frota resolvida pelo cadastro **atual** da placa aplicado retroativamente (placa SGH9C62: 31 cadastros, 20 corridas Prime contra 101 de outras frotas); `01_risco_frota_por_data.sql` mede e **ainda não foi rodada**.

## 7. Capacidade da frota Prime — a resposta (resumo; detalhe em [07](07_frota_e_operacao.md))

1.721 corridas Prime encerradas, região 1, 01–25/08/2026, **frota de 23 placas** do centro de custo `300590260`. **Não é preciso comprar carro nem (principalmente) contratar motorista**; o problema é **despacho**: 81% dos transbordos aconteceram com carro parado e motorista apto. A pergunta mudou para: *a frota atual está dimensionada acima da demanda Prime, e o que fazer com a folga?* (depende de contrato e nível de serviço, que não estão no banco).
