# Arquitetura após a reorganização (28/10/2026)

Complementa [arquitetura.md](arquitetura.md) (camadas Bronze/Silver/Gold sintéticas e Databricks). Nome diferente do pedido no roteiro (`ARQUITETURA.md`) porque, no Windows, colidiria com `arquitetura.md`.

## Decisões

| # | Decisão | Motivo |
|---|---|---|
| A1 | Manter `src/tcc_frota/` (layout `src`, pacote único) | já é vertical por domínio; renomear para `tcc_mobilidade` quebraria `pyproject`, 280 testes, scripts e `egg-info` sem ganho científico |
| A2 | Não mover `reports/tcc_final`, `reports/tcc_v2`, `resultados/`, `tabelas/` | 19 hashes da v1 no pré-registro; o artigo e a banca citam esses caminhos |
| A3 | Mover `reviews/` → `reports/thesis_audit/` (`git mv`, conteúdo idêntico) | auditorias são relatórios, não código; era a única pasta fora do padrão |
| A4 | Não dividir arquivos para cumprir 400 linhas / 5 arquivos por pasta | o roteiro proíbe dividir código cientificamente coeso; `algoritmos/` (21 arquivos) e `v3/` (15) excedem a meta por haver um arquivo por método/fase |
| A5 | Não renomear `v3/` nem `scripts/v3_*.py` | o rótulo “v3” (pacote) designa a “extensão v2” (documentos); renomear mudaria comandos citados no pré-registro. Registrado como pendência |
| A6 | Acrescentar `scripts/validar_baseline.py` e `tests/reproducibility/test_estrutura_repositorio.py` | proteção contra regressão estrutural, sem tocar na ciência |

## Fronteiras

- **Dados reais** (`data/`, `reports/runs/`): nunca versionados; testado.
- **Lógica científica:** `v2/`, `v3/`, `algoritmos/`, `availability/`, `analise/`.
- **Orquestração e relatórios:** `cli.py`, `algoritmos/cli.py`, `scripts/`, `v2/final_run.py`, `v2/figures.py`, `algoritmos/relatorio.py`.
- **Configuração:** `config/*.yaml` e grades pré-registradas em `algoritmos/protocolo.py`; `config/custos_privado.yaml` é ignorado.
- **Publicação:** `tcc-artigo-latex/` (repositório aninhado).

## Dependências entre pacotes

`algoritmos` → `v2.policy`, `v2.sim`, `v2.stats`; `v3` → `v2` e `algoritmos` (não o contrário; `v2` não importa `v3`); `availability` é independente do planejamento. Não foram encontradas importações circulares (todos os 103 módulos importam; ver validação).
