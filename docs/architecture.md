# Arquitetura

Pacotes de `src/tcc_frota/` (sem ciclos):

```
cli ──► visualization ──► metrics ──► simulation ──► assignment ──► domain
 │            │                            │
 │            └──► scenarios ──────────────┘          simulation ──► data ──► domain
 └────────────────────────────────────────────────►  (cli importa todos)
```
Dependências permitidas (conferidas por `tests/reproducibility/test_package_layers.py`): `domain` não importa ninguém; `assignment`→`domain`; `data`→`domain`; `simulation`→`domain, assignment, data`; `scenarios`→`domain, assignment, simulation`; `metrics`→`domain, simulation, assignment`; `visualization`→`scenarios, metrics, domain`; `cli`→todos.

| Pacote | Responsabilidade | Principais símbolos |
|---|---|---|
| `domain` | entidades puras (dataclasses), unidades e assinatura de entrada | `SimParams`, `SimRequest`, `SimDriver`, `SimResult`, `reta_km`, `signature` |
| `assignment` | decisão do lote: o que a política escolhe a cada instante | `nearest_fifo` (A, B), `hungarian` (C), `kuhn_munkres`, `POLICIES` |
| `simulation` | simulador de eventos discretos (despacho imediato ou em lotes, jornadas, compromissos) e o experimento por dia real | `engine.simulate`, `historical.run_day` |
| `scenarios` | geografia pública (IBGE + OSM + H3), gerador sintético, catálogo e execução de pares A/B/C | `geography`, `generator`, `catalog`, `runner.run_pair` |
| `data` | extração somente leitura (SQL Server/Elasticsearch), pseudonimização, montagem do mundo histórico, portão de autorização | `world.montar`, `authorization.authorize` |
| `metrics` | totais, contrastes pareados por dia/semente, bootstrap, Holm, critérios de serviço | `historical`, `synthetic`, `statistics` |
| `visualization` | figuras reutilizáveis (PDF vetorial + PNG) e mapa H3 | `figures`, `maps` |
| `cli` | comando `tcc-frota` | `run-synthetic`, `run-historical`, `analyze-*`, `figures` |

## Fluxo de dados

1. **Histórico (privado):** extração local → `data/extraido/v1_viagens/` (Parquet pseudonimizado) → `data.world.montar` (pedidos, jornadas, compromissos, posição inicial) → `simulation.engine.simulate` por política → um Parquet por dia → `metrics.historical` → tabelas e figuras agregadas.
2. **Sintético (público):** `data/geografia/` (IBGE + OSM) → `scenarios.geography` (rede, pontos H3, recorte) → `scenarios.generator` (pedidos e frota por semente) → `simulation.engine.simulate` → Parquet por (cenário, semente) → `metrics.synthetic`.

Entradas das três políticas são **idênticas** (assinatura SHA-256 conferida por par). A política só vê pedidos já chegados e o estado do instante do lote.

## Decisões de projeto

* Código em inglês (`snake_case`); documentação em português. Os **identificadores gravados** nos resultados congelados (`B0_imediato_atual`, `B_lote60s_hungaro`, `D_lote60s_hungaro`, `R0`) foram mantidos para que os Parquet antigos continuem legíveis.
* Configuração externa em `configs/`; o código continua sendo a fonte executável e os testes conferem que as configurações concordam com ele.
* Nada em `reports/atribuicao_final/`, `reports/sintetico_v2/` ou `reports/tcc_final/` é sobrescrito: o CLI recusa essas pastas como saída.
