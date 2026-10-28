# Validação final

Fonte: `reports/validation_current/baseline_antes_final.json` (antes das alterações desta fase) e `baseline_final.json` (depois), mais execuções diretas em 28/10/2026.

| Verificação | Antes | Depois | Resultado |
|---|---|---|---|
| Testes | 280 passed, 1 skipped | 283 passed, 1 skipped | Aprovado (+3 de regressão numérica) |
| Lint (Ruff, regras do `pyproject.toml`) | não configurado; 140 pendências sob as regras adotadas | 0 | Aprovado |
| Formatação (`ruff format --check .`) | 146 de 169 arquivos Python fora do formato | 218 arquivos formatados | Aprovado; AST (sem docstrings) idêntico à versão pré-formatação em 169/169 |
| Imports | 103 módulos, 0 falhas | 103 módulos, 0 falhas | Igual |
| Compilação | OK | OK | Igual |
| Experimentos sintéticos | dia 0, 2 cenários × 2 políticas; ex.: `alcancavel|proporcional` KM vazio 43,949411552 | idêntico em todas as chaves | Igual (igualdade exata, 9 casas) |
| Decisão F4 (set, proporcional, e\*=30) | NB −0,537742662, IC [−1,156924; 0,086219], inconclusivo | idêntica | Igual |
| Hashes científicos | 19/19 hashes da v1; digests de `reports/tcc_final`, `reports/tcc_v2`, `resultados`, `tabelas`, `config`, `databricks` | idênticos | Igual |
| Reexecução com dados reais | não executável (`data/raw/` ausente) | idem | **Bloqueado, não afirmado** |
| Documentação | links dos 13 documentos novos (testados) | links resolvem | Aprovado para links; conteúdo revisado manualmente, sem verificação automática |
| Segurança Git | `data/` e `reports/runs/` fora do índice; sem caminhos de usuário em código; sem segredos achados por busca de padrões | idem | Aprovado dentro do alcance da busca (não é varredura forense); `tcc-artigo-latex/` aninhado, não adicionado |
| Cobertura de testes | não medida | não medida | Não verificado |
| Tipagem estática | não configurada | não configurada | Não verificado |
| pre-commit | inexistente | arquivo criado, não executado | Não verificado |

Reproduzir: `python scripts/verificar_repositorio.py` e `python scripts/validar_baseline.py --out reports/validation_current/baseline_novo.json`.
