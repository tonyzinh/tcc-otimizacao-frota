# 09 — Catálogo de código, consultas e convenções

## 1. Mapa de pastas (HEAD)

| Pasta | Conteúdo |
|---|---|
| `sql/` | ~75 consultas ad-hoc compartilhadas + `DICIONARIO_BANCO.md` (+ subpastas `consultas/`, `extraction/`, `testes/`) |
| `analises/<nome>_v1/` | Uma análise fechada: `README.md`, `docs/`, `sql/`, `dados/{bruto,intermediario,modelado}/`, `src/`, `outputs/` |
| `analises/diagnostico_novo_preco_v1/` | Queda de vendas após o deploy do preço real (a mais atual em preço) |
| `analises/frota_dedicada_pj_v1/` | Frota dedicada PJ, capacidade Prime, painéis (89 arquivos) |
| `analises/dre_simulacoes_preco/` | DRE, MC02, simulações por cliente PJ (encerrada) |
| `analises/pessoa_fisica/` | 01 comportamento, 02 preço mínimo, 03 novo preço, 04 acurácia |
| `analises/prime_corridas_seguidas_v1`, `prime_monetizacao_v1` | Prime |
| `analises/funil_conversao_v1`, `custos_operacao_v1`, `marketing_segmentation`, `km_por_placa` | Funil, custos, marketing, rodagem |
| `sigma_api/` | Cliente da API Sigma (`src/client.py`, `config.py`, 2 scripts) |
| `scripts/` | `checar_arquivos_pesados.sh`, `hooks/pre-commit`, `sql_pipeline/{core,cli,scaffold}.py` |
| `relatorios_entregas_tex/` | Entregáveis LaTeX por mês (7 pastas) |
| `feedback-app-v1/` | Avaliação de UX (35 prints, 4 relatórios .md, .docx) |
| `docs/` | `REGRAS_NEGOCIO_TCC.md` e esta pasta |
| `src/`, `notebooks/`, `data/` | **Vazios/resíduo** no HEAD (ETL de 2025 existe só em branches) |
| `azure-pipelines.yml` | CI: roda o verificador de arquivos pesados em todo PR |

## 2. Convenções de SQL (não negociáveis, `CLAUDE.md`)

- `WITH (NOLOCK)`; janela semi-aberta; dedup de `APP_SOLICITACAO_HIST`; `DATEDIFF(SECOND)/60.0`; `NULLIF` + piso.
- **Cabeçalho YAML** em todo arquivo: `type`, `owner`, `issue`, `source`, `dest`, `params`, `depends_on`, `change_log`.
- Parâmetros em `DECLARE` no topo, marcados `-- AJUSTE AQUI`.
- **Banner** `-- >>> RESULT SET N -> salvar como: <nome>.csv` por grade; o CSV vai para `dados/bruto/` com esse nome. O banner virou **contrato executável**: `regenerar_dados.py` o lê.
- Comentários em português **sem acento em letras** (em-dash liberado). *(Na prática muitos arquivos antigos de `sql/` não seguem — são anteriores à convenção.)*
- Numeração por fase em `frota_dedicada_pj_v1/sql/` (`0x` dimensionamento, `1x` PJ, `2x` Prime, `3x` jornada/disponibilidade, `99` exploração).

## 3. Regras de análise (do `CLAUDE.md`)

Nunca zero no lugar de nulo · comparar período aberto em média diária · mediana ao lado da média · declarar cobertura (`%` de linhas em que o campo existe) · "achado de qualidade de dado vale mais que achado de negócio" · registrar no `CLAUDE.md`/dicionário toda descoberta de schema · questionar a premissa, não só o número (dizer se o dado aponta produto inviável, segmento que destrói margem ou horário em que a frota é sequestrada).

## 4. Dados pesados e o que nunca entra no git

Contexto: em 21/08/2026 o repositório tinha 1,2 GB em `.git/objects`; regras de `.gitignore` por pasta quebraram na renomeação `data/ → dados/`; um `Faturamento Março_v09.xlsx` de 55 MB ficou versionado mesmo com regra. Seis CSVs antigos respondem por ~1,4 GB do histórico somando versões.

Três camadas de defesa: (1) `.gitignore` global com bloco "Artefatos pesados" (`csv, tsv, jsonl, xlsx, pptx, docx, joblib, pkl, parquet, db…`, `**/dados/bruto/`); (2) `scripts/hooks/pre-commit` (limite de **5 MiB** por blob; instalar com `git config core.hooksPath scripts/hooks` e `git config hooks.maxfilesize 5`); (3) `azure-pipelines.yml` (mesmo `scripts/checar_arquivos_pesados.sh`). Dado extraído do banco **não entra**; entram só entradas não regeneráveis liberadas com `!` explícito e comentário de origem.

## 5. Pipeline de regeneração

`analises/frota_dedicada_pj_v1/regenerar_dados.py`: `--listar` · `--verificar` · `--executar [--forcar] [--somente <arq>] [--timeout S] [--testar-conexao]`.
- Lê os banners `-- >>> RESULT SET N -> salvar como: dados/bruto/<nome>.csv` (regex aceita rótulo alfanumérico `0a`/`0b` e prefixo `BLOCO N /`).
- **Conexão:** `DB_CONNECTION_STRING` (formato `mssql+pyodbc://@<servidor>.database.windows.net/<banco>?driver=ODBC+Driver+18+for+SQL+Server`, mesmo `.env` do projeto irmão `sql-query-pattern`); sem usuário/senha ⇒ **token Azure AD** (`AZURE_ACCESS_TOKEN` ou `DefaultAzureCredential` via `az login`); `V1_SQL_*` é fallback que **não serve** para o banco atual. Requer **ODBC Driver 18**, `azure-identity`, `python-dotenv`. A string do `.env` traz `applicationintent=ReadOnly` (réplica de leitura).
- **pyodbc puro** (precisa de `cursor.nextset()` para vários RESULT SETs).
- **Execução única** por consulta (antes rodava duas vezes: contagem + gravação); CSV temporário `.tmp_regenerar_*` na pasta da análise, movido por `shutil.move` só se a contagem bater.
- **`ARITHABORT`**: o driver ODBC abre sessão com `ARITHABORT OFF` (SSMS usa `ON`), o que muda a chave do cache de planos — explica "3 s no SSMS, trava no script". `conectar()` aplica as opções de sessão do SSMS. Segunda hipótese: SSMS contra o primário × script contra a réplica read-only. `--testar-conexao` separa as duas.
- `scripts/sql_pipeline/` generaliza o padrão (`core`, `cli`, `scaffold`); **está atrás** do `regenerar_dados.py` (falta token Azure AD, `.env`, execução única, `ARITHABORT`). Decisão em aberto: portar as quatro coisas e então trocar. **Nada gera SQL** — só executa SQL escrito à mão (corpus de 92 consultas + dicionário permitiria um gerador).
- Alternativa em `painel-simultaneidade`: `src/conexao_banco.py` (mesma lógica) e notebook que troca os `DECLARE` por parâmetros.

## 6. Scripts Python relevantes por análise

| Análise | Scripts |
|---|---|
| `frota_dedicada_pj_v1/capacidade_prime` | `diagnosticar_transbordo.py`, `estado_no_transbordo.py`, `exportar_frota.py`, `presenca_ociosos.py`, `padrao_jornada_sem_corrida.py`, `build_cessao_agosto.py`, `build_criterios_frota.py`, `build_frota_agosto.py` |
| `.../dimensionamento` | `dimensionar_frota.py`, `gerar_excel_frota.py`, `gerar_excel_transbordo_prime.py` |
| `.../ocupacao_frota` | `montar_painel.py`, `basemap.py`, `regenerar_ocupacao_multidia.py`, notebook `notebook_frota_e_reserva_20260911/` (`LEIA_PRIMEIRO.md`, `FONTES_E_RESERVA.md`) |
| `.../osrm` | `rotear_corridas.py` |
| `.../auditoria_20260911` | 8 arquivos de verificação |
| `dre_simulacoes_preco/clientes_pj/_motor` | `gerar_entrega.py`, `gerar_analise_mc02.py`, `comparativo_carteira.py`, `gerar_capa.py`, `agregar_simulacao.py`, `build_simulacao_xlsx.py`, `validar_simulacao.py`, `docx_report.py` |
| `pessoa_fisica/01_comportamento_pf/src` | `tratamento.py`, `features.py`, `recorrencia_retencao.py`, `clusterizacao.py`, `utils.py`, `target.py` |
| `pessoa_fisica/01_comportamento_pf/analises/estrategia_crm_pf` | `executar_crm.py`, `executar_tudo.py`, `gerar_excel_resumo.py`, `gerar_listas_segmentos.py`, `concatenar_bases.py` |
| `funil_conversao_v1/src` | `gerar_excel_funil.py` |
| `prime_corridas_seguidas_v1/src/regra_simultaneidade` | `casos.py`, `graficos.py`, `build_pdf.py`, `build_docx.js` |
| `prime_monetizacao_v1/src` | `build_monetizacao.py`, `build_acumulo.py`, `figuras_*.py`, `acumulo.py`, `estilo.py` |
| `sigma_api` | `src/client.py`, `config.py`, `scripts/01_listar_motoristas.py`, `02_alterar_preco.py` |

Dependências típicas (`requirements.txt`): pandas, numpy, matplotlib, seaborn, plotly, scikit-learn (KMeans), statsmodels, sqlalchemy, pyodbc, azure-identity, python-dotenv, openpyxl, reportlab, weasyprint, pypdf, folium/h3 (branch bairro).

## 7. Catálogo das consultas de `sql/` (raiz)

| Grupo | Arquivos |
|---|---|
| **Extrações brutas / depuração** | `app_solicitacao_hist_2025(.sql, copy)`, `extracao2`, `consultas.sql` (identificação de colaboradores/usuários/motoristas, agendamentos, cupons, parâmetros de preço), `big_consulta` (jan–fev/2026 por mês), `suporte_big_query`, `teste`, `teste2`, `testex`, `test`, `testes_lara` |
| **Composição de preço** | `composicao_preco(.sql, _ticket, _v2)` (cotação com DV/DP/DR, custo veículo/motorista), `corridas_estimativas_precificacao_original.sql` (estimado × realizado, base de testes de unidade), `ticket_km` |
| **Funil** | `funil_conversao.sql`, `funil_estimativa_solicitacao_corrida_pf_pj.sql` (12–21/mai × 12–21/jun) |
| **Corridas/Prime por período** | `corridas_marco_2026`, `corridas_prime_15jun2026`, `estatisticas_pickup_viagem_regiao1_nao_prime`, `diag_pickup_log_marco` (texto exato de `TX_STATUS` — achou o `Conductor` vs `Condutor`) |
| **Faturamento / segmento** | `faturamento_por_segmento_mar_{jun,jul}_2026`, `faturamento_diario_pf_pj_regiao1_30jul_02ago2026`, `consolidado_novo_preco_mar_jul_2026`, `consolidado_valores_por_perfil` |
| **PF** | `pf_grupos_intensidade_subsegmento_*`, `pf_heavy_users_*`, `pf_top20_clientes_*`, `pf_corridas_aeroporto_*` (5), `pf_clientes_aeroporto_madrugada_jul_set2026`, `ext_marketing_pf_*`, `ext_solicitacao_hist_nome(_idade)`, `segmentacao_geral`, `base_clusterizacao_corridas_teste` (testa `TX_LOGIN` e `TX_TELEFONE` na base) |
| **PJ** | ver [05](05_pj.md) §6 |
| **Cupom/desconto** | `cupom_desconto` (`ESP_RELATORIO_FATURAMENTO`), `explorar_cupom_desconto` |
| **Inventário de schema** | `inv_colunas_aceite_solicitacao_hist`, `inv_colunas_app_empresa`, `explorar_fin_parametro_pagamento_pj_customizado` |
| **Lookups de uma corrida** | `lookup_solicitacao_hist`, `lookup_solicitacao_por_cd`, `lookup_agendamento` (usar `@cd_solicitacao`) |
| **Frota/veículo** | `km_faturado_por_placa`, `placa_modelo_veiculo`, `placa_tempo_` |

`analises/diagnostico_novo_preco_v1/sql/`: C1 `quem_parou_de_andar` · C2 `quanto_pagavam` · C3 `estimado_x_real` · C4 `ciclo_km_tempo_pf_regiao1` (grão de corrida) · C5 `base_estimado_x_real_km_tempo` (crua, mai–jul) · C6 `ticket_km_faixa_dv_pf` · C7 `composicao_preco_mc02_pf` · C8 `preco_km_elasticidade_pf` · C9 `preco_fixo_migracao_viagem_longa` · C10 `funil_unificado_fixo_dinamico` · `_apoio/inspecionar_ciclo_da_corrida.sql`.

## 8. Avaliação de UX do app (`feedback-app-v1`)

35 prints de uma **versão beta** do app + relatórios `analise-lote-01/02.md`, `recomendacoes-ux.md`, `prompts-mockups.md`, `Feedback-App-V1-Viagens.docx`. Formato por item: tela, problema, sugestão, prioridade, heurística de Nielsen. Achado de maior valor (P1, alta prioridade, alto esforço): **não é possível alterar o trajeto/inserir parada durante a viagem** — só trocar o destino final, embora a operação já suporte (hoje negociado verbalmente com o motorista e cobrado ao final se passar da tolerância), o que gera custo de experiência e **perda de receita/dado** (parada combinada de boca pode não ser registrada). O documento também discute a faixa azul de cupons na home (não é botão), excesso de "cards" que nivela o destaque, e as duas opções de serviço na confirmação ("Serviço padrão V1 — R$ 31,93 — 5 min" e "V1 Prioridade").
