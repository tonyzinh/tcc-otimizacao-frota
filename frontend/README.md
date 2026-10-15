# FleetLab — Mobility Intelligence (frontend)

POC visual do TCC **Otimização da Alocação de Frota em Aplicativos de Transporte Urbano**: simulação e
comparação de estratégias de alocação preventiva **D+1** para reduzir o **KM vazio estimado**, com a
cobertura de atendimento como controle.

> **Todos os dados exibidos são fictícios.** Eles vêm de um gerador local determinístico em
> `src/mocks/`. Nada é lido de `data/`, da Gold do Databricks ou do Elasticsearch, e nenhum número
> desta interface deve ser citado como resultado do TCC. O resultado real está em
> `docs/experimento_real.md`, na raiz do repositório.

Esta pasta é independente do projeto científico: não importa código Python, não altera o simulador e
não instala dependências na raiz.

## Execução (PowerShell)

```powershell
cd frontend
npm install
npm run dev          # http://127.0.0.1:5173
```

Outros comandos:

```powershell
npm run check        # typecheck + ESLint + testes + build
npm run test         # Vitest (jsdom)
npm run lint         # ESLint (typescript-eslint strict, react-hooks)
npm run build        # build de produção em dist/
npm run preview      # serve o build em http://127.0.0.1:4173
```

Requer Node.js 20.19+ (testado com Node 24). O mapa base usa tiles vetoriais públicos do
[OpenFreeMap](https://openfreemap.org) (dados © OpenStreetMap), sem token nem conta; sem internet o
mapa continua funcional com fundo liso e as camadas de dados. Somente a área visível é consultada:
nenhum dado do estudo é enviado a esse serviço.

## Telas

| Rota | Tela | O que faz |
|---|---|---|
| `/` | Dashboard | KPIs do experimento, KM vazio por dia, composição pickup × reposicionamento, tabela comparativa, demanda prevista × observada, desenho D+1 e lista de experimentos |
| `/lab` | Simulation Lab | Mapa da Grande Vitória com demanda H3 (r7), calor de solicitações, solicitações, veículos, reposicionamento planejado (tracejado) e executado (contínuo), trilhas, fluxos entre zonas e concentração; filtros por estado do veículo, desfecho e demanda mínima; painel contextual por clique; linha do tempo |
| `/comparison` | Algorithm Comparison | Dois mapas com câmera sincronizada (mesmo dia, horário, zoom e posição), indicadores por cenário e diferença B − A |
| `/replay` | Historical Replay | Play/pause, velocidade (30×–300×), evento anterior/seguinte, início/fim, linha do tempo com densidade de pedidos, veículos em movimento, rastros acumulados com transparência progressiva, comparação temporal entre estratégias, KM vazio acumulado e log de eventos |
| `/insights` | Experiment Insights | Efeito líquido (cascata), sensibilidade de parâmetros, cobertura, desfecho das recomendações, definições do KM vazio e limitações |

Atalhos do replay: `espaço` (play/pause), `←`/`→` (evento anterior/seguinte), `Home`/`End`.

## Estrutura

```
frontend/
├── index.html, vite.config.ts, eslint.config.js, tsconfig*.json, .env.example
├── public/favicon.svg
└── src/
    ├── App.tsx, main.tsx            # rotas (lazy) e provedores
    ├── components/
    │   ├── ui/                      # design system (Button, Badge, Panel, Select, Switch, Slider, Segmented, Tooltip, Metric…)
    │   ├── maps/                    # FleetMap (MapLibre + deck.gl), estilo base, camadas, transformações, legenda, sincronização
    │   ├── charts/                  # ECharts (tree-shaken, SVG) e um construtor de opção por gráfico
    │   └── simulation/              # motor do replay, relógio, controles e linha do tempo
    ├── features/                    # páginas e regras de apresentação
    │   ├── layout/  dashboard/  lab/  comparison/  replay/  insights/
    │   └── shared/                  # contexto de experimento, hooks de dados, camadas por cenário, rótulos
    ├── services/                    # porta de dados: mock (padrão) e cliente HTTP futuro + adaptadores do Python
    ├── mocks/                       # catálogo e gerador demonstrativo (geografia, frota, eventos)
    ├── types/                       # contratos TypeScript
    ├── lib/                         # métricas, formatação pt-BR, geo, tempo, PRNG
    ├── theme/                       # tema claro/escuro e paleta de dados
    ├── styles/                      # tokens e estilos globais (Tailwind v4)
    └── test/                        # setup do Vitest e substitutos de WebGL/canvas
```

## Contratos e origem dos dados

Os contratos em `src/types/domain.ts` cobrem `Experiment`, `Algorithm`, `Vehicle`, `DemandZone`,
`FleetPosition`, `RepositionMovement`, `RideRequest`, `SimulationEvent`, `ScenarioMetrics` e
`ReplayFrame`, além de `DaySnapshot`, `ScenarioRun`, `ExperimentResults` e `SensitivityAnalysis`.
Toda distância carrega o método (`haversine`); `observedKm` e `returnKm` são sempre `null`.

Os componentes visuais só conhecem a interface `FleetLabDataSource` (`src/services/dataSource.ts`),
consumida pelos hooks de `src/features/shared/useStudyData.ts`. A escolha da origem fica em
`src/services/index.ts`:

| Origem | Arquivo | Uso |
|---|---|---|
| `mock` (padrão) | `services/mockDataSource.ts` → `mocks/generator.ts` | todas as telas hoje |
| `http` | `services/httpDataSource.ts` | futura API Python |

Componentes que hoje consomem mocks (via hooks, nunca importando `mocks/` diretamente): Topbar e
`ExperimentProvider` (experimentos e algoritmos), Dashboard (`useExperimentResults`), Simulation Lab,
Comparison e Replay (`useDaySnapshot` + `useScenarioRun`) e Insights (`useExperimentResults` +
`useSensitivity`). Exceções conscientes: `FleetMap` usa apenas os limites geográficos públicos da
Grande Vitória e os testes do gerador/motor importam `mocks/` para validar invariantes.

### O que é fictício no gerador

- Pedidos, frota (`V-01`…), previsões e posições são sintéticos, com semente fixa, sobre bairros
  públicos aproximados. Não há placas, nomes, IDs internos nem coordenadas individuais reais.
- Os planos **não executam** o guloso (DT001), o proporcional nem a atribuição ótima: são movimentos
  ilustrativos de uma rotina genérica com perfis arbitrários (`DEMO_PLAN_PROFILES`).
- O roteiro de eventos imita apenas o desenho público do replay (corte em D às 20h, mesmo mundo para
  todos os cenários, veículo livre mais próximo, reposicionamento somado ao KM vazio). Não é o
  simulador Python.
- Trajetos são curvas ilustrativas; as distâncias exibidas são Haversine entre pontos.

## Como conectar ao backend Python (futuro)

1. Expor uma API (por exemplo FastAPI) que leia os artefatos **agregados e autorizados** já produzidos
   pelo núcleo (`tcc-frota gold-replay --details` gera `result.json` e `days/<data>.json`) e responda
   nas rotas documentadas em `services/httpDataSource.ts`:
   `GET /experiments`, `/algorithms`, `/experiments/{id}/results`, `/experiments/{id}/days/{date}`,
   `/experiments/{id}/days/{date}/scenarios/{algorithmId}`, `/experiments/{id}/sensitivity`.
2. Converter o formato Python para os contratos do frontend. `services/pythonAdapters.ts` já mapeia
   as métricas por cenário (`estimated_pickup_km`, `estimated_reposition_km`,
   `estimated_km_dead_total`, `coverage`…) e os desfechos (`aplicada`, `motorista_ausente`,
   `motorista_em_corrida`, `conflito_disponibilidade`), e recusa métodos de distância diferentes.
3. Preencher `provenance.kind` corretamente (`real` só com autorização); a interface exibe esse selo
   em todas as telas.
4. Criar `frontend/.env.local` a partir de `.env.example`:

   ```powershell
   Copy-Item .env.example .env.local
   # VITE_DATA_SOURCE=http
   # VITE_API_BASE_URL=http://127.0.0.1:8000/api
   ```

Antes de servir dados reais, respeite `docs/seguranca_dados.md`: apenas agregados ou dados
pseudonimizados autorizados, sem credenciais no frontend e sem envio automático a serviços externos.

## Qualidade

- TypeScript estrito (`strict`, `noUncheckedIndexedAccess`, `noImplicitReturns`…).
- ESLint com `typescript-eslint` (strict), `react-hooks` e `react-refresh`, sem avisos.
- Vitest + Testing Library: gerador (determinismo, corte D+1, sem vazamento, sem ocupação
  simultânea, comparabilidade), motor do replay, métricas, serviços/adaptadores, transformações,
  controles do replay, navegação e interatividade do Lab (MapLibre/deck.gl/ECharts substituídos por
  dublês no jsdom).
- Paleta das estratégias validada para daltonismo (3 cores + baseline neutro); tema claro e escuro.
