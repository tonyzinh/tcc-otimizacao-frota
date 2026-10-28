# Relatório final de organização (28/10/2026)

Base: ramo `v2-extensoes`, commit `abf4c5c`. Nada foi commitado, empurrado ou colocado em stage por esta fase (as renomeações `git mv` já ficam em stage por natureza). Complementa [a reorganização anterior](../repository_migration/RELATORIO_REORGANIZACAO.md).

## Problemas de partida

Sem Ruff nem configuração de estilo (146 de 169 arquivos Python fora do formato); 46 blocos de importação desordenados, 19 importações não usadas, 4 variáveis mortas; dependências diretas (SciPy, statsmodels, arch) sem declaração no `pyproject.toml`, vindas só do ambiente; testes só em `unit/` e `integration/`; `.gitignore` sem caches de ferramentas; nenhum guia de versões; `README.md` desatualizado; nenhum portão de qualidade único.

## Ações

| Ação | Detalhe |
|---|---|
| Linha de base | `baseline_antes_final.json` (280 passed, 1 skipped) e `baseline_final.json` |
| Lint | Ruff 0.17.3 via `uvx`; regras E, F, I, B, UP, SIM, C4, RUF; ignoradas com motivo no `pyproject.toml` (notação Unicode, `zip(strict)`, fechamentos em laço, etc.). Autofix seguro (sem `--unsafe-fixes`): imports, `datetime.UTC`, `typing` obsoleto, aspas em anotações, `dict.fromkeys`, `noqa` inútil |
| Variáveis mortas | 4 renomeadas para `_nome` ou removidas (`im`, `zone_of`, `pick_speed_reta`, `pn_`), sem efeito colateral |
| Formatação | `ruff format` (largura 140) em `src`, `scripts`, `tests`, `app`; AST sem docstrings idêntico antes/depois nos 169 arquivos |
| Dependências | extras `algoritmos`, `extensao`, `qualidade` no `pyproject.toml`; `uv.lock` atualizado (somente adições: +386/−1 linhas) |
| Testes | `tests/regression/test_metricas_congeladas.py` (3 testes novos); `test_estrutura_repositorio.py` e o teste de guarda contra respostas inventadas da empresa movidos para `tests/reproducibility/` |
| Qualidade | `scripts/verificar_repositorio.py`, `.pre-commit-config.yaml` (não executado), `.gitignore` ampliado |
| Documentação | `README.md` reescrito; novos `VERSOES_E_EXPERIMENTOS`, `GUIA_DESENVOLVEDOR`, `GUIA_EXPERIMENTOS`, `ESTADO_FINAL_REPOSITORIO`; referências de caminho de teste corrigidas |

## Contagem

Modificados (rastreados): 151 (146 `.py`, mais `pyproject.toml`, `uv.lock`, `README.md`, `.gitignore`, `docs/V2_PREREGISTRO.md`). Movidos: 3 (`git mv`) + 1 teste estrutural não rastreado. Novos (não rastreados): 18 caminhos, entre eles os documentos desta fase, `tests/regression/`, `scripts/verificar_repositorio.py`, `.pre-commit-config.yaml`, `reports/final_release/` e `reports/validation_current/`. Removidos: 0.

## Compatibilidade

Nenhum módulo, comando, ponto de entrada ou caminho de saída mudou. Importações não usadas removidas foram checadas por importação de todos os módulos e pela suíte inteira. Scripts em `scripts/` ficaram onde estão: são citados pelo pré-registro e pelos documentos; um reagrupamento exigiria atualizar essas citações e não traria ganho científico.

## Integridade científica

Ver [VALIDACAO_FINAL](VALIDACAO_FINAL.md). Resumo: 19/19 hashes da v1; digests dos diretórios protegidos idênticos; métricas sintéticas e decisão F4 idênticas. **Não** reexecutei dados reais.

## Itens para decisão do proprietário

1. `pyproject.toml.bak`: versão antiga do `pyproject.toml` (sem a extra `v2`, `requires-python >=3.12`), rastreada, sem referências em código ou scripts (só citada nos relatórios de reorganização); histórico preservado no Git. **Proposta de remoção** (`git rm`), não executada.
2. `tcc-artigo-latex/`: repositório Git independente (remoto `tonyzinh/tcc-artigo-latex`, ramo `main`, árvore limpa), não é submódulo. Um `git add tcc-artigo-latex` aqui criaria um gitlink acidental. Opções: manter como está e evitar o `add`; ignorar no `.gitignore`; ou formalizar como submódulo. Não decidi.
3. Revisar o diff de `uv.lock` (extras antes não travadas).
4. `docs/TCC_CAP3_TRABALHOS_RELACIONADOS.md` e `docs/TCC_REFERENCIAS_ANOTADAS.md`: rascunhos novos não rastreados; commitar só se forem desejados.
5. Terminologia “dinâmico” no Cap. 3 (ver classificação PRV).

## Limitações

Cobertura, mypy, pre-commit e reexecução com dados reais não verificados (ver `docs/ESTADO_FINAL_REPOSITORIO.md`).
