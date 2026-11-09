# Artigo: atribuição conjunta (algoritmo Húngaro) em lotes de 60 s

Fonte LaTeX (XeLaTeX + BibTeX). Estrutura: `main.tex`, `sections/`, `appendices/`, `references/referencias.bib`, `figures/`, `config/` (formatação central, incluindo o espaçamento do corpo `\espacamentocorpo`), `build/` (saída, ignorada pelo git).

## Compilar

```bash
cd article
BIBINPUTS=".;.." latexmk -g -interaction=nonstopmode main.tex   # gera build/main.pdf
```

`latexmkrc` já define `build/` como saída e o motor XeLaTeX. Requer MiKTeX (ou TeX Live) com Arial disponível.

## Figuras

Geradas a partir dos resultados congelados, sem nova simulação:

```bash
tcc-frota figures                      # km/atendimento, ICs, sintético
python -c "from pathlib import Path; from tcc_frota.visualization.maps import plot_study_cut; plot_study_cut(Path('article/figures'), footer=False)"
```

O PDF final é copiado para `ARTIGO_ATRIBUICAO_HUNGARO.pdf`. Estado de conformidade e pendências: `RELATORIO_CONFORMIDADE.md`.
