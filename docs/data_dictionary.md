# Dicionário de dados e unidades

Convenções: tempo em **segundos desde a meia-noite local** do dia simulado; distâncias em **km estimados** (nunca odômetro); coordenadas em graus decimais (WGS84). Dados reais: só processamento local e agregado.

## Entidades da simulação (`domain/entities.py`)

| Campo | Significado | Unidade |
|---|---|---|
| `SimRequest.rid`, `t` | identificador (pseudônimo) e instante de chegada do pedido (`dT_REGISTRO` é *proxy* da criação) | —, s |
| `lat, lon` / `dlat, dlon` | origem e destino da corrida | graus |
| `trip_s` | duração da corrida | s |
| `patience_s` | desistência observada antes do aceite, se houver | s |
| `SimDriver.sessions` | jornadas `(início, fim, lat, lon)` | s, s, graus |
| `SimDriver.commitments` | compromissos externos `(início, fim, lat_fim, lon_fim)` | s, s, graus |
| `SimParams` | `radius_km` (raio de despacho), `speed_kmh`, `road_factor` (rua/reta), `patience_s` | km, km/h, —, s |

## Resultados por dia (Parquet, `reports/atribuicao_final/execucao/grupo_B/<período>/dia=AAAA-MM-DD.parquet`)

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

## Resultados sintéticos (Parquet por cenário e semente)

`cenario`, `semente`, `politica` (`R0`/`A`, `D_lote60s_guloso_fifo`, `D_lote60s_hungaro`…), `pedidos`, `atendidos`, `km_vazio_total`, `km_busca`, `km_reposicionamento`, `espera_media_s`, `espera_p90_s`, `n_veiculos`, `tempo_plano_s`.

## Distância

* Histórico: Haversine × 1,3012 a 16,079 km/h (herdados da calibração de março); raio de despacho 4,5 km em **linha reta**. Não há roteamento viário; pontes e baía não são modeladas.
* Sintético: caminho mínimo (Dijkstra) sobre a rede viária OpenStreetMap recortada; 25 km/h; raio de 8 km por via.

## Fontes e cobertura

Contrato de dados em `configs/data/data_contract.yaml`; hipóteses de acesso temporal em `configs/data/hipoteses_tempo.yaml`; origem e qualidade dos dados V1 Viagens em `docs/DADOS_V1_VIAGENS.md`, `docs/AVALIACAO_BASE_V1_VIAGENS.md` e `docs/DISPONIBILIDADE_E_UNIVERSO.md`. Não se infere que o registro de solicitação seja toda a procura, nem que "online" seja "disponível".
