# Mapeamento TCC → código

Capítulos conforme [TCC_ESTRUTURA.md](TCC_ESTRUTURA.md). Artefatos de `reports/` são agregados já versionados; os que dependem de dados reais só se regeneram com `data/raw/`.

| Seção / afirmação | Código | Evidência versionada |
|---|---|---|
| 4 Metodologia: corte D+1, sem vazamento | `algoritmos/base.py` (`PlanContext`), `v2/policy.py`, `scripts/nao_vazamento_seletivo.py` | `docs_antigos/metodologia.md`, `docs_antigos/simulacao.md` |
| 4 Qualidade e limpeza dos dados | `v2/rules.py`, `v2/silver.py`, `quality/audit.py` | `reports/tcc_final/tab02_qualidade.csv` |
| 5 Demanda por hora/zona | `analise/demanda.py`, `v2/forecast.py`, `scripts/rodar_demanda.py` | `tab03`, `tab07`, `fig01`, `fig03`, `resultados/demanda/` |
| 5 Não atendimento por zona | `v2/final_run.py` | `tab04`, `tab17`, `fig02` |
| 5 Frota | `v2/fleet.py` | `tab05` |
| 6 Simulador e calibração | `v2/sim.py` | `tab08`, `tab09`, `tab10`, `resultados/calibracao/` |
| 6 Planejadores de referência (guloso, proporcional, limiar) | `v2/policy.py` | `tab11`, `tab13` |
| 6 Bateria de 13 algoritmos | `algoritmos/*.py` | `resultados/tabela_final_criterios.csv`, `tabelas/tab_bateria_*.tex`, `docs_antigos/BATERIA_ALGORITMOS.md` |
| 6 Guloso seletivo C0–C3 | `algoritmos/guloso_seletivo.py`, `seletivo.py` | `resultados/seletivo/`, `docs_antigos/RESULTADO_SELETIVO.md`, `tabelas/tab_seletivo_criterios.tex` |
| 7 Efeito principal (KM vazio/corrida, corridas) | `v2/stats.py`, `v2/final_run.py` | `tab11`, `tab12`, `fig05` |
| 7 Ponto de equilíbrio `e` | `analise/valor_liquido.py`, `v3/inferencia.py` | `tab14`, `fig07`, `tabelas/tab_equilibrio_*.tex` |
| 7 Escada de informação / oráculo | `v3/fase3.py` | `tab15`, `fig06`, `reports/tcc_v2/fase3_*` |
| 7 Fronteira de Pareto | `algoritmos/relatorio.py` | `tab16`, `fig04`, `resultados/fronteira_pareto.*` |
| 7 Inferência robusta (bootstrap dependente, Romano–Wolf, Fieller, MDE) | `v3/reamostragem.py`, `v3/inferencia.py`, `v3/fase1.py` | `reports/tcc_v2/fase1_*` |
| 7 Controles positivo/negativo, poder | `v3/controle.py`, `v3/fase2.py` | `fase2_*`, `fase2_curva_poder.pdf` |
| 7 Baselines B0–B4, recuperabilidade ρ, conformidade | `v3/deriva.py`, `v3/avaliacao4.py`, `v3/fase4.py` | `fase4_*` |
| 7/8 Decisão por NB(e\*) | `v3/decisao.py`, `v3/mde_nb.py` | `fase1_nb*.csv`, `docs_antigos/EXEMPLO_DECISAO.md` |
| 8 Limitações | — | `docs_antigos/limitacoes.md`, `docs_antigos/PREMISSAS_E_LIMITACOES.md`, `reports/thesis_audit/` |
| Hipóteses e critérios pré-registrados | — | `docs_antigos/V2_PREREGISTRO.md`, `docs_antigos/ORCAMENTO_CONFIGURACOES.md` |
| Disponibilidade operacional | `availability/` | `docs_antigos/disponibilidade.md` |
| Ética/LGPD | `v2/raw.py` (pseudonimização), `.gitignore` | `docs_antigos/seguranca_dados.md` |

Rastreabilidade de execução: `resultados/registro_configuracoes.csv` (configurações), `resultados/finalistas.json` (congelamento), hashes da v1 no pré-registro, tag `v1-congelada`.
