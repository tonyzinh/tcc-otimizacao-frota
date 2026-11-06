# 08 — Inventário das branches

Levantamento por `git ls-tree` e `git diff` contra o HEAD (`analise/dimensionamento-frota-pj`, 823 arquivos) e `origin/main` (231 arquivos). **Todas as branches são remotas, exceto `analise/dimensionamento-frota-pj` e `main` (locais).** Datas = último commit da branch.

## 1. Visão geral

| Branch | Último commit | Autor | Arq. totais | Novos vs `main` | O que é |
|---|---|---|---|---|---|
| `main` | 2025-11-05 | Vitor Amorim | 231 | — | Base de 2025: ETL, notebooks de preço mínimo, relatórios LaTeX |
| **`analise/dimensionamento-frota-pj`** (HEAD) | 2026-10-13 | Vitor Amorim | 823 | 654 | **Linha viva**: tudo o de 2026 (diagnóstico de preço, frota, Prime, PF, DRE/PJ) |
| `development` | 2026-08-23 | Vitor dos Santos Amorim | 783 | 615 | Tronco de integração; fundiu o PR "Preço base v1 viagens". **Quase subconjunto do HEAD** (só 3 arquivos fora dele: CSV de centro de custo de veículos, `99_investigar_lacunas.sql` na raiz de `sql/`, `Feedback-App-V1-Viagens.docx`) |
| `feature/analise-v1-prime` | 2026-10-09 | Marcelo P. Marques | 826 | 657 | **Superconjunto do HEAD** + `planos_prime_v1`, `ociosidade_frota_prime_v1` |
| `feature/painel-simultaneidade` | 2026-09-30 | Marcelo P. Marques | 792 | 624 | + `simultaneidade_prime_v1` (painel de casos de simultaneidade) |
| `sigma` | 2026-03-12 | Vitor Amorim | 392 | 189 | Linha de março/2026: `preco-base`, `Avaliacao_final_ano`, `marketing_segmentation`, `analise_precos_min`, relatórios LaTeX (plano de ação, threshold km) |
| `feature/sigma` | 2025-12-17 | Entony J. dos Santos | 4 | 1 | Coletor de snapshots de status de motoristas (API Sigma) |
| `feature/utils_db` | 2025-10-27 | Elias N. N. Silva | 264 | 39 | Utilidades de banco; notebooks 2025/09 de Elias; marketing segmentation; relatório de preço mínimo |
| `feature/latex-reports` | 2025-10-31 | Entony J. dos Santos | 181 | 55 | Modelos LaTeX (`Modelo_referencia/…Preco_minimo`) |
| `fix/repos-restructuring` | 2025-11-03 | Henrique H. R. Perin | 22 | 2 | Reestruturação (`notebooks_analytics/behavior/251031_pf_predict_conversion_funnel`), README de "Precificação Dinâmica — V1" |
| `feature/analise-pf-lara` | 2025-11-05 | Lara A. Nascimento | 65 | 47 | PF: receita 2024×2025, faixa de km, fixo×dinâmico, cupom, cancelamento |
| `feature/avaliacao-pf-Isllan` | 2025-11-05 | Isllan T. Pereira | 81 | 57 | Comportamento PF (distância × gênero × idade); segmentação de marketing |
| `feature/demanda-cancel-Isllan` | 2025-11-05 | Lara A. Nascimento | 50 | 25 | Cancelamento e demanda reprimida |
| `feature/projecao-metas-Isllan` | 2025-10-21 | Isllan T. Pereira | 56 | 31 | Projeção de metas/receita (geral, por carro, por hora) |
| `feature/analise-ticket-km` | 2025-11-11 | Isllan T. Pereira | 46 | 23 | Ticket por km (PF e PJ Padrão) com gráficos interativos |
| `feature/analise-engenharia` | 2025-11-05 | Isllan T. Pereira | 45 | 23 | Análise de projetos de **engenharia** (horas estimadas × realizadas) — fora do domínio de corridas |
| `feature/analise-bairro-isllan` | 2025-10-23 | Isllan T. Pereira | 25 | 20 | Bairros/H3 de maior demanda PF |
| `feature/analise-pj-customizada-isllan` | 2025-10-21 | Isllan T. Pereira | 33 | 8 | Receita semanal e ranking de perda PJ Customizado |
| `feature/analise-demanda-reprimida-tony` | 2025-10-22 | Entony J. dos Santos | 20 | 12 | Notebooks de demanda reprimida (geral/PF/PJ) |
| `feature/analise-geral-outubro` | 2025-11-03 | Entony J. dos Santos | 22 | 14 | Análise geral outubro/2025 (PF) e receita por horário |
| `feature/analise-resultado-por-carro-tony` | 2025-10-22 | Entony J. dos Santos | 31 | 15 | Resultado financeiro por carro |
| `feature/analise-pj-padrao-tony` | 2025-09-11 | Entony J. dos Santos | 27 | 3 | PJ Padrão (`extracoes_pj_padrao_tony*.sql`) |
| `feature/analise-pf-cupom-elias` | 2025-09-15 | Elias N. N. Silva | 33 | 9 | PF × cupom |
| `feature/analise-queda_receita_por_pj-elias` | 2025-09-19 | Elias N. N. Silva | 35 | 11 | Queda de receita por empresa PJ |

> Nota de leitura: "Novos vs main" conta arquivos adicionados (qualquer tipo, inclusive imagens/LaTeX), não mérito analítico. As branches de 2025 repetem o mesmo **esqueleto** (ETL `src/etl/[01..03]`, `src/pricing/*` vazio, `notebooks/01_eda…04_simulacao`, `etl_audit.ipynb`, `run_pipeline.ps1`, `pyproject.toml`, `sql/extraction/*`, `sql/testes/*`) e acrescentam a sua análise.

## 2. O que só existe em branches (não está no HEAD)

| Conteúdo | Branch(es) | Observação |
|---|---|---|
| **`planos_prime_v1`**: catálogo de planos Prime, planos ativos, simultaneidade, intervalo entre corridas, auto-sobreposição, coordenadas, `exploracao_banco/99*_*.sql`, `Análise_Pontual_Prime.xlsx` | `analise-v1-prime` | Ver [06](06_prime.md) |
| **`ociosidade_frota_prime_v1`**: heatmap de ociosidade (27,9% por hora cheia; 53,5% por minuto ocupado) | `analise-v1-prime` | Ver [06](06_prime.md) §6 |
| **`simultaneidade_prime_v1`**: notebook + SQL 04/06/07 + gerador de HTML | `painel-simultaneidade` | Ver [06](06_prime.md) §4 |
| **Coletor Sigma** (`status_snapshot.py`, README de agendamento no Windows) | `feature/sigma` | Ver [07](07_frota_e_operacao.md) §7 |
| **Pipeline H3 / bairros** (`src/filtragem_bairros/h3_processor/*`, `ES_Municipios_2024.dbf`) | `analise-bairro-isllan` | Corridas PF encerradas, GV, valor>R$ 500, jan–out/2025; resolução H3 8; saídas `mapa_h3_integrado.html`, `relatorio_h3_integrado.html`; usa Folium, h3, SQLAlchemy |
| **Análise de engenharia** (`projetos_2025.parquet`, `utils_v1/gerador_html/*`) | `analise-engenharia`, `analise-ticket-km` | Projetos de engenharia (fases DTI, Inovatech, Homologação); desvio % = (estimado−executado)/estimado; exemplos: VIX MOVE 159 h → 986 h; IDMAN 823 h → 3.554 h. `utils_v1/gerador_html` gera HTML interativo a partir de notebooks (seletor, renderizador de gráficos) |
| **Cancelamento / demanda reprimida** | `demanda-cancel-Isllan`, `analise-demanda-reprimida-tony`, `analise-geral-outubro` | `Corrida_cancelada_heatmap_{1,2}.sql`, `Corrida_cancelada_macro_{1,2,3}.sql`, `Query_Canceladas(_Completa).sql`, `Query_Reprimida.sql`, `demanda_reprimida.sql`, `analise_geral.sql`, `receita_por_horario.sql` |
| **Projeção de metas** (`calculador_metas.py`, `calculador_precificacao.py`, `analisador_performance.py`, `extrator_dados.py`, `gerador_relatorios.py`, `principal.py`) | `projecao-metas-Isllan` | Pipeline orientado a objeto; custo operacional = distância × R$ 2,50 |
| **PF Lara** (`analise_geral/{cupom,faixa_km,receita,rendimentos,sql}`, `analise_pf/{corridas_canceladas,faixa_km,fixo_dinamico,sql}`, `analise_pj/sql`) | `analise-pf-lara` | Receita básica 2024 × 2025; `tabela_rec_lucro_custo.sql`; `previsao.sql`; `pf_fixo_temporal.sql` |
| **PF preço-base / dinâmico × fixo** (`preco-base/…`, `Avaliacao_final_ano/avaliacao_2025.ipynb`) | `sigma` | Linha de março/2026 |
| **Funil de conversão preditivo** (`251031_pf_predict_conversion_funnel`, notebooks de extract/transform/validate/ML linear) | `fix/repos-restructuring` | Arquivos aparecem sem extensão (nomes `nb_sql_ext_…`, `nb_mod_regression_linear_funnel`): possível problema de nomenclatura |
| **Notebooks 2025/09 de PF × cupom e queda de receita PJ** (`setup_syspath.py`) | `feature/utils_db` | |
| **Relatórios LaTeX 2025** (`Relatorios_entregas_tex/…`) | `latex-reports`, `utils_db`, `sigma` | No HEAD a pasta existe em minúsculas: `relatorios_entregas_tex/` (renomeada; "corrige caixa da pasta"). Relatórios: Preço mínimo, V1 plano de ação, V1 Prioridade threshold km (2025-10); marketing (2025-11); Projeção de ações (2025-12); preço dinâmico (2026-01, slides de 2 págs.); Pesquisa de mercado (2026-03). Modelo base: `book-unizar.cls` (Univ. de Zaragoza) |

## 3. O que só existe no HEAD (e nas posteriores)

Estudo do **preço real e novo preço** (`diagnostico_novo_preco_v1`), **funil de conversão**, **DRE e PJ customizado**, **frota dedicada PJ e capacidade Prime**, **Prime corridas seguidas / monetização**, **PF consolidado (01–04)**, **custos da operação**, **Sigma API** (cliente), **sql_pipeline**, **feedback do app**, **TCC** e consultas de aeroporto/top-20. 118 arquivos do HEAD não estão em `development`.

## 4. Relação de fusão (resumo)

```text
main (nov/2025) ── features de 2025 (Isllan, Tony, Elias, Lara, Perin…) ──┐
   └─ sigma (mar/2026)                                                    │
development (ago/2026, PR "Preço base v1 viagens") ────────────────────────┤
   └─ analise/dimensionamento-frota-pj (HEAD, out/2026)                    │
        ├─ feature/painel-simultaneidade (set/2026)  ─ Marcelo             │
        └─ feature/analise-v1-prime (out/2026) ─ Marcelo (superconjunto)   ┘
```
(Estrutura inferida pelo conteúdo e pelas contagens; não conferi a topologia exata do grafo de commits.)

## 5. Observações de higiene

- Muitas branches de 2025 estão **desatualizadas** e carregam `uv.lock`, `.vscode/*`, `data/{raw,interim,processed}/.gitkeep`, parquet/joblib e CSVs de dados (`users_features.csv`, `persona_cards.csv`, `projetos_2025.parquet`, `nome.csv`): contrariam a regra atual de "dado não entra no git".
- **Dados pessoais em branches:** `outputs_mkt_2025/users_*.csv` e listas de CRM — tratar com cuidado (LGPD).
- A decisão registrada em 22/08/2026 foi **não reescrever** o histórico (≈ 499 MB de pack, 1,2 GB em `.git/objects` em 21/08; blobs de caminhos que não existem mais); revisitar só se o tempo de clone virar problema.
- Autoria: dois autores aparecem com o sufixo "(VIX Matriz)" no nome e uma mensagem de merge cita `dev.azure.com/ag…` → o remoto é **Azure Repos** (limite 250 GB; recomendado <10 GB, segundo o `CLAUDE.md`).
