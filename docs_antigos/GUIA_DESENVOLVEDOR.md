# Guia do desenvolvedor

Para quem vai mexer no código. Complementa o [guia completo](GUIA_COMPLETO_REPOSITORIO.md) e o [mapa de versões](VERSOES_E_EXPERIMENTOS.md).

## Preparar o ambiente

```powershell
python -m pip install -e ".[test,algoritmos,extensao,qualidade]"   # Python 3.12
python -m pytest
python scripts/verificar_repositorio.py      # lint + formatação + compilação + pytest + hashes
```

`uv sync` também funciona (o `uv.lock` foi atualizado em 28/10/2026 para incluir as extras). Sem instalar o Ruff: `uvx ruff check .`. Extras: `v2` (h3, numpy, matplotlib, pyarrow, scikit-learn), `algoritmos` (+ scipy), `extensao` (+ statsmodels, arch), `qualidade` (ruff, pytest-cov).

## Onde está cada coisa

Ver a árvore no guia completo. Regra prática: **lógica científica** em `src/tcc_frota/<domínio>/`; **orquestração** em `cli.py`, `scripts/` e `*/final_run.py`; **configuração** em `config/*.yaml`; **resultados** em `reports/`, `resultados/`, `tabelas/` (gerados).

## Padrões de código

Python 3.12, Ruff (`pyproject.toml`): regras E, F, I, B, UP, SIM, C4, RUF, largura 140. Cada regra ignorada tem motivo no próprio `pyproject.toml`. Antes de commitar: `ruff check .` e `ruff format --check .`. Docstrings em português, unidades nos nomes (`*_km`, `*_s`). Não renomeie identificadores públicos nem símbolos que espelham o manuscrito. **Não aplique `--unsafe-fixes` em módulos científicos** e não misture formatação com mudança de comportamento (commits separados).

Sem tipagem estática automatizada (mypy/pyright não configurados): os contratos centrais (`Planner`, `PlanContext`, `Moves`) já têm anotações; adotar o verificador de tipos é pendência registrada.

## Testes

`tests/unit` (por domínio), `tests/integration` (ponta a ponta sintético, medalhão, Elasticsearch local), `tests/regression` (valores numéricos congelados), `tests/reproducibility` (hashes da v1, estrutura, ausência de dados reais e de respostas inventadas da empresa). Use Arrange–Act–Assert e entradas explícitas e determinísticas. Um teste de regressão numérica só muda com autorização científica explícita.

## Adicionar um algoritmo

1. `src/tcc_frota/algoritmos/<nome>.py`: classe que herda `Planner` (`algoritmos/base.py`) e devolve `Moves = {motorista: (lat, lng, km)}`, no máximo um destino por motorista, usando só `PlanContext` (nada de D+1).
2. Grade e parâmetros no protocolo **antes** de olhar resultados (`algoritmos/protocolo.py`, `docs_antigos/ORCAMENTO_CONFIGURACOES.md`).
3. Registro na bateria (`algoritmos/bateria.py`) e teste em `tests/unit/test_algoritmos_<nome>.py`.
4. Rodar sob o protocolo único; gerar saídas em pasta nova, nunca nas congeladas.

## Adicionar um experimento

Pré-registro commitado antes da execução (modelo: `docs_antigos/V2_PREREGISTRO.md`); script em `scripts/` com semente e saída explícitas; saídas agregadas em `reports/<nova_pasta>/`; individuais em `reports/runs/` (ignorado); teste e linha em `docs_antigos/VERSOES_E_EXPERIMENTOS.md`.

## Não toque nos artefatos congelados

`reports/tcc_final/`, `reports/tcc_v2/`, `resultados/`, `tabelas/`: não renomear, mover, regenerar no lugar ou editar. `tests/reproducibility/test_estrutura_repositorio.py` confere os 19 hashes da v1. `tcc-artigo-latex/` é um repositório Git independente: faça commits **dentro** dele, não no repositório principal.

## Mudança que pode alterar resultados

Registrar como defeito em `docs/DECISOES_TECNICAS.md`, obter autorização, isolar em commit próprio, rodar de novo `scripts/validar_baseline.py` antes e depois, e documentar a diferença. Dados reais e credenciais nunca vão para o Git.
