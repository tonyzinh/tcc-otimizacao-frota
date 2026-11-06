# 04 — Pessoa Física (PF)

PF = `h.CD_EMPRESA IS NULL`. **Só existe na região 1** (Grande Vitória): 76.956 solicitações PF em 124 dias (01/04–02/08/2026), todas `CD_REGIAO = 1` (VERIFICADO 03/08/2026, C10 RS0). `h.CD_REGIAO = 1` é redundante em consulta PF (mantê-lo documenta a intenção). `CD_TIPO_SERVICO` é sempre 1 em PF (0 linhas com outro valor).

Pastas: `analises/pessoa_fisica/` (01–04), `analises/funil_conversao_v1/`, `analises/marketing_segmentation/`, e consultas `sql/pf_*.sql`.

## 1. Funil de conversão (estimativa → solicitação → corrida)

`analises/funil_conversao_v1` + `sql/funil_conversao.sql`. Série 01/04–02/08/2026 (124 dias), PF região 1 não-Prime.

- **Pergunta motivadora:** a redução de margem de 30/07/2026 moveu o resultado? **Não.** Aceite ficou em 37,8% e conclusão em 37,3% — dentro de 1 desvio-padrão (janela de apenas 4 dias, "poucos").
- **A perda é de oferta, não de preço no aceite:** `NaoAtendida` ≈ 57% de tudo que não vira corrida; com `LimiteEsperaAtingido`, oferta explica ~62%; desistência do cliente ≈ 34%. A perda acontece **entre pedir e rodar**.
- **Não há "muro de capacidade":** a frota já entregou 392 corridas num dia; ~285/dia nos dias de maior demanda; a fricção cresce suave (não atendida sobe de ~25% para ~36% do quintil baixo ao alto de demanda). A leitura anterior (teto em 145–160/dia) era artefato de usar só julho.
- **O que moveu o funil foi o preço real de ~13/06** (ver [03](03_precificacao.md) §4), com o efeito corrigido de −10,6 pp (não −22,4).
- **Ressalvas operacionais:** (a) a data de cada etapa vem de `DT_REGISTRO` = carimbo do status **final** (corrida pedida 23:50 e encerrada 00:10 conta no dia seguinte); (b) o dedup do funil ordena só por `DT_REGISTRO DESC` (divergência do padrão do repositório, mantida para não deslocar números circulados); (c) a ressalva "`APP_ESTIMATIVA_PRECO` sem `CD_REGIAO` ⇒ piso" foi **cancelada** em 03/08 (PF só região 1).
- **Anomalia:** `CorridaCanceladaOperador` de 0,1/dia (maio) a 3,7/dia (julho), pico 21 em 31/07 — perguntar à operação.
- **Excel** (`outputs/funil_conversao_analise.xlsx`, gerado por `src/gerar_excel_funil.py`): abas Resumo, Perda_Pos_Pedido, Blocos_QuiDom, Pareado_DiaSemana, Serie_Semanal, Motivos_Nao_Atendimento, Quebra_Preco_Junho, Capacidade_e_Demanda, Dados_Diarios. Sem gráficos embutidos de propósito (openpyxl + série longa trava o recálculo do LibreOffice; perfil persistente do LibreOffice leva 0,8 s contra ~30 s).

## 2. Ciclo físico da corrida PF (C4) — ver também [02](02_modelo_de_dados.md) §3–4 e [03](03_precificacao.md) §1

Principais achados (n = 1.023, 23–29/jul/2026):
- Erro de tempo **é de pickup e espera, não de trânsito**: deslocamento até o cliente +2,16 min (32%), espera +3,80 min (57%), viagem **−0,75** (11%, super-estimada). "O trânsito quebrou o preço" não se sustenta nesta janela; é problema de **frota e alocação**.
- **Agendamento** (159 corridas, 15,5%): espera mediana 10,6 min × 0,82; 73,3% do tempo alocado não faturado; R$/h levemente melhor (63,15) mas frota sequestrada.
- **Cupom** (527 corridas, 51,5%): desconto efetivo 10,3%; R$/h de frota cai de 65,22 para 58,12.
- Faixas de distância (n, ticket, % km não faturado, R$/h, erro de tempo): ≤2 km (148; 20,56; 76,1%; 60,30; +4,32) · 2–4 (314; 24,52; 60,1%; 58,89; +5,05) · 4–6 (194; 34,67; 51,6%; 58,41; **+6,83**) · 6–10 (221; 41,15; 40,7%; 60,95; +6,51) · 10–15 (89; 56,39; 41,3%; 61,46; +4,41) · 15–25 (47; 71,93; 41,5%; 65,25; −1,43) · 25+ (10; 200,11; 41,4%; 81,39; +2,00). **O maior erro de tempo está no miolo (4–10 km), não na ponta curta.**
- Retorno (quando existe): mediana 4,07 km contra 4,69 km de viagem — "quase uma segunda corrida que ninguém paga" (mas é derivado da estimativa).
- Ressalvas: uma semana, PF região 1, custos 0,969/0,33 de empréstimo do PJ; margem bruta da semana 37,9%, 2,3% das corridas com margem negativa.

## 3. Composição de preço e MC02 por cotação (C7) e prejuízo por desconto

`07_composicao_preco_mc02_pf.sql` → `outputs/composicao_preco_mc02_pf_julho.xlsx` (Resumo + Dados 5.212 × 34). Nas 5.211 corridas PF de julho (até 29/07): **as 129 corridas com MC02 negativo têm desconto — 100%**; nas de margem positiva, 66,5%. Mecanismos mutuamente exclusivos na amostra: cupom (62 corridas; valores 50→47×, 40→14×, **100→1×**), parceria (30; 40% e 30%), colaborador (37; 40% e 30%). MC02 médio por desconto de produto: R$ 14,70 (sem), R$ 13,48 (30%), **R$ 6,79 (40%)**; a faixa de 40% concentra 751 corridas. As 129 somam **−R$ 386** contra R$ 70.060 de MC02 do mês: financeiramente é ruído; o valor do achado é o **mecanismo** (existe caminho de configuração comercial que fura o piso sem trava). Perguntas: quem aprovou o cupom de 100; se 50/100 são R$ ou %; quais parceiros; se o cupom respeita o piso (a regra de ouro). `BL_PERCENTUAL_DESCONTO_CUPOM` na tabela fixa e `APP_CUPOM_DESCONTO.BL_PERCENTUAL` resolvem R$ × %.

## 4. Comportamento, retenção e CRM (`01_comportamento_pf`)

- **Base canônica:** `dados/intermediario/corridas_finalizadas_pf_tratada.csv` (gerada por `analises/02_tratamento_e_qualidade.ipynb` + `src/tratamento.py`).
- Camadas `src/`: `utils.py`, `tratamento.py`, `features.py` (overview, resumo mensal, agregação por cliente, retenção por etapas, cohorts, mix de segmentos, tendências), `recorrencia_retencao.py`, `clusterizacao.py`, `target.py` (reservado; `docs/definicao_target.md` e `docs/hipoteses.md` são **modelos em branco**, não definições).
- Notebooks: `03_analise_exploratoria_preco`, `03_analise_exploratoria_usuarios`, `04_analise_cupons`, `05_analise_fidelidade_heavy_users`, `06_evolucao_usuarios_corridas`.
- **Clusterização KMeans** (snapshot 04/04/2026; 11.394 usuários; 4 clusters; só **23,49% ativos nos últimos 30 dias**, 76,51% sem corrida há >30 dias, 64,69% há >60 dias):

| Cluster | Usuários | Ticket | Corridas/mês | Recência | Leitura / ação sugerida |
|---|---|---|---|---|---|
| 0 Heavy users ativos | 2.677 (23,5%) | R$ 42,70 | 2,08 | 12,1 d | Fidelizar; VIP sem excesso de desconto |
| 1 Recorrentes promocionais em desaceleração | 3.764 (33,0%) | R$ 43,28 | 0,79 | 139,9 d | Alta dependência de cupom; "desmame de incentivo" |
| 2 Premium noturnos em reativação | 2.254 (19,8%) | R$ 67,12 | 0,21 | 237,2 d | Reativação premium personalizada |
| 3 Ocasionais de horário comercial | 2.699 (23,7%) | R$ 48,67 | 0,21 | 236,6 d | Oferta utilitária ida-e-volta |

- **Estratégia de CRM** (`estrategia_crm_pf/`): segmentação por valor e risco de evasão, 6 segmentos prioritários, listas exportadas (`gerar_listas_segmentos.py`, `executar_crm.py`). Contém dados pessoais — **não versionar listas**.
- Gênero predito por nome: modelo `modelo_genero_nome.joblib` (em `marketing_segmentation/modelos/`), consumido pelo `01_comportamento_pf`.

## 5. Marketing / segmentação (`analises/marketing_segmentation` e branch `avaliacao-pf-Isllan`/`sigma`)

Notebooks `pre_pro_seg_marketing`, `ml_segmentacao_marketing`, `analise_seg_marketing`; SQL `extracao/` (`ext_marketing_pf_2025.sql`, `ext_marketing_pf_pj_tipo_preco.sql`, `ext_solicitacao_hist_nome(_idade).sql`), `validacao/` (`val_ext_marketing_mes_a_mes_pf`, `_pf_pj_2025`, `_usuario`), `teste/`. Escopo 2025, Grande Vitória, **exclui Prime**. Branch `avaliacao-pf-Isllan` acrescenta análise de **comportamento PF por faixa de distância × gênero × faixa etária** (jan–set/2025): faixas A 0–3 km, B 3–6, C 6–10, D >10; faixas etárias A 13–17 … G 65+; períodos madrugada/manhã/tarde/noite; métricas: corridas, receita recalculada, ticket médio, ticket/km.

## 6. Novo preço (PF + PJ) e segmentos — `03_novo_preco`

`sql/consolidado_novo_preco_mar_jul_2026.sql` roda 9 consultas (um RESULT SET cada) que alimentam `analise_consolidada_novo_preco_mar_jul_2026.xlsx` (Resumo Executivo, Segmentos, PF-Grupos, PF-Grupo×Subsegmento, **PF-Heavy Users** [446 linhas], PJ-Top10 Todas Regiões, PJ-Top10 Região 1, PJ-Migração). Há versão mar–jun. Consultas relacionadas: `faturamento_por_segmento_mar_{jun,jul}_2026.sql` (PF Sem Cupom / Com Cupom / Com Parceria / PJ Padrão / PJ Customizado), `pf_grupos_intensidade_subsegmento_*`, `pf_heavy_users_*`, `pj_top10_clientes_faturamento_*`, `pj_migracao_customizado_padrao_*` (clientes que **migraram de Customizado para Padrão**), `faturamento_diario_pf_pj_regiao1_30jul_02ago2026.sql`. **Contêm dados de pessoa — não usar no documento.**

## 7. Acurácia da precificação (`04_acuracia_precificacao`)

EDA de acurácia estimado × real (erro de km e tempo) e sub-estudo de **tolerância PF** (`acuracia_tolerancia_fisica`) com PDFs executivos. Resultados-chave estão em [03](03_precificacao.md) §1/§3. `02_preco_minimo_pf`: simulador (`plot_simulator.py`, `plot_helpers.py`), base `preco_min.csv` e notebook `analise_Preco_min_PF_vitor.ipynb` (branch `sigma` o guarda como `analise_precos_min`).

## 8. Aeroporto (consultas mais recentes — set/out 2026, commit `c445050`)

Seis consultas em `sql/`: `pf_corridas_aeroporto_set2026.sql`, `pf_corridas_aeroporto_madrugada_set2026.sql`, `pf_corridas_aeroporto_detalhe_jul_set2026.sql`, `pf_corridas_aeroporto_madrugada_detalhe_jul_set2026.sql`, `pf_clientes_aeroporto_madrugada_jul_set2026.sql`, e `pf_top20_clientes_{set,por_mes_jul_set}2026_regiao1.sql`. Identificam corridas com aeroporto como origem/destino por **texto de endereço** (`TX_ORIGEM`, `TX_DESTINO_REAL`, `TX_DESTINO`) e trazem o top 20 de clientes (nome, e-mail via `SEG_USUARIO.TX_LOGIN`, nascimento, telefone, gasto líquido de cupom). *Conteúdo individual — dado pessoal.* A motivação de negócio não está documentada nos arquivos (INFERIDO: avaliar demanda de aeroporto/madrugada e relacionamento com maiores clientes). Há um `sql/test.sql` não rastreado no working tree.

## 9. Outras análises PF só presentes em branches (ver [08](08_branches.md))

- **Cancelamento e demanda reprimida** (`demanda-cancel-Isllan`, `analise-demanda-reprimida-tony`): heatmaps de cancelamento por dia × faixa horária, motivo, perfil (PF/PJ Padrão/PJ Customizado), faixa de valor e distância; comparação jan–ago × set/2025; deduplicação por intervalo de 30 min; intervalo configurável de 120 min; filtros: região 1, exclusão de Prime.
- **Fixo × dinâmico, faixa de km, cupom bruto, receita comparativa 2024×2025** (`analise-pf-lara`).
- **PF × cupom** (`analise-pf-cupom-elias`), **queda de receita por PJ** (`analise-queda_receita_por_pj-elias`).
- **Bairros/H3** (`analise-bairro-isllan`): corridas PF encerradas, Grande Vitória, valor >R$ 500, jan–out/2025, convertidas em hexágonos H3 (resolução 8 padrão) com mapa Folium.
- **Projeção de metas** (`projecao-metas-Isllan`): projeção geral/mês/hora e por carro (6 conjuntos de resultados) por PF/PJ Padrão/PJ Customizado; parâmetros: 01/01–01/10/2025, região 1, UF 'ES', corridas encerradas, sem Prime; **custo operacional assumido = distância total × R$ 2,50** (premissa diferente das de 0,97/1,10 do restante).
