# Elasticsearch local: contrato e limites

Esta adaptação usa apenas `data/raw/{solicitacoes,ofertas,sumarios}/YYYY-MM/dados.jsonl` entre 2025-10 e 2026-09. Os `pagina_*.json` representam os mesmos documentos e não entram na soma. Bronze guarda referência, tamanho e hash do manifesto; Silver JSONL guarda o documento deduplicado por `_id` quando existir ou hash do conteúdo; Silver Parquet tipa apenas campos aceitos; Gold Parquet agrega por data/hora. Originais nunca são alterados. Runs sensíveis ficam em `reports/runs/elasticsearch/<run_id>/`, ignorados pelo Git. Mudança em manifesto, tamanho ou data de modificação do JSONL gera outro run; a nova versão é reprocessada integralmente para garantir deduplicação entre meses. Runs anteriores não são apagados automaticamente.

## Esquema observado e decisões de uso

Inspeção estrutural da primeira linha de cada mês em 14/10/2026; é uma amostra de esquema, não auditoria de completude por coluna. Os 36 manifestos presentes dizem `completed`, região 1 e possuem `dados.jsonl`. As primeiras linhas de solicitações variam em presença de `cD_MOTORISTA`, `cD_VEICULO` e `logStatus`.

**Auditoria local completa em 14/10/2026:** 36/36 meses conferidos, sem divergência entre contagem declarada e lida: 451.386 solicitações, 262.708 snapshots de ofertas e 262.708 sumários. Não houve duplicatas documentais pelo marcador `_id`/hash nem repetição de `codigo` de solicitação nesta extração; foram 451.386 IDs distintos. Isto não confirma que a extração capture todas as versões históricas ou o instante de criação. `logStatus` está presente em 446.519 documentos de solicitação e ausente em 4.867; `cD_MOTORISTA` aparece em 271.582 e `cD_VEICULO` em 268.552 documentos (presença da chave, incluindo eventual valor nulo). Os snapshots contêm 10.556.363 entradas de oferta. O diagnóstico registrou 8.080 posições com idade acima de 120 minutos e 982 timestamps de posição posteriores ao snapshot. Todos os 262.708 sumários passaram pela tipagem básica de horário com offset e sete contadores inteiros não negativos. Relatório local: `reports/runs/elasticsearch/5230ded5bd206dc8/coverage.json` e `analytics_coverage.json` (não versionados).

**Perfil temporal adicional:** o proponente confirmou que nenhum campo ou evento está validado como criação. Em 436.130 documentos, `dT_REGISTRO` do documento antecede todos os eventos de `logStatus`; 4.867 não têm histórico de status. Isso torna o campo útil como **proxy exploratória de registro**, sem provar que seja `created_at`. O perfil agregado está em `request_time_profile.json` no mesmo run. A série exploratória `exploration/registration_proxy_hourly.parquet` contém 451.386 registros tipados e deduplicados por `codigo`; ela não é a tabela Gold de demanda validada. Um ensaio D+1 local para 30/09/2026, corte 29/09 às 20h, usou 52 quartas feiras anteriores e estimou 1.402,27 registros no dia. Esse número não é previsão validada de solicitações criadas.

| Dataset | Campos observados | Uso implementado | Portão |
|---|---|---|---|
| Solicitações | `codigo`, `dT_REGISTRO`, `tX_STATUS`, `logStatus[]` com `dT_REGISTRO`/`tX_STATUS`; IDs opcionais de motorista/veículo, região, tempos de corrida | dedup por `codigo`; evento explicitamente escolhido pode gerar hora de criação; Gold temporal sem coordenadas | `dT_REGISTRO` do documento não é criação validada; o significado do evento escolhido exige validação |
| Ofertas | `codigo`, `codigoRegiao`, `dataHora`, `ofertaList[]`; no exemplo há status, latitude, longitude, H3 e horários GPS/atualização | contagem de snapshots, entradas, coordenadas inválidas/ausentes e posições com mais de 120 min; nenhum veículo elegível | vínculo motorista–veículo, continuidade, status e posição futura sem validação |
| Sumários | `codigo`, `codigoRegiao`, `dataHora`, sete contadores `qtd*` | Silver tipada; Gold com número de snapshots e média de `qtdOnline` por hora | `qtdOnline` não representa veículos livres; soma entre snapshots não é frota distinta |

Timestamps observados nas primeiras linhas têm offset explícito. O parser rejeita timestamp sem fuso; as tabelas tipadas guardam UTC e agregam o calendário em `America/Sao_Paulo`. Isto não comprova a semântica de cada relógio de origem. Campos ausentes, tipos observados, contagens divergentes e meses incompletos são registrados em `coverage.json`. Meses com contagem divergente não entram nas tabelas tipadas/Gold.

## Correspondência com fontes anteriores

| Entidade | Correspondência antiga → Elasticsearch | Estado |
|---|---|---|
| Solicitação | `CD_SOLICITACAO` → `codigo` | candidata; igualdade de entidade/chave depende de confronto autorizado |
| Corrida | `CORRIDAS_V1` → tempos/status em solicitação | candidata; evento de corrida exige semântica e intervalos validados |
| Motorista | `CD_MOTORISTA` → `cD_MOTORISTA` / `ofertaList.codigo` | indeterminada; nenhum join implementado |
| Veículo | `CD_VEICULO` → `cD_VEICULO` | candidata; identificador e vínculo temporal não confirmados |
| Status | `EVENTOS_STATUS_MOTORISTAS` → `ofertaList.status` | indeterminada; enum e intervalos não confirmados |
| Jornada | `JORNADAS_MOTORISTAS` → sem campo equivalente observado | indeterminada |
| Posição | `COBLI_EVENTOS` → latitude/longitude/H3 da oferta | candidata como localização do ofertante, incompatível como origem da solicitação |
| Disponibilidade | estados reconstruídos dos CSVs → oferta/sumário | indeterminada; Online e `qtdOnline` não provam veículo livre |
| Região | região antiga → `cD_REGIAO` / `codigoRegiao` | candidata; região administrativa não é coordenada de origem |
| Tempo de referência | `DT_REGISTRO` antigo → `dT_REGISTRO`/`dataHora` | indeterminada para criação; offset observado, significado pendente |

## Execução PowerShell

Instale o projeto e o extra Parquet no ambiente Python autorizado. Na raiz do projeto:

```powershell
python -m pip install -e ".[parquet]"
$env:TCC_REAL_DATA_AUTHORIZED = 'YES'
python -m tcc_frota.cli es-inventory --raw-root data/raw
python -m tcc_frota.cli es-audit --raw-root data/raw --out reports/runs/elasticsearch
python -m tcc_frota.cli es-build --raw-root data/raw --out reports/runs/elasticsearch
python -m tcc_frota.cli es-profile-requests --run reports/runs/elasticsearch/SEU_RUN_ID
python -m tcc_frota.cli es-explore-demand --run reports/runs/elasticsearch/SEU_RUN_ID
python -m tcc_frota.cli es-forecast --run reports/runs/elasticsearch/SEU_RUN_ID --cutoff 2026-09-29T20:00:00-03:00 --target-date 2026-09-30 --slot-hours 1 --exploratory-registration-proxy
```

Sem confirmação de criação, `es-build` gera diagnóstico de ofertas, Silver de sumários e Gold agregado de `qtdOnline`; o Gold de demanda permanece bloqueado. `es-explore-demand` oferece a série de registro **fora de Gold**, e a opção `--exploratory-registration-proxy` explicita essa condição na previsão. Após validar **qual** evento de `logStatus` significa criação de solicitação e quando ele já era conhecido, passe `--creation-status VALOR_VALIDADO` a `es-build`. Também existe `--creation-field CAMPO_VALIDADO` para um campo específico comprovado; `dT_REGISTRO` do documento é recusado como criação. Não escolha o parâmetro por semelhança de nome. O `run_id` aparece no resultado; para previsão temporal validada, quando o gate for resolvido:

```powershell
python -m tcc_frota.cli es-forecast --run reports/runs/elasticsearch/SEU_RUN_ID --cutoff 2026-09-29T20:00:00-03:00 --target-date 2026-09-30 --slot-hours 1
```

O corte e o alvo acima ilustram apenas a interface. O baseline usa médias de dias completos de mesmo dia da semana anteriores ao corte, com fallback para todos os dias completos. A falta de mês é registrada; o backtest só é interpretável quando a cobertura da janela e o evento de criação estiverem validados. `ingestion/es_bridge.py` é a interface com o `greedy_plan` original: exige previsão por zona de origem, horários de criação, elegibilidade, posições, ocupação e jornadas validadas. O Gold atual, apenas temporal, falha nesse portão. Sem origem/destino confiáveis e frota elegível, não há plano guloso nem replay real. O fluxo sintético continua em `run-synthetic`.
