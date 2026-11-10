# Artigo: atribuição conjunta (algoritmo Húngaro) em lotes de 60 s

Fonte LaTeX (XeLaTeX + BibTeX). Estrutura:

- `main.tex`;
- `sections/` (`00_abstract` a `05_conclusion`);
- `appendices/appendices.tex`;
- `references/references.bib`;
- `figures/` (cópias geradas; ver abaixo);
- `config/`: formatação central, incluindo o espaçamento do corpo `\espacamentocorpo`;
- `build/`: saída, ignorada pelo Git.
- `supplement/main.tex` e `supplement/material_suplementar.pdf`: apêndices detalhados compilados separadamente após o artigo principal.

## Compilar

```bash
cd article
BIBINPUTS=".;.." latexmk -g -interaction=nonstopmode main.tex   # gera build/main.pdf
```

`latexmkrc` já define `build/` como saída e o XeLaTeX como motor. É preciso o MiKTeX (ou o TeX Live) com a fonte Arial disponível.

Sem latexmk, a sequência manual é:

```bash
xelatex -output-directory=build main.tex
bibtex build/main
xelatex -output-directory=build main.tex
xelatex -output-directory=build main.tex
```

O PDF final de entrega tem sempre o nome `TCC 2026-2 - Entony Jovino - Raphael Simões - Orientador Rober Marcone Rosi.pdf`, em `article/`. O modo recomendado compila e copia de uma vez, e só copia se não houver erro nem referência ou citação indefinida:

```bash
python scripts/build_article.py
```

Depois do latexmk ou da sequência manual, copie `build/main.pdf` para esse nome.

## Figuras

A origem oficial é `reports/figures/`. As figuras são geradas a partir dos resultados congelados e das análises posteriores, sem simulação nova.

| Figura | Gerador | Origem oficial |
|---|---|---|
| Diferenças de km vazio e atendimento | `tcc-frota figures` (`visualization.figures.plot_km_and_attendance`) | `reports/figures/empty_km_service_differences.pdf` |
| Mapa do recorte, sem rodapé | `visualization.maps.plot_study_cut(Path('reports/figures'), name='study_area_h3_map_no_footer', footer=False)` | `reports/figures/study_area_h3_map_no_footer.pdf` |
| Diferenças diárias da recalibração | `python scripts/plot_recalibration_daily_differences.py` | `reports/figures/recalibration_daily_differences.pdf` |

`article/figures/` contém só as cópias das figuras que o LaTeX inclui. Os comandos são:

- `python scripts/sync_article_figures.py`: copia as figuras da origem;
- `python scripts/sync_article_figures.py --check`: confere as cópias pelo SHA-256. Esse modo também roda em `tests/reproducibility/test_article_figures.py`.

## Relatórios editoriais

- `compliance_report.md`: conformidade com as normas e pendências.
- `reference_audit.md`: tabela obra × afirmação × evidência.
- `review_response.md`: resposta ao parecer.
