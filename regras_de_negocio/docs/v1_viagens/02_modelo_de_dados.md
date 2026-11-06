# 02 — Modelo de dados (SQL Server / Azure SQL)

Fonte principal: `sql/DICIONARIO_BANCO.md` (v1.0, 29/07/2026) e `CLAUDE.md`, mais as ~830 consultas do repositório. Banco **Azure SQL com autenticação Entra ID**, dialeto **T-SQL**, esquema `dbo`.

## 1. Tabelas mais usadas (contagem de citações em `*.sql` no HEAD)

| Tabela | Citações | Papel |
|---|---|---|
| `APP_SOLICITACAO_HIST` (`h`) | ~350 | **A corrida realizada.** Histórico: uma linha por transição de status |
| `FIN_PARAMETRO_PAGAMENTO` (`pp`) | ~176 | Parâmetros de pagamento/contrato: `TX_TIPO` (`Padrao`/`Customizado`), `TX_PERFIL`, tarifa (bandeirada, R$/km, minuto parado, espera, faixa de horário/distância) |
| `APP_EMPRESA` | ~111 | Cliente PJ (`TX_NOME`, `CD_EMPRESA`) |
| `APP_ESTIMATIVA_PRECO` (`e`) | ~93 | A **cotação dinâmica** (o que foi ofertado) |
| `APP_LOG_STATUS_SOLICITACAO` (`ls`) | ~92 | Eventos do ciclo de vida da corrida |
| `APP_VEICULO` | ~79 | Cadastro **de alocação** do veículo (ver §5) |
| `APP_COLABORADOR` / `SEG_USUARIO` | ~78 / ~60 | Pessoa/usuário (nome, telefone, nascimento, login) |
| `APP_DESCONTO` | ~47 | Descontos (`TX_TIPO_DESCONTO`: `Parceria`, `Colaborador`…) |
| `APP_JORNADA_MOTORISTA`, `APP_TURNO_TRABALHO` | ~45 / ~29 | Jornada escalada × realizada; turnos (`H_INICIO`, `H_FIM`, `H_CARGA_HORARIA_DIARIA_VAPT`) |
| `APP_CONSUMO_CICLO_PRIME` | ~41 | Débito de minutos Prime por corrida |
| `APP_MOTORISTA`, `APP_LOG_STATUS_MOTORISTA`, `APP_LOG_MOTORISTA` | ~40 / ~21 / ~10 | Motoristas e log de status do motorista (online, em corrida, pausa…) |
| `APP_AGENDAMENTO`, `APP_LOG_STATUS_AGENDAMENTO` | ~33 / ~2 | Agendamentos |
| `APP_CUPOM_DESCONTO`, `APP_CUPOM_DESCONTO_LOTE` | ~32 / ~15 | `VL_CUPOM`, `BL_PERCENTUAL` (1 = %, 0 = R$) |
| `APP_MODELO_VEICULO`, `APP_SOLICITACAO_JORNADA_MOTORISTA` | ~23 / ~28 | Modelo do veículo; vínculo solicitação ↔ jornada |
| `APP_ESTIMATIVA_PRECO_FIXO_PRINCIPAL` | ~21 | Cotação **fixa** (PF até 13/06, PJ ainda hoje). Traz `DE_VALOR_BRUTO`, `DE_VALOR_FINAL`, `DE_FATOR_EQUILIBRIO_OPERACIONAL` (σ), `NU_KM_PRECO_FIXO`, `BL_INTRAMUNICIPAL`, `BL_PERCENTUAL_DESCONTO_CUPOM` |
| Família Prime (~39 tabelas, 5 views) | — | `APP_PLANO_PRIME`, `APP_PLANO_USUARIO_PRIME`, `APP_CICLO_PRIME`, `APP_CONSUMO_CICLO_PRIME`, `SEG_USUARIO_PRIME(_DEPENDENTE)`, `APP_PLANO_DEPENDENTE_PRIME`, `LOG_PLANO_USUARIO_PRIME`, `APP_ESTIMATIVA_PRIME`, `APP_PARAMETRO_PRIME`, `APP_DESPESA_ADICIONAL_PRIME`, `APP_SERVICO_ADICIONAL_PRIME`, views `VW_GESTAO_CONSUMO_PRIME`, `VW_RELATORIO_FATURAMENTO_PRIME`, `VW_CONTRATO_PLANO_PRIME`. Ver [06](06_prime.md) |
| Outras citadas 1–8× | — | `APP_MOTIVOS_ALTERACAO_STATUS`, `APP_SOLICITACAO_DETALHE`, `APP_REGIAO`, `APP_VEICULO_CONDUTOR`, `FIN_PARAMETRO_PRECO_DINAMICO`, `VW_DEMANDA_HORARIA_CIDADE`, `ESP_RELATORIO_FATURAMENTO` (tabela de relatório de faturamento), `SEG_VIAGEM`, `SEG_OCUPACAO`, `SEG_CLI`, `SEG_MES`, `SEG_USUARIO_BACKOFFICE` |

## 2. Relações-chave

```text
APP_ESTIMATIVA_PRECO (cotação dinâmica)  e.CD_ESTIMATIVA ─────────┐
APP_ESTIMATIVA_PRECO_FIXO_PRINCIPAL      h.CD_ESTIMATIVA_PRECO_FIXO_PRINCIPAL ─┤
                                                                   ▼
                                APP_SOLICITACAO_HIST (h)  1 linha por transição de status
                                   │  h.CD_SOLICITACAO
                                   ├── APP_LOG_STATUS_SOLICITACAO (ls)  1 linha por evento
                                   ├── h.CD_EMPRESA ─► APP_EMPRESA            (NULL = PF)
                                   ├── h.CD_PARAMETRO_PAGAMENTO ─► FIN_PARAMETRO_PAGAMENTO
                                   ├── h.CD_CUPOM / CD_CUPOM_LOTE ─► APP_CUPOM_DESCONTO(_LOTE)
                                   ├── h.CD_DESCONTO_PRODUTO ─► APP_DESCONTO
                                   ├── h.CD_AGENDAMENTO ─► APP_AGENDAMENTO
                                   ├── h.CD_PASSAGEIRO ─► SEG_USUARIO ─► APP_COLABORADOR (nome, tel., nascimento)
                                   └── veículo/motorista ─► APP_VEICULO, APP_MOTORISTA, APP_JORNADA_MOTORISTA
```

- `h.CD_ESTIMATIVA = e.CD_ESTIMATIVA`: `INNER` para estimado × realizado; `LEFT` quando o escopo é "todas as corridas".
- **Nenhuma solicitação tem as duas FKs de estimativa** (dinâmica e fixa); 96,1% das fixas têm a sua.
- **Prime:** `CD_USUARIO_PRIME` aponta para `SEG_USUARIO_PRIME`, **não** para `SEG_USUARIO` — não casa com `h.CD_PASSAGEIRO` (colisão de inteiros pequenos dá falso casamento). O vínculo corrida → plano é via `APP_CONSUMO_CICLO_PRIME.CD_SOLICITACAO` (FK declarada para `APP_SOLICITACAO_HIST`).
- **Motorista tem DOIS espaços de identificador** (`APP_LOG_STATUS_MOTORISTA.CD_MOTORISTA` ≠ `APP_JORNADA_MOTORISTA.CD_MOTORISTA`): não é join direto. Registrado em `PENDENCIAS.md` §1g. *(CONFIRMADO)*

## 3. Ciclo de vida da corrida (`APP_LOG_STATUS_SOLICITACAO.TX_STATUS`)

```text
AguardandoCondutor → CondutorACaminho → CondutorChegou → CorridaIniciada → CorridaEncerrada
   └─ fila ─────────┘  └─ deslocamento ┘  └─ espera ─────┘  └─ viagem ──────┘
```

- Status em **português** (`CondutorACaminho`, não `ConductorACaminho` — houve bug por isso em `diag_pickup_log_marco.sql`).
- `CD_MOTORISTA = 0` = "ainda sem condutor".
- **`CondutorChegou` é sempre gravado** (100% em 1.023 corridas — VERIFICADO).
- **Não existe evento de retorno**: o log termina em `CorridaEncerrada`. O km/tempo de retorno **não é medido**.
- **Não existe marco entre `CorridaIniciada` e `CorridaEncerrada`** (7.470 corridas PJ de julho): o "minuto parado em viagem" não deixa rastro no log.
- Outros desfechos vistos: `NaoAtendida`, `LimiteEsperaAtingido`, `CorridaCanceladaOperador` (subiu de 0,1/dia em maio para 3,7/dia em julho, pico de 21 em 31/07 — ABERTO), `Retracamento`, `PagamentoRejeitado`, cancelamentos por passageiro/motorista (autoria ABERTA).
- **Fila em corrida agendada é o próprio agendamento** (mediana 0,28 h vs 0,01 h nas não agendadas): nunca somar na média geral.
- **Não medir pickup a partir de `DT_REGISTRO`**: no dedup ele é o carimbo do status **final**.

### Definições canônicas de pickup (diferem exatamente pela espera média, +3,80 min)

| | Intervalo | Erro médio vs ETA | Usar para |
|---|---|---|---|
| (a) `t_pickup_desloc` | `CondutorACaminho → CondutorChegou` | **+2,16 min** | Avaliar o modelo de ETA |
| (b) `t_pickup_c_espera` | `CondutorACaminho → CorridaIniciada` | **+5,96 min** | Custo e ocupação de frota |

## 4. As quatro armadilhas de coluna (VERIFICADO)

| Coluna | O nome sugere | O que é de fato |
|---|---|---|
| `h.NU_DP` | distância de pickup realizada | **É `e.NU_DP`, a estimativa.** Igualdade em **100,0%** de 1.023 corridas. Pickup realizado = `NU_DISTANCIA_ACEITE_CHEGUEI` |
| `h.NU_DR_REAL` | distância de retorno realizada | Igual a `e.NU_DR` em **96,8%**. Não é medição. Preenchido em ~52% das corridas |
| `h.NU_TEMPO_DR` | tempo de retorno realizado | Inteiro em 100% das linhas, correlação 0,96 com o ETA estimado. Campo calculado |
| `e.DE_VALOR_HORA_MOTORISTA` | custo do motorista por **hora** | **Está em R$/MINUTO** (valor único 0,33 em 13.220 corridas). Multiplicar por minutos, **sem dividir por 60** |

Consequência: o repositório **não tem medição de retorno** — o km morto é premissa, não dado.

## 5. Notas por tabela

### `APP_SOLICITACAO_HIST` (`h`)
- Distâncias (metros): `NU_DISTPERCORRIDA` (DV faturada), `NU_DISTANCIA_ACEITE_CHEGUEI` (DP realizado), `NU_DP` (⚠ estimativa), `NU_DR_REAL` (⚠).
- Tempos: `DT_INICIO_REALIZADA`/`DT_FIM_REALIZADA` (viagem faturada), `DE_TEMPO_ESPERA_PASSAGEIRO` (min; *fallback* quando o log não tem `CondutorChegou`), `DT_REGISTRO` (carimbo da **linha**).
- Valores: `DE_VALORFINAL` (**líquido** de cupom — para caixa), `DE_VALOR_FINAL_BRUTO_DINAMICO` (**bruto** — para avaliar a fórmula), `DE_VALORESTIMADO`, `DE_VL_BANDEIRADA`, `DE_VL_KMPERCORRIDO`, `DE_VL_MINUTOPARADO`, `DE_VL_MOTORISTA_AGUARDANDO`, `DE_TAXA_AGENDAMENTO_PF`, `DE_VALOR_DESCONTO_FUNCIONARIO`, `DE_DESCONTO_REALIZADO`, `DE_VALOR_ESTIMADO_{DINAMICO,FIXO}[_DESCONTO]`, `DE_VALORFINAL_FIXO`, `DE_VALOR_FINAL_DINAMICO`.
- **Colunas do motor novo** (escritas após o deploy): `DE_MC2_ALVO`, `DE_CUSTO_MOTORISTA`, `DE_CUSTO_VEICULO`, `DE_SIGMA`. **A presença delas detecta a data de corte do deploy**.
- Recortes: `CD_REGIAO`, `TX_MODELO_SOLICITACAO` (pode ser NULL), `CD_AGENDAMENTO`, `BL_PRECO_DINAMICO`, `BL_CORTESIA`, `TX_CIDADEORIGEM`/`TX_CIDADEDESTINO[_REAL]`, `TX_ORIGEM` (texto no formato Google), coordenadas `TX_ORIGEM_LAT/LNG`, `TX_DESTINO_LAT/LNG`, `TX_DESTINOREAL_LAT/LNG` (**varchar anulável**; vírgula/ponto a validar). **Não existe coluna de bairro** — é parse de `TX_ORIGEM` entre o último `" - "` e a vírgula antes da cidade.
- Colunas ainda não descodificadas do notebook de features: `DE_VO`, `DE_VV`, `DE_IV_REAL` (aparecem em `KEEP_COLS_ORIG` do ETL antigo; significado **não documentado** — ABERTO).

### `APP_ESTIMATIVA_PRECO` (`e`) — o que foi cotado
`NU_DISTANCIA_VIAGEM` (m), `NU_DP` (m), `NU_DR` (m), `NU_TEMPO_ESTIMADO_MINUTOS` (min), `NU_ETA_TEMPO_SEGUNDOS` (s, **ETA até o cliente**, r = 0,980 com DP, 18,6 km/h implícito), `NU_ETA_TEMPO_PROXIMA_SEGUNDOS` (s, "ETA do retorno" — se é retorno à base ou ETA da próxima corrida está **ABERTO**), `DE_VL_ESTIMADO` (R$ cotado), `DE_VALOR_ANTIGO` (preço pré-reajuste — conferir cobertura), `DE_FATOR_EQUILIBRIO_OPERACIONAL` (σ), `DE_VALOR_KM_VEICULO` (**0,97 R$/km**, valor único em jul/2026), `DE_VALOR_HORA_MOTORISTA` (**0,33 R$/min**), `DE_PERCENTUAL_DEDUCAO` (percentual: 9,25 / 14,25 / 21,25 / 16,25 = PIS 1,65 + COFINS 7,60 + ISS do regime 0/5/12/7).
- **Não tem `CD_REGIAO`** — inócuo para PF (só existe na região 1).
- Teste interno: `TX_LOGIN LIKE '%mobicity%'` identifica **usuário da equipe** (cota sem pedir; contamina o topo do funil).

### `APP_VEICULO`
**Não é cadastro de veículo, é cadastro de alocação**: 1.178 linhas para 258 placas (uma com 31 registros). Regra de frota Prime = placa cujo **cadastro mais recente** está no centro de custo `300590260` → **23 placas** (confirmado pela operação). `BL_PRIME` é conflitante entre cadastros da mesma placa em 6 casos → inutilizável.

### `FIN_PARAMETRO_PAGAMENTO`
Contrato PJ: bandeirada, R$/km, `DE_VL_MINUTOPARADO`, `DE_VL_ESPERA`, `Hora (De/Até)`, `Distância (Metros)` (faixa — a v1 da extração trazia só `NU_DE_KM`). Vários parâmetros ativos por empresa podem ser **faixas de horário**, não cadastro poluído.

## 6. Regras de qualidade que valem em toda consulta

| Regra | Por quê |
|---|---|
| `WITH (NOLOCK)` em leitura transacional | Convenção |
| Janela semi-aberta `>= @ini AND < DATEADD(DAY,1,@fim)` | Evita perder/duplicar fronteira |
| **Dedup:** `ROW_NUMBER() OVER (PARTITION BY CD_SOLICITACAO ORDER BY DT_INICIO_REALIZADA DESC, DT_REGISTRO DESC) = 1` | `DT_INICIO_REALIZADA` sozinho não desempata (é atributo da corrida) — o `rn=1` pegaria linha arbitrária. O funil usa só `DT_REGISTRO DESC` (divergência mantida para não deslocar números já circulados) |
| `DATEDIFF(SECOND,…)/60.0`, nunca `DATEDIFF(MINUTE,…)` | `MINUTE` conta cruzamento de fronteira; erra até 59 s por corrida |
| `NULLIF(x,0)` + **piso** quando o denominador é campo cru | `0,001 min` com 100 km estoura o `CAST` e aborta o result set |
| Nunca `ISNULL(x,0)` em soma de tempos | Faz corrida sem log parecer eficiente |
| Média diária (nunca total) se algum período estiver aberto | Mês corrente é parcial |
| Mediana ao lado da média | Cauda quase sempre presente |
| Declarar cobertura (`%` de linhas com log/campo opcional) | |
| **Corrida válida:** `TX_STATUS='CorridaEncerrada'` · não-Prime · `TRY_CAST(DE_VALORFINAL AS DECIMAL(18,2)) > 0` | Quem não aplicar o 3º filtro precisa declarar |
| `DE_VALORFINAL` (líquido) × `DE_VALOR_FINAL_BRUTO_DINAMICO` (bruto) | Misturar cria surpresa negativa artificial (51,5% das PF têm cupom) |

## 7. Unidades — três padrões na mesma tabela

| Colunas | Unidade | Conversão |
|---|---|---|
| `NU_DIST*`, `NU_DP`, `NU_DR`, `NU_DR_REAL` | **metros** | `/1000.0` |
| `NU_ETA_TEMPO_SEGUNDOS`, `NU_ETA_TEMPO_PROXIMA_SEGUNDOS` | **segundos** | `/60.0` |
| `NU_TEMPO_ESTIMADO_MINUTOS`, `NU_TEMPO_DR`, `DE_TEMPO_ESPERA_PASSAGEIRO` | **minutos** | direto |
| Planilha de rodagem (`Distancia_percorrida.xlsx`) | **km** | — |

## 8. Sobre a espera: `Espera cliente` ≠ `Minuto parado` (duas cláusulas)

Informado por Vitor em 04/08/2026 a partir da tela de cadastro de parâmetros:

| Campo | O que cobra | Intervalo no log |
|---|---|---|
| **Espera cliente** (`DE_VL_ESPERA`) | carro parado aguardando o passageiro **embarcar** | `CondutorChegou → CorridaIniciada` |
| **Minuto parado** (`DE_VL_MINUTOPARADO`) | tempo parado **depois que a viagem iniciou** | dentro de `CorridaIniciada → CorridaEncerrada` |

A extração antiga (`parametros_contrato_pj.sql` v1) puxou só o minuto parado; **toda análise de espera anterior a 04/08/2026 valorou a espera de embarque pela tarifa errada** (ex.: Arcelor R$ 1,16/min no lugar de R$ 0,72; Usiminas R$ 0,97 no lugar de R$ 1,31). A extração correta é `parametros_contrato_pj_v2.sql`. Ver [05](05_pj.md).

## 9. Espera é cauda, e a cauda é o agendamento

| | média | mediana | p90 | p99 |
|---|---|---|---|---|
| geral | 3,80 | **1,08** | 10,12 | 38,19 |
| não agendada (n=864) | 1,83 | 0,82 | 4,74 | — |
| agendada (n=159) | **14,47** | **10,60** | 29,12 | — |

48% das corridas têm espera ≤ 1 min. Somar 3,80 min a todas superestimaria 77% dos casos; a correção barata é uma constante **por segmento de agendamento**.

## 10. Exploração de schema já feita

Dumps de `INFORMATION_SCHEMA` e investigações vivem em `analises/*/sql/exploracao_banco/` (`99_*.sql`) e `analises/*/dados/bruto/exploracao_banco/` (não versionados). Principais achados: 44 tabelas com PRIME no nome; `APP_PARAMETRO_PRIME` é regra **global** (1 versão vigente, histórico de 8); `ESP_RELATORIO_FATURAMENTO`; views de gestão de consumo Prime; `APP_AGENDAMENTO` nunca havia sido aberta (só o flag `CD_AGENDAMENTO`) até `99_investigar_lacunas.sql`.
