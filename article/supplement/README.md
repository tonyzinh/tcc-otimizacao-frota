# Material suplementar

O PDF `material_suplementar.pdf` entrega os quatro apêndices completos: séries diárias, intervalos, cenários sintéticos, validação operacional, recalibração e rastreabilidade. É compilado de `main.tex`, que inclui `appendices_full.tex` e remete às equações, tabelas e figuras do artigo principal. O texto suplementar foi alinhado à terminologia e às limitações do artigo; os números não foram alterados. Os resultados agregados de origem permanecem em `reports/`.

O arquivo `pdf_recebido_40_paginas.pdf` preserva o PDF de entrada (40 páginas) antes da revisão. Ele é apenas registro da versão recebida. Os achados centrais e os limites da avaliação permanecem no PDF principal.

Para recompilar o suplemento, no diretório `article/supplement/`, execute XeLaTeX em `main.tex`, BibTeX em `build/main` e mais duas passagens de XeLaTeX; copie `build/main.pdf` para `material_suplementar.pdf`. O suplemento lê `../build/main.aux` para as remissões ao artigo, portanto compile o artigo primeiro.
