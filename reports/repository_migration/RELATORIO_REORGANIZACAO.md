# Relatório de reorganização (28/10/2026)

Commit-base `abf4c5c` (ramo `v2-extensoes`); estado original em `git_status_original.txt`. Nada foi commitado nem enviado; nenhum histórico, ramo ou tag foi tocado.

## Problemas estruturais encontrados

1. `reviews/` (auditorias) fora de `reports/`.
2. Sem verificação automática de estrutura (hashes, importações, pontos de entrada, dados reais fora do Git, caminhos de usuário).
3. Sem guia único: documentos dispersos em `docs/` e README desatualizado quanto à v2/bateria.
4. Rótulo `v3` (pacote/scripts) para a “extensão v2” (documentos); `scripts/` plano com 19 arquivos; `algoritmos/` (21) e `v3/` (15) acima de 5 arquivos por pasta; `pyproject.toml.bak` versionado.

## Nova organização

Reorganização **mínima e deliberada** (decisões A1–A6 em [ARQUITETURA_REORGANIZADA](../../docs/ARQUITETURA_REORGANIZADA.md)): a estrutura vertical por domínio já existia e caminhos científicos são citados por hashes e pelo artigo. Mover mais traria risco de reprodutibilidade sem ganho verificável.

## Arquivos

| Categoria | Qtde | Itens |
|---|---:|---|
| Movidos (`git mv`) | 2 | `reviews/DATA_SCIENCE_AUDIT.md`, `reviews/code_review_report.md` → `reports/thesis_audit/` (conteúdo idêntico) |
| Modificados | 2 | `docs/V2_PREREGISTRO.md` (nota de caminho na linha de fonte), `README.md` (seção de entrada e índice) |
| Criados | 10 | `docs/GUIA_COMPLETO_REPOSITORIO.md`, `ARQUITETURA_REORGANIZADA.md`, `COMO_EXECUTAR.md`, `MAPEAMENTO_TCC_CODIGO.md`; `scripts/validar_baseline.py`; `tests/unit/test_estrutura_repositorio.py`; esta pasta (`baseline_antes.json`, `baseline_depois.json`, `git_status_original.txt`, 2 relatórios) |
| Preservados | todos os demais | inclusive `reports/tcc_final` (19 hashes idênticos), `reports/tcc_v2`, `resultados/`, `tabelas/`, `config/`, `databricks/` |
| Não rastreado/preexistente | — | `docs/TCC_CAP3_*`, `docs/TCC_REFERENCIAS_ANOTADAS.md`, `tcc-artigo-latex/` (Git aninhado): intocados |

Compatibilidade: nenhum módulo, comando ou caminho de saída mudou. A única referência ao caminho antigo (`reviews/`) está em `V2_PREREGISTRO.md` (anotada) e no texto histórico da própria auditoria.

## Desvio do roteiro

`docs/ARQUITETURA.md` não foi criado: no Windows colide com o `docs/arquitetura.md` existente. Usou-se `ARQUITETURA_REORGANIZADA.md`.

## Validação

Ver [VALIDACAO_ANTES_DEPOIS](VALIDACAO_ANTES_DEPOIS.md).

## Problemas conhecidos e ações não realizadas

- Reexecução com dados reais (`final-run`, bateria, Fases v3) **bloqueada**: `data/raw/` não está no repositório; equivalência numérica foi verificada só nos hashes da v1, nos agregados versionados e em métricas sintéticas determinísticas.
- Não feitos (decisão do autor): renomear `v3`; agrupar `scripts/` por fase; remover `pyproject.toml.bak`; limitar `algoritmos/` e `v3/` a 5 arquivos por pasta; `configs/` por experimento; nota de aviso no `final-run --publish` (que sobrescreve a v1).
- Defeito científico: nenhum novo encontrado; nenhuma correção científica foi feita.
- Notebooks Databricks seguem sem validação em workspace.
(Nota de 28/10/2026, fase final: o teste passou para `tests/reproducibility/`.)
