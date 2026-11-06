# Dados da operação V1 Viagens: fontes, contrato, extração e diagnóstico (06/11/2026)

"V1 Viagens" é o nome da operação, não a versão do algoritmo. Escopo aprovado (R-04/R-05 em `REGISTRO_DECISOES.md`): produto `V1`, região 1 (Grande Vitória), serviços 1, 11, 12 e 19, **sem Prime**. Nada aqui afirma ganho; o algoritmo guloso **não foi reescrito**. Decisão continua **D+1 preventiva**: planejador decide a posição de espera por motorista com dados até o corte da véspera (`v2/policy.py`, `v2/fleet.py`); nada nas fontes muda isso, e os campos de "estado atual" abaixo não podem entrar no plano.

Evidência: execuções de 06/11/2026 (metadados, agregados e um dia-piloto, 10/03/2026). Só esse dia foi extraído; **não há extração do período do estudo**.

## 1. Síntese das regras (`regras_de_negocio/docs/`, matriz RN001–RN033)

| Tema | Regra / origem | Consequência |
|---|---|---|
| Duas famílias de ID de motorista | `v1_viagens` + matriz RN | junção entre fontes só por chave confirmada; pseudônimo único por ID |
| `NU_DP`/`NU_DR_REAL` são estimativas; aproximação real = `NU_DISTANCIA_ACEITE_CHEGUEI`; `NU_DISTPERCORRIDA` = trecho com passageiro | RN (distâncias em m, ETA em s, esperas em min) | pickup observado só nas corridas com aceite→chegada; 42,6% nulo no piloto |
| Sem evento de retorno | RN | KM morto de retorno/circulação **não é medido** pelas regras; só inferível por telemetria |
| Fuso sem deslocamento (RN024 pendente) | RN024 | evidência nova: ODS naive = -03:00 (14/14 idênticas no ES); manter pendente até confirmação da empresa |
| `CD_REGIAO=1` Grande Vitória; `APP_VEICULO` é registro de alocação | RN | frota por região, não por nome de tabela |
| Prime (23 placas, cessão, transbordo) | RN | **conflito**: veículos Prime executam corridas "Normal" (ver §3, Cobli) |
| Lacunas críticas L1–L5 | matriz | não resolvidas aqui |

Ambiguidades abertas: (a) o ODS `APP_SOLICITACAO_HIST` tem uma linha por solicitação (6.446.410 linhas = 6.446.410 solicitações), ao contrário da descrição "uma linha por transição"; a cadeia de status vem de `APP_LOG_STATUS_SOLICITACAO`; (b) views do DW divergem sobre a frota de Viagens (`IN (1,4)` × `NOT IN (3,5)`); (c) significado dos códigos `status` das ofertas e de `mode/idMotivo` do reposicionamento; (d) "Operação V1 VIX CAM" na Cobli.

## 2. Inventário das fontes

| Fonte | Conteúdo útil | Granularidade / chave | Histórico e volume | Fuso | Acesso |
|---|---|---|---|---|---|
| ODS (SQL Server) | `APP_SOLICITACAO_HIST`, `APP_LOG_STATUS_SOLICITACAO`, `APP_VEICULO`, `APP_JORNADA_MOTORISTA`, `APP_LOG_STATUS_MOTORISTA`, `APP_REPOSICIONAMENTO_MOTORISTA`, `COBLI_TELEMETRIA_VIAGENS`, `APP_REGIAO`, `APP_TIPO_SERVICO` | 1 linha/solicitação (`CD_SOLICITACAO`); log de status por evento | 20/09/2017 a 06/11/2026; 6,45 M solicitações; Cobli 5,96 M linhas desde 16/07/2022 | naive = -03:00 (amostra) | leitura, login do `.env` |
| DW (SQL Server) | fatos/views derivados (`FT_SOLICITACAO`, `FT_REPOSICIONAMENTO_MOTORISTA`, `FT_POSICAO_TURNO`, `VW_FROTA_VIAGENS`…) | idem, agregados | derivado do ODS | idem | leitura; **só metadados e definições de views lidos** |
| STG (SQL Server) | `FT_OFERTA`, `FT_VEIC_POSICAO_VELTEC_HIST`, `APP_SOLICITACAO_HIST` | área de preparação | não perfilado | idem | leitura; **só catálogo** |
| Elasticsearch (510 índices, maioria monitoramento) | `indexofertamotoristaelasticmodel-AAAA-MM` (posição/estado dos veículos ofertados, ~2 min), `indexsumarioofertamotorista-AAAA-MM`, `indexdriversfuture` (reposicionamento, 24,2 M docs), `indexsolicitacaodetalhe` (6,48 M, tem região/serviço), `indexsolicitacaohistorico` (2,69 M, sem região), `indexdemanda`, `indexprevisibilidade` | documento por snapshot / evento | ofertas 03/2026 com 22.311 snapshots/região/mês; driversfuture 07/01/2020 a 06/11/2026 | ISO com `-03:00` | leitura (PIT + `search_after`) |

Refresh, retenção e duplicidade por fonte: **não verificados** (ofertas e sumário têm índice mensal; retenção desconhecida). Índices de Aluguel/Assinatura (`indexassinatura*`, `indexofertaveiculosaluguel*`) foram excluídos por serem outros produtos.

## 3. Delimitação V1 Viagens por fonte

| Fonte | Filtro aplicado | Garantia |
|---|---|---|
| ODS solicitação / log de status | `CD_REGIAO=1`, `CD_TIPO_SERVICO IN (1,11,12,19)`, `TX_MODELO_SOLICITACAO <> 'Prime'` | campos próprios; 127 de 1.452 solicitações do dia-piloto eram Prime e saíram |
| ODS motorista (jornada, log de status, reposicionamento) | coorte: motorista com solicitação V1 região 1 em ±7 dias | **limitação**: sem campo de região; motorista que opere em outro produto na mesma semana não é separável |
| ODS veículo | `CD_REGIAO=1` | foto atual, 9.598 cadastros (109 ativos): mistura histórico |
| Cobli | `VEHICLE_GROUP='Operação'` | 106 de 113 placas com corrida V1 região 1 no dia; **o grupo contém veículos que também fazem Prime**; "Operação Prime" e "Operação V1 VIX CAM" ficaram de fora |
| ES ofertas | `codigoRegiao=1` e interseção dos serviços do veículo com {1,11,12,19} | por veículo/snapshot |
| ES sumário | `codigoRegiao=1` | **não separa serviço**: contagem agregada da região |
| ES reposicionamento | `regiaoId=1` | sem serviço; semântica pendente |
| DW / STG | não extraídos | sem separação segura verificada |

Fontes sem separação segura aqui (sumário por serviço, motorista fora da coorte) ficam sinalizadas em `limites` do manifesto; nada delas entra como "V1 Viagens puro".

## 4. Matriz de precedência

Solicitação e cadeia de status: ODS (ES `indexsolicitacaodetalhe` só para conferência; o `historico` do ES cobriu 14 de 300 solicitações amostradas, cobertura parcial). Posição e disponibilidade do motorista: ES ofertas (≈2 min) > log de status ODS > jornada. Percurso observado: Cobli (início/fim de viagens e paradas). Frota: ODS `APP_VEICULO` (foto atual, só para cadastro). Em conflito, vale a fonte primária do evento e a divergência vai para `REGISTRO_DECISOES.md`.

## 5. Dicionário (campos essenciais; todos com tempo de ocorrência e `available_at` proxy)

Status: C = confirmado em regra/documento, P = significado pendente, D = derivável, A = ausente, N = não verificado. Prioridade: E essencial, I importante, O opcional.

| Entidade.campo (padronizado) | Definição | Unid./tipo | Tempo | Disponível na decisão | Uso | Pri. | Status |
|---|---|---|---|---|---|---|---|
| solicitacao.dt_registro | criação (proxy) | timestamp -03:00 | ocorrência | sim (≤ corte) | demanda histórica | E | P (proxy) |
| solicitacao.tx_origem_lat/lng (3 casas), tx_h3index_origem | origem do passageiro | graus / H3 | idem | histórico sim | demanda por zona | E | C |
| solicitacao.cd_motorista/cd_veiculo (pseudônimo) | quem atendeu | string | no aceite | histórico sim | oferta, pickup | E | C |
| solicitacao.nu_distancia_aceite_cheguei | pickup real | m | chegada | histórico sim | KM de aproximação | E | C (42,6% nulo) |
| solicitacao.nu_distpercorrida | trecho com passageiro | m | fim | histórico sim | controle/economia | E | C |
| solicitacao.tx_status, dt_inicio/fim_realizada | desfecho e marcos | texto/timestamp | evento | histórico sim | atendimento/cobertura | E | C |
| solicitacao.tx_modelo_solicitacao, tx_tipo_prime | Prime × Normal | texto | — | — | filtro | E | C |
| status_solicitacao.* | cadeia de status por evento | texto/timestamp | evento | histórico sim | espera, cancelamento | E | C |
| posicao_ofertas.latitude/longitude/h3_index/status/passageiro_embarcado | posição e estado do veículo ofertado | graus/enum | snapshot ~2 min; `data_posicao_gps` | sim (última antes do corte) | estado inicial da frota, regime A/B | E | P (enum) |
| posicao_ofertas.codigo_solicitacao / codigo_proxima_solicitacao / tempo_segundos_viagem_restante | viagem em curso e próxima | id/s | snapshot | sim | liberações previstas | I | N |
| sumario_ofertas.qtd_* | contagem de motoristas por estado | int | snapshot | sim | oferta agregada | I | P |
| jornada_motorista.* | turno estimado/realizado | timestamp | evento | escala só se conhecida na véspera (regime B a confirmar) | oferta | I | N (0 linhas no piloto) |
| log_status_motorista.* | login/estado do motorista | enum | evento | histórico sim | disponibilidade | I | P (enum inferido) |
| reposicionamento.* (ODS) | reposicionamentos operados | coords/m | registro/aceite/fim | histórico sim | KM de reposicionamento observado | E | N |
| reposicionamento_sugerido.* (ES) | sugestão do sistema | h3/coords | registro | histórico sim | baseline de operação | I | P |
| telemetria_cobli.* | viagens/paradas (início, fim, distância, duração, ocioso) | m/ms | início/fim do trecho | histórico sim | validar KM, medir circulação | E | C (estrutura), N (semântica de `idle`) |
| veiculo.* | cadastro da frota | — | foto atual | **não** (estado atual) | cadastro | O | C |

Tratamento de ausentes: nulos preservados, nunca imputados na extração; `rejeitados.parquet` guarda chave nula, chave duplicada, tempo nulo e fora da janela, com contagem no manifesto (0 rejeitadas no piloto).

## 6. Dados prioritários

- **Pacote mínimo:** solicitação + cadeia de status, posições de ofertas (ES), Cobli, log de status e jornada do motorista.
- **Melhoria:** reposicionamento operado (ODS) e sugerido (ES), sumário, demanda prevista do ES.
- **Futuro / lacunas:** retorno e circulação (só Cobli, aproximado), escala conhecida na véspera, vínculo motorista-veículo vigente por data (`APP_VEICULO_CONDUTOR`, `APP_VEICULO_HISTORICO` não extraídos), rede viária real (hoje Haversine × fator).

## 7. Plano e comandos reprodutíveis

Ordem: solicitação → status → telemetria Cobli → ofertas/sumário (ES) → motorista (coorte) → reposicionamento → qualidade. Lotes diários, idempotentes (assinatura = filtro + consulta + janela + esquema; lote pronto é pulado se o checksum confere), retomáveis (basta repetir o comando). Saída em `data/extraido/v1_viagens/<fonte>/<entidade>/dt=AAAA-MM-DD/` (`part-000.parquet`, `amostra.csv`, `rejeitados.parquet`, `manifest.json`); campanha em `campanha.json`; relatório em `reports/extracao_v1_viagens/`.

```
set TCC_REAL_DATA_AUTHORIZED=YES   # portão do proprietário
.venv\Scripts\python.exe -m tcc_frota.extracao --fonte ods --entidade solicitacao --inicio 2026-03-10 --fim 2026-03-10
# entidades ods: solicitacao status_solicitacao jornada_motorista log_status_motorista reposicionamento veiculo telemetria_cobli
# entidades es:  posicao_ofertas sumario_ofertas reposicionamento_sugerido
.venv\Scripts\python.exe -m tcc_frota.extracao.qualidade --inicio 2026-03-10 --fim 2026-03-10
.venv\Scripts\python.exe -m pytest tests/unit/test_extracao.py tests/unit/test_leitura.py
```

Custo medido no piloto de 1 dia: ODS 14–16 s por entidade de coorte; ES 2–6 s. Período do estudo (março e setembro) não foi extraído.

## 8. Qualidade e reconciliação (piloto 10/03/2026, `reports/extracao_v1_viagens/qualidade_2026-03-10_2026-03-10.json`)

| Entidade | Linhas | Rejeitadas |
|---|---|---|
| ods/solicitacao | 1.325 | 0 |
| ods/status_solicitacao | 5.202 | 0 |
| ods/log_status_motorista | 896 | 0 |
| ods/reposicionamento | 297 | 0 |
| ods/jornada_motorista | 0 | 0 |
| ods/telemetria_cobli | 3.227 (1.511 trips + 1.716 stops) | 0 |
| es/posicao_ofertas | 38.153 (720 snapshots, 132 motoristas) | 0 |
| es/sumario_ofertas | 720 | 0 |
| es/reposicionamento_sugerido | 7.178 | 0 |
| ods/veiculo | 9.598 (foto) | 0 |

Conferências: chave de solicitação única; 0 eventos de status órfãos; início ≤ fim em 100% das encerradas; GPS das ofertas defasado em mediana 2,7 s; 22% das viagens Cobli sem motorista.

**Reconciliação de KM (um dia, agregada):** Cobli `trips` do grupo "Operação" 13.471,5 km; corridas encerradas V1 sem Prime 8.303,1 km + aproximação 3.246,1 km = 11.549,2 km; resíduo 1.922,3 km (14%). Antes de excluir Prime o resíduo era 257,4 km, o que indica que **os veículos da Cobli "Operação" também rodam corridas Prime**. O resíduo não é KM morto medido: soma Prime que a Cobli não separa por viagem, circulação, retorno e erros de casamento. Casar viagem a viagem (por placa e janela de tempo com a solicitação) é o passo necessário e não foi feito.

## 9. Sobre a Cobli (pedido do proprietário)

Vale investigar, com ressalvas. **Tem:** início/fim de cada viagem e parada (coordenadas, horário, distância, duração, tempo ocioso), por placa e motorista, desde 07/2022. **Não tem:** a trajetória ponto a ponto, então não é o "percurso completo"; a distância é o total do trecho informado pela Cobli. **Potencial:** única fonte que observa deslocamento sem passageiro (aproximação, circulação, retorno); permitiria separar KM vazio observado de estimado. **Riscos:** não distingue Prime × Normal por viagem; 22% das viagens sem motorista; semântica de `idle` não confirmada; amostra de 1 dia. Próximo passo: casar viagens Cobli com as solicitações do mesmo veículo e janela e medir a taxa de casamento antes de qualquer número de KM morto.

## 10. Registro de migração do Databricks

Feito (06/11/2026, só árvore de trabalho; nada em commit): removidos frontend/Streamlit (`app/`), gravação no Databricks (`databricks.yml`, `databricks/`, `gold-export`, comando fleetlab no `cli.py`) e dependências (`uv.lock` regenerado). Mantidos: leitura `gold/export.py` (`TABLES`, `read_table`), replay local. Substituído por: `src/tcc_frota/leitura/` (SQL Server e ES, somente leitura) e `src/tcc_frota/extracao/` (Parquet/CSV locais). Resíduos de nome: `dataset_kind="real_gold_databricks"` em `gold/replay.py` e teste (rótulo histórico, não alterado para não mexer em resultado congelado) e docstrings. Nenhum workspace, tabela ou dado remoto foi tocado ou apagado, e nenhum dado foi enviado ao Databricks.

## 11. O que cada dado habilita no guloso (sem alegar ganho)

| Dado | Habilita |
|---|---|
| Posições de ofertas (~2 min) | estado inicial real da frota, veículos a caminho e liberações previstas, filtro de elegibilidade |
| Solicitação + status | demanda por zona/hora, espera e cancelamento, atendimento e cobertura como controles |
| Cobli | calibrar fator rua/reta e velocidade, observar circulação e retorno, validar o KM estimado |
| Jornada e log de status | oferta (quem trabalha) separada de demanda |
| Reposicionamento ODS e sugerido ES | baseline operacional mais forte e custo observado de movimento |
| Sumário | verificação cruzada da oferta |

Nada disso prova que o guloso reduz KM vazio; o mecanismo e a formulação seguem em `.claude/rules/otimizacao-de-frota.md`, e R-01 continua aberta.
