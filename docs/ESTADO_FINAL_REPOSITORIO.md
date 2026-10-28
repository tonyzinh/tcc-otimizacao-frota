# Estado final do repositório (28/10/2026)

Retrato verificado ao fim da padronização. Base: ramo `v2-extensoes`, commit `abf4c5c`, **com alterações locais ainda não commitadas** (nada foi commitado, empurrado ou colocado em stage, exceto três renomeações feitas com `git mv`).

## Arquitetura final

Estrutura de domínio preservada (nenhum pacote renomeado): ver [guia completo](GUIA_COMPLETO_REPOSITORIO.md) e [arquitetura](ARQUITETURA_REORGANIZADA.md). Mudanças desta fase: `reviews/` → `reports/thesis_audit/`; testes agora em `tests/{unit,integration,regression,reproducibility}`; novos `scripts/verificar_repositorio.py`, `.pre-commit-config.yaml`, configuração Ruff no `pyproject.toml`.

## Versão científica atual

Resultados congelados: v1 (`reports/tcc_final`, tag `v1-congelada`) e bateria/seletivo (`resultados/`, `tabelas/`). Atual: extensão v2 (pacote `v3`), Fases 1–4, `reports/tcc_v2/`. Mapa e histórico: [VERSOES_E_EXPERIMENTOS](VERSOES_E_EXPERIMENTOS.md).

## Comandos principais

`python -m pytest` · `python scripts/verificar_repositorio.py` · `python scripts/validar_baseline.py --out <json>` · `ruff check .` · `ruff format --check .`. Experimentos: [GUIA_EXPERIMENTOS](GUIA_EXPERIMENTOS.md).

## Resultados de verificação (28/10/2026)

| Item | Resultado |
|---|---|
| pytest | 283 passed, 1 skipped (antes: 280 passed, 1 skipped; +3 testes de regressão numérica) |
| Ruff lint (`ruff check .`, regras em `pyproject.toml`) | 0 pendências (antes: 614 achados com todas as regras candidatas; 140 após ignorar, com justificativa, as regras que mexeriam em semântica numérica ou na notação; os 140 foram corrigidos por autofix seguro ou à mão) |
| Ruff format | 218 arquivos formatados; árvore sintática (sem docstrings) idêntica antes/depois da formatação nos 169 arquivos Python de `src`, `scripts`, `tests` e `app` |
| Compilação e importação | `compileall` OK; 103 módulos importados, 0 falhas |
| Hashes da v1 | 19/19 conferem com `docs/V2_PREREGISTRO.md` |
| Artefatos protegidos | digests de `reports/tcc_final`, `reports/tcc_v2`, `resultados`, `tabelas`, `config`, `databricks` idênticos antes/depois; `git diff HEAD` nesses caminhos vazio |
| Métricas sintéticas determinísticas (dia 0, 2 cenários × 2 políticas) e decisão F4 (NB = −0,5377, “inconclusivo”) | idênticas |

## Não verificado

Cobertura de testes (pytest-cov foi só declarado; não medido); verificação de tipos (mypy/pyright não configurados); `pre-commit` (configuração escrita, não executada); reexecução com dados reais (`final-run`, bateria, Fases v3); notebooks Databricks em workspace; Linux/macOS; compilação do artigo LaTeX.

## Limitações e pendências (por severidade)

| Severidade | Pendência |
|---|---|
| Alta (reprodutibilidade) | Resultados reais só reproduzíveis com `data/raw/`, ausente do repositório; `final-run --publish reports/tcc_final` sobrescreveria a v1 congelada |
| Média | Nomes `v2`/`v3` ambíguos (documentados, não renomeados); `uv.lock` ganhou extras antes ausentes (revisar o diff); `tcc-artigo-latex/` é repositório aninhado (decidir entre ignorar, submódulo ou manter independente); carimbo do pré-registro só no Git local |
| Baixa | `pyproject.toml.bak` (sem referências; ver relatório final) ; pastas `algoritmos/` e `v3/` acima de 5 arquivos; B905/B023 e outras regras ignoradas por segurança numérica; 15 linhas > 140 colunas; mypy ausente |

## Protegido

`reports/tcc_final/`, `reports/tcc_v2/`, `resultados/`, `tabelas/`: intactos. Origem do problema: o TCC estuda **reposicionamento preventivo D+1, não PRV** ([classificação](../reports/validation_current/16_CLASSIFICACAO_PRV_VRP.md)).
