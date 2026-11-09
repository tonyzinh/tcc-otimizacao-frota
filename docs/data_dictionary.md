# Dicionário de dados

> Documento consolidado em 09/11/2026 na reestruturação do repositório. Cada parte abaixo é o documento de origem, com o conteúdo preservado; só os caminhos de arquivos foram atualizados para a estrutura nova (mapa em `reports/manifests/repository_restructure/path_map.csv`). Datas e afirmações são as da origem.
> Caminhos marcados com † são de arquivos retirados da árvore ativa nas reorganizações de 09/11/2026 (código e documentos do estudo anterior, scripts substituídos pelo pacote). As cópias estão na pasta de preservação `../tcc-otimizacao-frota_preservacao_2026-11-09/` (`arvore_antiga/`, `rodada4_arquivamento/`, `copia_completa_pre_migracao/`). Nos trechos anteriores a 09/11/2026, `data/raw/` designa a pasta de extrato bruto antiga, apagada em 08/11; desde a reestruturação, `data/raw/` é a antiga `data/extraido/`.


## Dicionário de dados e unidades

_Origem: `docs/data_dictionary.md`._

Convenções: tempo em **segundos desde a meia-noite local** do dia simulado; distâncias em **km estimados** (nunca odômetro); coordenadas em graus decimais (WGS84). Dados reais: só processamento local e agregado.

### Entidades da simulação (`domain/entities.py`)

| Campo | Significado | Unidade |
|---|---|---|
| `SimRequest.rid`, `t` | identificador (pseudônimo) e instante de chegada do pedido (`dT_REGISTRO` é *proxy* da criação) | —, s |
| `lat, lon` / `dlat, dlon` | origem e destino da corrida | graus |
| `trip_s` | duração da corrida | s |
| `patience_s` | desistência observada antes do aceite, se houver | s |
| `SimDriver.sessions` | jornadas `(início, fim, lat, lon)` | s, s, graus |
| `SimDriver.commitments` | compromissos externos `(início, fim, lat_fim, lon_fim)` | s, s, graus |
| `SimParams` | `radius_km` (raio de despacho), `speed_kmh`, `road_factor` (rua/reta), `patience_s` | km, km/h, —, s |

### Resultados por dia (Parquet, `reports/historical/frozen_evaluation/execucao/grupo_B/<período>/dia=AAAA-MM-DD.parquet`)

| Coluna | Significado |
|---|---|
| `config` | política: `B0_imediato_atual` (A), `B_lote60s_guloso_fifo` (B), `B_lote60s_hungaro` (C) |
| `pedidos` / `atendidos` / `nao_atendidos` | universo elegível do dia / atendidos / diferença |
| `km_vazio_total`, `km_busca` | km de aproximação estimado (nesta linha, não há reposicionamento: `km_vazio_total = km_busca`) |
| `esperas_s` | espera de cada pedido **atendido** (lista); inclui o tempo até a fronteira do lote e o deslocamento de aproximação |
| `espera_media_s`, `espera_p90_s` | calculadas **só entre atendidos** |
| `comp_violacao_por_politica` | compromissos externos prejudicados pela política (E1) |
| `tempo_plano_s` | relógio de parede da chamada `simulate` do dia (inclui elegibilidade, distâncias, lotes e solver; exclui construção do mundo) |
| `assinatura_entrada` | SHA-256 da entrada (igual nas três políticas) |

### Resultados sintéticos (Parquet por cenário e semente)

`cenario`, `semente`, `politica` (`R0`/`A`, `D_lote60s_guloso_fifo`, `D_lote60s_hungaro`…), `pedidos`, `atendidos`, `km_vazio_total`, `km_busca`, `km_reposicionamento`, `espera_media_s`, `espera_p90_s`, `n_veiculos`, `tempo_plano_s`.

### Distância

* Histórico: Haversine × 1,3012 a 16,079 km/h (herdados da calibração de março); raio de despacho 4,5 km em **linha reta**. Não há roteamento viário; pontes e baía não são modeladas.
* Sintético: caminho mínimo (Dijkstra) sobre a rede viária OpenStreetMap recortada; 25 km/h; raio de 8 km por via.

### Fontes e cobertura

Contrato de dados em `configs/data/data_contract.yaml`; hipóteses de acesso temporal em `configs/data/time_access_assumptions.yaml`; origem e qualidade dos dados V1 Viagens em `docs/data_dictionary.md`, `docs/data_quality.md` e `docs/availability.md`. Não se infere que o registro de solicitação seja toda a procura, nem que "online" seja "disponível".


## Dados da operação V1 Viagens: fontes, contrato, extração e diagnóstico (06/11/2026)

_Origem: `docs/data_dictionary.md`._

"V1 Viagens" é o nome da operação, não a versão do algoritmo. Escopo aprovado (R-04/R-05 em `decisions.md`): produto `V1`, região 1 (Grande Vitória), serviços 1, 11, 12 e 19, **sem Prime**. Nada aqui afirma ganho; o algoritmo guloso **não foi reescrito**. Decisão continua **D+1 preventiva**: planejador decide a posição de espera por motorista com dados até o corte da véspera (`v2/policy.py`, `v2/fleet.py`); nada nas fontes muda isso, e os campos de "estado atual" abaixo não podem entrar no plano.

Evidência: execuções de 06/11/2026 (metadados, agregados e um dia-piloto, 10/03/2026). Só esse dia foi extraído; **não há extração do período do estudo**.

### 1. Síntese das regras (`regras_de_negocio/docs/`, matriz RN001–RN033)

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

### 2. Inventário das fontes

| Fonte | Conteúdo útil | Granularidade / chave | Histórico e volume | Fuso | Acesso |
|---|---|---|---|---|---|
| ODS (SQL Server) | `APP_SOLICITACAO_HIST`, `APP_LOG_STATUS_SOLICITACAO`, `APP_VEICULO`, `APP_JORNADA_MOTORISTA`, `APP_LOG_STATUS_MOTORISTA`, `APP_REPOSICIONAMENTO_MOTORISTA`, `COBLI_TELEMETRIA_VIAGENS`, `APP_REGIAO`, `APP_TIPO_SERVICO` | 1 linha/solicitação (`CD_SOLICITACAO`); log de status por evento | 20/09/2017 a 06/11/2026; 6,45 M solicitações; Cobli 5,96 M linhas desde 16/07/2022 | naive = -03:00 (amostra) | leitura, login do `.env` |
| DW (SQL Server) | fatos/views derivados (`FT_SOLICITACAO`, `FT_REPOSICIONAMENTO_MOTORISTA`, `FT_POSICAO_TURNO`, `VW_FROTA_VIAGENS`…) | idem, agregados | derivado do ODS | idem | leitura; **só metadados e definições de views lidos** |
| STG (SQL Server) | `FT_OFERTA`, `FT_VEIC_POSICAO_VELTEC_HIST`, `APP_SOLICITACAO_HIST` | área de preparação | não perfilado | idem | leitura; **só catálogo** |
| Elasticsearch (510 índices, maioria monitoramento) | `indexofertamotoristaelasticmodel-AAAA-MM` (posição/estado dos veículos ofertados, ~2 min), `indexsumarioofertamotorista-AAAA-MM`, `indexdriversfuture` (reposicionamento, 24,2 M docs), `indexsolicitacaodetalhe` (6,48 M, tem região/serviço), `indexsolicitacaohistorico` (2,69 M, sem região), `indexdemanda`, `indexprevisibilidade` | documento por snapshot / evento | ofertas 03/2026 com 22.311 snapshots/região/mês; driversfuture 07/01/2020 a 06/11/2026 | ISO com `-03:00` | leitura (PIT + `search_after`) |

Refresh, retenção e duplicidade por fonte: **não verificados** (ofertas e sumário têm índice mensal; retenção desconhecida). Índices de Aluguel/Assinatura (`indexassinatura*`, `indexofertaveiculosaluguel*`) foram excluídos por serem outros produtos.

### 3. Delimitação V1 Viagens por fonte

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

### 4. Matriz de precedência

Solicitação e cadeia de status: ODS (ES `indexsolicitacaodetalhe` só para conferência; o `historico` do ES cobriu 14 de 300 solicitações amostradas, cobertura parcial). Posição e disponibilidade do motorista: ES ofertas (≈2 min) > log de status ODS > jornada. Percurso observado: Cobli (início/fim de viagens e paradas). Frota: ODS `APP_VEICULO` (foto atual, só para cadastro). Em conflito, vale a fonte primária do evento e a divergência vai para `decisions.md`.

### 5. Dicionário (campos essenciais; todos com tempo de ocorrência e `available_at` proxy)

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

### 6. Dados prioritários

- **Pacote mínimo:** solicitação + cadeia de status, posições de ofertas (ES), Cobli, log de status e jornada do motorista.
- **Melhoria:** reposicionamento operado (ODS) e sugerido (ES), sumário, demanda prevista do ES.
- **Futuro / lacunas:** retorno e circulação (só Cobli, aproximado), escala conhecida na véspera, vínculo motorista-veículo vigente por data (`APP_VEICULO_CONDUTOR`, `APP_VEICULO_HISTORICO` não extraídos), rede viária real (hoje Haversine × fator).

### 7. Plano e comandos reprodutíveis

Ordem: solicitação → status → telemetria Cobli → ofertas/sumário (ES) → motorista (coorte) → reposicionamento → qualidade. Lotes diários, idempotentes (assinatura = filtro + consulta + janela + esquema; lote pronto é pulado se o checksum confere), retomáveis (basta repetir o comando). Saída em `data/raw/v1_viagens/<fonte>/<entidade>/dt=AAAA-MM-DD/` (`part-000.parquet`, `amostra.csv`, `rejeitados.parquet`, `manifest.json`); campanha em `campanha.json`; relatório em `reports/data_quality/v1_viagens_extraction/`.

```
set TCC_REAL_DATA_AUTHORIZED=YES   # portão do proprietário
.venv\Scripts\python.exe -m tcc_frota.extracao --fonte ods --entidade solicitacao --inicio 2026-03-10 --fim 2026-03-10
# entidades ods: solicitacao status_solicitacao jornada_motorista log_status_motorista reposicionamento veiculo telemetria_cobli
# entidades es:  posicao_ofertas sumario_ofertas reposicionamento_sugerido
.venv\Scripts\python.exe -m tcc_frota.extracao.qualidade --inicio 2026-03-10 --fim 2026-03-10
.venv\Scripts\python.exe -m pytest tests/unit/test_data_extraction.py tests/unit/test_data_reading.py
```

Custo medido no piloto de 1 dia: ODS 14–16 s por entidade de coorte; ES 2–6 s. Período do estudo (março e setembro) não foi extraído.

### 8. Qualidade e reconciliação (piloto 10/03/2026, `reports/data_quality/v1_viagens_extraction/qualidade_2026-03-10_2026-03-10.json`)

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

### 9. Sobre a Cobli (pedido do proprietário)

Vale investigar, com ressalvas. **Tem:** início/fim de cada viagem e parada (coordenadas, horário, distância, duração, tempo ocioso), por placa e motorista, desde 07/2022. **Não tem:** a trajetória ponto a ponto, então não é o "percurso completo"; a distância é o total do trecho informado pela Cobli. **Potencial:** única fonte que observa deslocamento sem passageiro (aproximação, circulação, retorno); permitiria separar KM vazio observado de estimado. **Riscos:** não distingue Prime × Normal por viagem; 22% das viagens sem motorista; semântica de `idle` não confirmada; amostra de 1 dia. Próximo passo: casar viagens Cobli com as solicitações do mesmo veículo e janela e medir a taxa de casamento antes de qualquer número de KM morto.

### 10. Registro de migração do Databricks

Feito (06/11/2026, só árvore de trabalho; nada em commit): removidos frontend/Streamlit (`app/`), gravação no Databricks (`databricks.yml`, `databricks/`, `gold-export`, comando fleetlab no `cli.py`) e dependências (`uv.lock` regenerado). Mantidos: leitura `gold/export.py` (`TABLES`, `read_table`), replay local. Substituído por: `src/tcc_frota/data/reading/` (SQL Server e ES, somente leitura) e `src/tcc_frota/data/extraction/` (Parquet/CSV locais). Resíduos de nome: `dataset_kind="real_gold_databricks"` em `gold/replay.py` e teste (rótulo histórico, não alterado para não mexer em resultado congelado) e docstrings. Nenhum workspace, tabela ou dado remoto foi tocado ou apagado, e nenhum dado foi enviado ao Databricks.

### 11. O que cada dado habilita no guloso (sem alegar ganho)

| Dado | Habilita |
|---|---|
| Posições de ofertas (~2 min) | estado inicial real da frota, veículos a caminho e liberações previstas, filtro de elegibilidade |
| Solicitação + status | demanda por zona/hora, espera e cancelamento, atendimento e cobertura como controles |
| Cobli | calibrar fator rua/reta e velocidade, observar circulação e retorno, validar o KM estimado |
| Jornada e log de status | oferta (quem trabalha) separada de demanda |
| Reposicionamento ODS e sugerido ES | baseline operacional mais forte e custo observado de movimento |
| Sumário | verificação cruzada da oferta |

Nada disso prova que o guloso reduz KM vazio; o mecanismo e a formulação seguem em `.claude/rules/fleet_assignment.md`, e R-01 continua aberta.


## Pseudonimização estável e vínculos entre fontes (08/11/2026)

_Origem: `docs/data_dictionary.md`._

Estado: **implementado e testado**; piloto de 10/03/2026 regravado com o esquema novo (ver §5). Decisões formais: R-07 e R-08 em `decisions.md`.

### 1. Por que `data/.pseudo_salt`† e `data/raw/` sumiram (investigação de 08/11/2026)

| Evidência | Resultado |
|---|---|
| Scripts, testes e configuração do repositório (`rmtree`, `unlink`, `Remove-Item`, `git clean`, `rm -rf`) | Só `saida.py` apaga o `rejeitados.parquet` do próprio lote. Nenhum script remove `data/` ou o sal. `pytest` usa `--basetemp=.pytest-tmp`, fora de `data/` |
| `.claude/settings.json` | `bypassPermissions`; sem hooks de limpeza |
| Lixeira do Windows | **Contém os dois itens**: `raw` e `.pseudo_salt` (origem `data/`), apagados em 06/11/2026 às 21:37 UTC (18:37 local), um minuto antes do sal atual ser criado (mtime 18:38 local). `raw` tem 82 arquivos, 348 MB (`dados_historico56`, `dados_historico56_set`, `dados_mar2026`, `dados_set2026`). Na mesma data foram para a lixeira `docs`, `reports`, `resultados`, `tabelas`, `.codex`, `.ref`, `.pytest*`, `.ruff_cache` (~20:52–20:55 UTC) e a pasta-mãe `tcc-otimizacao-frota` (20:36 UTC) |
| Pasta sincronizada | O repositório está em `OneDrive\Documentos`; `data/` e o sal ficam sincronizados com a nuvem. Não há evidência de que o OneDrive tenha apagado algo |

**Conclusão (nível: executado, causa não provada).** Os itens foram *movidos para a lixeira* (não apagados em definitivo) por uma operação de usuário/shell durante a limpeza de 06/11, não por código do projeto. A lixeira não registra o processo responsável; **a causa exata não é determinável com a evidência disponível**. Consequência: o sal original e `data/raw` **são recuperáveis** (não restaurei nenhum dos dois; ver §6).

### 2. Esquema `hmac-sha256-v1`

- Segredo fora do repositório e fora de pasta sincronizada: `%LOCALAPPDATA%\tcc_frota\segredos\pseudo_secret` (`TCC_SEGREDOS_DIR` substitui), permissão restrita ao usuário (`icacls`, herança removida).
- Cópia de segurança separada: `%USERPROFILE%\.tcc_frota_backup\pseudo_secret.<chave_id>.bak` (conferida pela impressão digital). **Guarde também uma cópia off-line (gerenciador de senhas).**
- `chave_id` = HMAC-SHA256(segredo, rótulo fixo)[:12]: identifica a versão sem expor o segredo. Vai em todo manifesto (`pseudonimizacao.chave_id`), no registro `data/raw/v1_viagens/PSEUDONIMIZACAO.json` e na assinatura do lote.
- Pseudônimo = HMAC-SHA256(segredo, `entidade␟valor normalizado`)[:20 hex]. Entidades: `motorista`, `condutor`, `placa`, `veiculo_cod`, `passageiro`, `veiculo_condutor` e `cobli_*`. Normalização: espaços, `5.0`→`5`, placa em maiúsculas só com alfanuméricos.
- Guarda: segredo ausente ou diferente do registrado interrompe a extração (`SegredoAusente`/`SegredoIncompativel`); lotes sem versão (legado) bloqueiam a campanha; **nenhum segredo é criado automaticamente**, e `inicializar` recusa quando já existem lotes dependentes. Migração do sal legado preserva o valor (`inicializar --do-legado`).
- Comandos: `python -m tcc_frota.privacidade status|inicializar|backup|restaurar <chave_id>` (nunca imprime o segredo).

#### Por que a normalização importava (evidência)
Na Cobli, 67 de 3.000 placas amostradas (2,2%) vêm com espaço à direita. Com o esquema antigo (SHA-256 do texto bruto) a mesma placa geraria dois pseudônimos.

### 3. Famílias de identificadores (evidência de 10/03/2026, contagens de interseção)

| Par | Interseção | Leitura |
|---|---|---|
| motorista (solicitação) × motorista (ES ofertas) × usuário (ES reposicionamento) × motorista (log de status) | 111, 111, 111 de 129 motoristas com corrida | **mesma família**: junção válida |
| motorista (solicitação) × `CD_MOTORISTA` da jornada | **0** de 129 | famílias distintas |
| `CD_MOTORISTA` da jornada × `CD_CONDUTOR` (`APP_VEICULO_CONDUTOR`) | 167 de 168 | a jornada usa o **condutor** |
| `CD_VEICULO` do ODS × placa | 0 | `CD_VEICULO` é código numérico, **não** é placa |
| placa do cadastro (`TX_PLACA`) × placa Cobli | 117 de 117 | ponte ODS↔Cobli possível via `APP_VEICULO.TX_PLACA` |
| placa ES ofertas × placa Cobli | 101 de 117 | consistente (ofertas listam só veículos ofertados) |
| `CD_INTEGRACAO_VEHICLE_ID`/`TX_INTEGRACAO_DEVICE_ID` × ids Cobli | 0 | não servem de ponte |
| Motorista Cobli (`DRIVER_ID`, UUID) × motorista ODS | 0 (família própria; 22% das viagens sem motorista) | não há ponte |

Pendência: o cadastro tem **1.928 placas repetidas** em mais de um `CD_VEICULO` (reuso/histórico); `CD_VEICULO → placa` é função, `placa → CD_VEICULO` não. A placa vem de uma foto atual: pode divergir da placa vigente em março.

### 4. Teste de integração dos vínculos
`tests/integration/test_pseudonymization.py`: dois processos separados geram os mesmos pseudônimos; ODS e ES ligam o mesmo motorista; ES e Cobli ligam a mesma placa (inclusive com espaço/caixa distintos); guarda contra segredo ausente/trocado/legado; migração, backup e restauração. `tests/integration/test_extraction_resumable.py`: segunda execução pula o lote, segredo trocado interrompe antes de gravar, lote corrompido é regravado.

### 5. Arquivos antes e depois da troca
- **Antes (sal anterior):** `data/raw/` (lixeira) e qualquer silver derivado dele. Nenhum artefato congelado (`resultados/`, `reports/tcc_final`†) contém pseudônimos (verificado por busca de colunas de identificador): a perda do sal não altera resultado congelado.
- **Depois da troca, mesmo sal (18:38 local):** todo o piloto antigo (sal criado 18:38; lotes de 18:38 a 18:52). Interseções altas entre fontes (§3) confirmam que usam **um único** sal. Foi movido, sem apagar, para `data/raw/v1_viagens_previous_salt_20261106/` (pseudônimos de 16 hex, sem versão).
- **Decisão sobre o segredo:** o valor do sal de 06/11 foi **mantido** (migrado sem alteração para o local protegido; `chave_id 02f6c9316eb0`) porque era o único com dados dependentes vivos. Os dados foram regravados com a transformação nova em `data/raw/v1_viagens/`.
- `data/.pseudo_salt`† permanece **porque o pipeline v2 (`v2/rules.py::load_salt`) ainda o lê**; ele fica em pasta sincronizada. Recomenda-se removê-lo depois de migrar o v2 (ação sua).

### 6. Recuperação do material na lixeira (não executada)
`raw` (348 MB) e o sal original estão na lixeira. Restaurar `data/raw` é cópia local, sem enviar nada a serviço externo; não o fiz porque não foi pedido e o uso exige o portão. Se quiser o sal original apenas para consulta, copie-o para um nome distinto: restaurá-lo sobre `data/.pseudo_salt`† sobrescreveria o arquivo atual.
