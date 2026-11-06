# 10 — Lacunas, perguntas abertas e contradições

Regra do repositório: **não inventar resposta** para o que exige dev, FP&A ou operação. Esta lista consolida o que os documentos marcam como aberto, mais as inconsistências que encontrei entre eles.

## 1. Perguntas ao dev / produto

| # | Pergunta | Por que importa | Fonte |
|---|---|---|---|
| D1 | Data/hora exata do deploy do preço real (~13/06/2026); rollout gradual ou de uma vez; houve rollback/ajuste; PJ Customizado e Prime realmente não foram tocados? | Todo o DiD depende do controle estar limpo | `o_que_falta_buscar` §1 |
| D2 | Como `NU_DR_REAL` e `NU_TEMPO_DR` são gravados (cotação ou rotina pós-corrida)? Por que só 52% preenchidos? Há alguma fonte de retorno real (telemetria/GPS)? | Define se o km morto é observável ou premissa permanente | CLAUDE §abertas 1; `o_que_falta_buscar` §2b |
| D3 | Por que `valor_bruto − valor_cotado` = −R$ 4,20 em média, com inclinação zero vs tempo? Em que momento o bruto é fixado e o que entra? | Se a fórmula em produção ≠ `equacoes.md`, simulações ficam inválidas | `o_que_falta_buscar` §11; `c4_achados` §4 |
| D4 | Como o sistema calcula o **Minuto parado** que cobra, se não há marco entre `CorridaIniciada` e `CorridaEncerrada`? | Cláusula existe e não é medida no log | CLAUDE §abertas 4 |
| D5 | Parâmetros vigentes da fórmula e os de antes de 13/06; banda e condição de acionamento do σ | Atribuir efeito a parâmetro | `o_que_falta_buscar` §2 |
| D6 | `NU_ETA_TEMPO_PROXIMA_SEGUNDOS`: retorno à base ou ETA da próxima corrida? | Uso atual assume a primeira | DICIONARIO §8.4 |
| D7 | Há sentinela (`-1`, `0`) para "não calculado"? | Guardas `> 0` ficam por precaução; não confirmado | DICIONARIO §7 |
| D8 | Cupom: "50" e "100" são R$ ou %? Quem aprovou o de 100? O cupom respeita o piso (P*)? | Regra de ouro | `o_que_falta_buscar` §12 |
| D9 | Significado de `DE_VO`, `DE_VV`, `DE_IV_REAL` (colunas de `APP_SOLICITACAO_HIST` usadas no ETL de 2025) | Não documentado | `build_features_rides.py` |
| D10 | Quando exatamente a solicitação é criada; autoria e regras de cancelamento; `LimiteEsperaAtingido`; por que `CorridaCanceladaOperador` explodiu em jul/2026 | Demanda por hora, D+1 | TCC §7 |

## 2. Perguntas ao FP&A

| # | Pergunta |
|---|---|
| F1 | Parâmetros de custo de **PF** (R$/km, R$/min): parâmetro único global por decisão ou PF nunca teve custo próprio? Hoje usa-se **0,97–0,969 R$/km e 0,33 R$/min emprestados do PJ** (e `equacoes.md` usa 1,10 e 20 R$/h; a branch de metas usa R$ 2,50/km) |
| F2 | Rateio administrativo por corrida e critério; custo do motorista por minuto **alocado** |
| F3 | Custo do carro dedicado (mensalidade, motorista fixo, ociosidade) — adiado por decisão em 20/08 |
| F4 | 74% das corridas PF sem ISS (alíquota 9,25) — regime ou campo não preenchido? |
| F5 | Taxas unitárias (τ MO/GG/MT) usadas no rateio da BD — "não documentadas" |
| F6 | Planilha financeira original (custos por corrida) citada no README de `custos_operacao_v1` não está na árvore |

## 3. Perguntas à operação / RH / comercial

- Que operação é a **"escala fantasma"** (27% das jornadas, quase todas sem corrida)? (`11:00-21:00 4X2` = 100% sem corrida em 597 jornadas; `05:00-15:00 5X2` = 99,7% em 923.)
- Amostra de 20–30 **transbordos Prime** conferidos com a operação (fecha a hipótese de despacho).
- Política atual de **despacho/espera/reposicionamento**; local de espera pós-desembarque; autorização para mover carro vazio; adesão do motorista.
- **SLA contratado** com clientes PJ (tempo máximo de espera, frota mínima) — está em PDF de contrato, não no banco.
- Carros simultâneos do plano **Familiar**: 3 / ilimitado / 2.
- Por que 74 contratos ativos × 171 usuários Prime com corrida.
- Quanto da espera Oiltanking é atraso do cliente e quanto antecipação nossa (`espera_agendamento_pj.sql` — a rodar).
- Frota: exclusividade (agregados, aluguel), capacidade/acessibilidade, manutenção, fuso dos timestamps (sem offset).

## 4. Lacunas de dado estruturais

1. **Retorno / KM morto não medido** (premissa). Rodagem total só mensal por placa.
2. **Disponibilidade real da frota** não é observável no retrovisor; a API Sigma dá só o estado atual (coletor de 5 min existe em branch, sem série).
3. **Demanda suprimida** não medida (cotações sem pedido, `NaoAtendida`) em PJ.
4. **Horário pedido do agendamento** (`APP_AGENDAMENTO`) não explorado.
5. **Motivo de cancelamento / reclamação** não está no banco (SAC/NPS/WhatsApp, se existirem, estão fora).
6. **Chave de motorista conflitante** entre jornada e status.
7. **Cobertura de coordenadas** (varchar anulável) e fuso.
8. **Série pós-deploy curta** (6 semanas): repetir em 30 dias antes de decisão estrutural de preço; sem controle de 2025 (junho–julho/2025 pedido como checagem sazonal).

## 5. Contradições e armadilhas de documentação (encontradas ao cruzar fontes)

| Tema | O que um documento diz | O que outro diz / achado |
|---|---|---|
| Corte do preço fixo | `dicionario_metricas.md` fala em **30 km** | Parâmetro do sistema é **10 km** (`NU_KM_PRECO_FIXO = 10.000 m`) — refutado |
| Queda do funil | −22,4 pp (como medido) | −10,6 pp corrigido; 53% era artefato |
| Frota Prime | 18 placas (planilha 17/08), 21 (`BL_PRIME`) | **23** (centro 300590260, confirmado pela operação) |
| `capacidade_prime/README.md` §1 | Mostra pico 17 / frota 18 / 1.241 transbordos | Válido: pico 14 / frota ativa 17 / 313 transbordos (resíduo conhecido, não corrigido) |
| Jornada | 9,15 h (inferida) / "8 h chute" | 11,67 h realizada; carga contratual 7 h 20 ou 8 h 48 |
| Dedup | Padrão: `DT_INICIO_REALIZADA DESC, DT_REGISTRO DESC` | Funil usa só `DT_REGISTRO DESC`; `km_faturado_por_placa.sql` **não deduplica** |
| Espera | Tarifa de "minuto parado" usada como espera | Cláusulas distintas; números a refazer |
| "Usiminas sem cláusula de espera" / "cláusula de parado precisa ser criada" | Afirmado | Invertido pela descoberta das duas cláusulas |
| `custos_operacao_v1` | Tem `docs/definicao_colunas.md` | README ainda lista planilha, notebook e `transformacao.py` como "próximos arquivos a criar" |
| `scripts/sql_pipeline/README` | Diz que o módulo generaliza o padrão | O `regenerar_dados.py` da frota está **à frente** (token Azure AD, `.env`, execução única, `ARITHABORT`) |
| `sql/31_disponibilidade_por_placa.sql` | Marcado para `to_delete/` e depois restaurado | Em uso (gera `31_prime_01..04`) |
| `RESUMO_PRIME` (causa do transbordo: "6%", "81% com motorista apto") | Apresentado como achado fechado | A `AUDITORIA_DADOS_E_CALCULOS.md` (11/09) tem seção "O indicador *apto* não mede aptidão operacional" — ler antes de citar |
| `development` × HEAD | `development` parece pai | Tem 3 arquivos que o HEAD não tem (CSV centro de custo, `99_investigar_lacunas.sql`, `.docx`) |
| Nome da empresa | `V1 Viagens`, `V1 Mobilidade`, `V1`, `App V1` | Usados como sinônimos |
| Datas | Branches de 2025 são `2025-09…11`; análises de preço/frota são `2026-06…10` | O relatório "Prioridade threshold km" e "plano de ação" são de **2025-10** (LaTeX) |
| Tempo do repo | `CLAUDE.md` atualizado em `2026-08-20` | O HEAD contém trabalho de set–out/2026 que não está refletido no `CLAUDE.md` (aeroporto, TCC, Prime corridas seguidas) |

## 6. Números aposentados (não citar)

13,3% e 16,1% (transbordo mai–jul) · 25,9% (agosto pela planilha) · 20,2/79,8 e 32,9/67,1 (causas de transbordo) · 35,5% (jornadas ociosas; real 10,1%) · 9,15 h (jornada) · −22,4 pp / 61,7%→39,4% (funil, sem correção de fluxo) · R$ 147.538, R$ 199.161, R$ 36.119, 17,2%, inclinação 0,55 (espera valorada pela tarifa de minuto parado) · "teto de 145–160 corridas/dia" (artefato de só olhar julho) · "20,2%/79,8%" · qualquer percentual de ociosidade que misture hora inteira com minuto ocupado sem declarar.

## 7. Limitações desta documentação

- Não abri `.xlsx/.pdf/.tex/.docx`; números de planilhas vêm dos READMEs/TCC.
- Não li integralmente `roteiro_investigacao.md`, `dicionario_metricas.md`, `PENDENCIAS.md`, `AUDITORIA_DADOS_E_CALCULOS.md`, `capacidade_prime/README.md`, `ocupacao_frota/README.md` — usei títulos e trechos. Para citar números de causa/transbordo em apresentação, **ler a auditoria de 11/09/2026 antes**.
- Das ~25 branches, li a documentação principal; os notebooks `.ipynb` e a maioria dos `.sql` de 2025 foram inventariados por nome, não analisados célula a célula.
- Nada foi reexecutado: toda cifra é "segundo o repositório".
