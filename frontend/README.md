# FleetLab — Mobility Intelligence (frontend)

POC visual do TCC **Otimização da Alocação de Frota em Aplicativos de Transporte Urbano**: simulação e
comparação de estratégias de alocação preventiva **D+1** para reduzir o **KM vazio estimado**, com a
cobertura de atendimento como controle.

> **Duas origens de dados.** Por padrão (`mock`), tudo vem de um gerador local determinístico em
> `src/mocks/` e é fictício. No modo **dados reais** (`http`), a interface lê os resultados da rodada
> final do TCC (v2), servidos só na máquina local pelo núcleo Python; o selo "Dados reais autorizados"
> e a faixa de aviso aparecem em todas as telas. O texto científico está em `docs/resultados_reais.md`.

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
| `mock` (padrão) | `services/mockDataSource.ts` → `mocks/generator.ts` | demonstração e testes |
| `http` | `services/httpDataSource.ts` | dados reais da rodada v2 via `tcc-frota fleetlab-serve` |

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

## Dados reais da rodada v2 (uso local)

Na raiz do repositório, com os extratos em `data/raw/` e o `final-run` já publicado em `reports/tcc_final/`:

```powershell
$env:TCC_REAL_DATA_AUTHORIZED = 'YES'
.venv\Scripts\python.exe -m tcc_frota.cli fleetlab-export   # gera reports/runs/fleetlab/ (ignorado pelo Git)
.venv\Scripts\python.exe -m tcc_frota.cli fleetlab-serve    # http://127.0.0.1:8000/api, só na máquina local
```

Em outro terminal, com um único `.env.local` contendo `VITE_DATA_SOURCE=http` e `VITE_API_BASE_URL=/api`:

```powershell
cd frontend
npm run build; npm run preview        # mais rápido: http://127.0.0.1:4173
# ou, para desenvolver: npm run dev   # http://127.0.0.1:5173
```

O Vite repassa `/api` para `127.0.0.1:8000` (proxy), então não há CORS e qualquer porta funciona. Mude o destino com `FLEETLAB_API_TARGET` (só endereços locais). Mudanças no `.env.local` ou no `vite.config.ts` exigem reiniciar o Vite.

**Problemas comuns:**

- *Faixa vermelha "Não foi possível carregar os dados":* a API local não está rodando. Deixe `tcc-frota fleetlab-serve` aberto em outro terminal, com `TCC_REAL_DATA_AUTHORIZED=YES`.
- *"porta 8000 ocupada":* já existe outra instância da API; feche-a (Ctrl+C no terminal dela) antes de iniciar outra.
- *Vite subiu em 5174 ou outra porta:* já havia outro Vite aberto. Funciona igual com o proxy, mas feche o antigo para não confundir as abas.
- *Lentidão no primeiro acesso em `npm run dev`:* o Vite pré-processa MapLibre, deck.gl e ECharts na primeira carga. Medido em 16/10/2026 com dados reais: cada tela pronta em 0,7–3,6 s no dev e em 0,6–1,8 s no `preview`.

O que aparece:

- **Experimentos:** março e setembro/2026 (dias de teste), cada um nos regimes B (escala conhecida, plano no fim de D), A (D+1 estrito às 20h) e C (oráculo, só diagnóstico). Janela 04–11h.
- **Estratégias:** sem reposicionamento, guloso de valor marginal (α = 0,2), proporcional e regra de limiar. Os parâmetros são os congelados no `final-run` (`reports/tcc_final/result.json`); o export roda o mesmo simulador e reproduz exatamente os totais da tabela principal.
- **Mapa e replay:** pedidos (inclusive não atendidos) e motoristas reais pseudonimizados. Motoristas aparecem como `M-001…` e pedidos como `P-0001…`; nem o pseudônimo nem o código interno saem do Python. Origem e destino com 3 casas, posição de motorista com 4. Corridas externas (agendadas e fora da janela) ocupam o motorista no simulador, mas não são desenhadas.
- **Distância:** `haversine_fator_rua` (linha reta × fator rua/reta calibrado). Estimativa, nunca odômetro.

Cuidados: os JSONs ficam em `reports/runs/fleetlab/` e o `.env.local` é ignorado pelo Git. O servidor recusa endereços fora de 127.0.0.1, abre a porta em modo exclusivo, aceita CORS só de origens locais, só responde GET e não registra rotas nos logs. `npm run build` com `.env.local` em modo `http` gera um `dist/` que lê a API local; não publique esse build. Os testes forçam o modo `mock` (`vite.config.ts`). O mapa base continua vindo do OpenFreeMap; só a área visível é consultada, sem enviar dados do estudo.

## Contrato da API (referência)

1. A API local `tcc-frota fleetlab-serve` (rodada v2) já implementa este contrato a partir dos arquivos de
   `tcc-frota fleetlab-export`. Outra API que queira substituí-la deve responder nas rotas documentadas em
   `services/httpDataSource.ts`:
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
   # VITE_API_BASE_URL=/api   (proxy do Vite até 127.0.0.1:8000)
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
