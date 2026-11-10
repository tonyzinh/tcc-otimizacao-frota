# Rodada 10: guloso global × atribuição conjunta e legibilidade das tabelas

Data: 09/11/2026. Natureza: revisão de texto e de apresentação do artigo. **Nenhuma simulação nova e nenhum número novo.** As análises citadas são as já existentes (todas posteriores aos resultados congelados, exceto as linhas congeladas indicadas).

PDF de referência (antes): SHA-256 `433B952576DEDC86B6DB9D2C3F469E747FB2D486F6F70C83AA48F435497EA5F0`, 37 páginas. Páginas abaixo são as desse PDF.

## 1. Ocorrências encontradas antes de alterar

Busca no PDF e nos `.tex` por "guloso", "greedy", "não se confirmou", "not confirmed" e "Húngaro sobre".

| # | Seção | Página | Arquivo:linha | Trecho |
|---|---|---|---|---|
| 1 | Resumo | 1 | `sections/00_abstract.tex:2` | "Um guloso global simples, que escolhe primeiro o par mais curto, teve menos km que o Húngaro; com a calibração refeita, atendeu quase o mesmo em setembro e outubro (até 0,4% a menos) e mais no teste, e a vantagem do Húngaro sobre ele não se confirmou." |
| 2 | Abstract | 2 | `sections/00_abstract.tex:6` | "A simple global greedy rule ... drove fewer kilometers than the Hungarian algorithm; ... so the Hungarian algorithm's advantage over it was not confirmed." |
| 3 | 4.3, parágrafo "Guloso global e janela" | 17 | `sections/04_results_discussion.tex:89` | "Com os parâmetros de março, o guloso teve menos km ... mas atendeu bem menos (179 e 83 pedidos a menos) ... A vantagem do Húngaro sobre um guloso global simples, portanto, não se confirmou." |
| 4 | 4.3, Tabela 8 (tab:bcd), título | 17 | `sections/04_results_discussion.tex:91` | "Lote simples, atribuição conjunta e guloso global lado a lado" |
| 5 | 4.3, Tabela 8, fonte | 17 | `sections/04_results_discussion.tex:118` | "D: guloso global, definido depois dos resultados congelados ..." |
| 6 | 4.5 Discussão, "Mecanismo" | 19 | `sections/04_results_discussion.tex:147` | "O guloso global mostra o outro lado. Com os parâmetros de março, ele reduziu mais o km e atendeu bem menos ... A vantagem do Húngaro sobre um guloso global simples não se confirmou." |
| 7 | 5 Conclusão, "O que não foi confirmado" | 20–21 | `sections/05_conclusion.tex:5` | "Um guloso global simples, definido depois, teve menos km ... A vantagem do Húngaro sobre esse guloso não se confirmou." |
| 8 | Apêndice B, Tabela 16 (tab:r5), fonte | 33 | `appendices/appendices.tex:238` | "D: guloso global." (colunas D×C) |
| 9 | Apêndice D | 36–37 | `appendices/appendices.tex:355` | identificador `B_lote60s_guloso_fifo` (nome gravado da política B; não é o guloso global), `global_greedy`, pasta e script `global_greedy_comparison` |

Sem ocorrência: Introdução (seção 1), Seção 2, Seção 3, 4.1, 4.2, 4.4, 4.6, Apêndices A e C. A Introdução e a contribuição não prometem superioridade do Húngaro sobre um guloso; a Seção 2 diz que o Húngaro é ótimo "para o lote" e que isso não garante o ótimo do dia.

## 2. O que foi reescrito (guloso global × atribuição conjunta)

| # | Onde | Antes | Depois |
|---|---|---|---|
| 1 | Resumo | "… e a vantagem do Húngaro sobre ele não se confirmou." | Uma frase simétrica. O guloso teve menos km em todos os períodos. O Húngaro atendeu mais com março; a diferença foi pequena com a calibração refeita (até 0,4%) e se inverteu no teste. "Nenhuma das duas regras mostrou vantagem clara." |
| 2 | Abstract | "… so the Hungarian algorithm's advantage over it was not confirmed." | Versão em inglês da mesma frase ("neither rule showed a clear advantage"). |
| 3 | 4.3 "Guloso global" | Narrativa com veredito ("não se confirmou"). | Mesmos números, sem veredito. Rótulo explícito "posterior e não confirmatória". Inclui o intervalo t pareado do teste (−23,2 a +12,2 km/dia). Fecha com "Nenhuma das duas regras mostrou vantagem clara", dizendo em quê cada uma foi melhor. O parágrafo da grade de janelas virou "Janela", separado. |
| 4–5 | Tabela 8 (tab:bcd) | B, C e D lado a lado, 8 colunas, título "lado a lado". | Título "Guloso global (D) contra atribuição conjunta (C): km vazio e atendidos por período e calibração", 6 colunas. Mostra a diferença D−C em km (%) e em atendidos, com sinal declarado e negrito no menor km de cada linha. Origem: congelada ou † posterior. Os absolutos com espera foram para a nova Tabela 18 (tab:bcdabs, Apêndice B). |
| 6 | 4.5 "Mecanismo" | "A vantagem do Húngaro sobre um guloso global simples não se confirmou." | O mecanismo, rotulado "leitura coerente com os dados, não testada": ótimo por lote, não por dia; o máximo de atendidos vem primeiro; aproximações mais longas para atender um a mais afastam veículos do lote seguinte; o guloso deixa pedidos, mas mantém veículos perto da demanda; os efeitos quase se compensam. Diz também que a distância dos pares extras não foi medida. |
| 7 | Conclusão | "A vantagem do Húngaro sobre esse guloso não se confirmou." | Diz em quê: km (D menor em todos) e atendimento (−179/−83, −41/−25, +29). "Nenhuma das duas regras mostrou vantagem clara." |
| 8 | Tabela 16 (tab:r5), fonte | "D: guloso global." | Grupos com nomes por extenso ("Guloso global − atribuição conjunta") e sinal explicado. |
| 9 | Apêndice D | Parágrafo | Tabela 22 (tab:rastreio). Os identificadores gravados foram mantidos. |
| novo | 4.6 | — | Item "Que o Húngaro seja melhor que um guloso global simples, nem o contrário." |
| novo | Tabela 3 (tab:politicas) | Sem D | Linha do guloso global, com † "definido depois dos resultados congelados". |

**Mantido sem alteração:** Introdução e contribuição, que não prometem superioridade sobre nenhum guloso. Seção 2, que já diz que o ótimo é "para aquele lote". Título. A coerência foi conferida entre título, resumo, 4.3, 4.5, 4.6 e conclusão: todos dizem "sem vencedor claro". Busca no PDF final: 0 ocorrências de "não se confirmou" ou "not confirmed".

**Análise opcional dos pares "extras" (passo 5): não feita, fica como hipótese.** Os resultados da rodada 7 guardam só agregados por dia e por política (`bcd_por_dia.csv`, `bcd_resumo.csv`), sem a saída por pedido. Medir a aproximação dos pares que só C forma exigiria simulação nova com dados reais, que não foi autorizada nesta rodada. O artigo (4.5) diz isso.

## 3. Legibilidade (tabelas, figuras, apêndices)

- **Nomes:** "despacho imediato", "lote simples", "atribuição conjunta" e "guloso global", nessa ordem, em células, cabeçalhos e legendas de figura. As letras A–D só aparecem entre parênteses nos títulos. A Tabela 3 perdeu a coluna "Letra".
- **Títulos:** descritivos e neutros. A Tabela 5 (resumo principal) ganhou a linha "Leitura:".
- **Diferenças:** cada fonte declara a referência ("primeira política menos a segunda", "atribuição conjunta menos a referência") e o sinal ("negativo = menos km"). O negrito marca o melhor valor da coluna, dito na fonte. Na Tabela 5, o negrito marca também "não cumprido", também dito na fonte. Na Tabela 14, o negrito continua marcando intervalos que incluem zero, como já declarado.
- **Formatação:** unidades nos cabeçalhos (km, %, s, km/dia, n, h); vírgula decimal e ponto de milhar já eram usados; decimais por coluna já eram uniformes. A ordem das linhas é sempre imediato, lote simples, conjunta, guloso.
- **Origem e calibração:** "março (congelada)" e "janeiro a agosto (nova)" nas Tabelas 5, 8 e 18; † para simulação posterior, explicado na fonte.
- **Largura:** tabelas do corpo com no máximo 7 colunas. A Tabela 7 agrupa por período; a 8 foi dividida (absolutos no apêndice).
- **Tabelas diárias:** a Tabela 11 (tab:diario) foi mantida e agrupada por semana (segunda a domingo, com dia da semana), em uma coluna por período em vez de duas lado a lado. A Tabela 17 (mensal) foi mantida: tem 7 linhas e a Figura 4 já mostra os dias.
- **Figuras 3 e 4:** refeitas a partir dos mesmos arquivos (`frozen_evaluation/analise/resumo.json`; CSV por dia da rodada 5). Cada comparação tem tom de cinza e hachura próprios na 3; círculos cheios e triângulos vazados, barras cheias e vazadas na 4. Eixos com unidade e legendas por painel. Conferidas renderizadas em tons de cinza. A Figura 2 (mapa) não foi alterada: a escala é sequencial e legível em cinza.
- **Seção 4.1:** frase-guia sobre o sinal, "critério de atendimento cumprido" e "inclui zero".
- **Apêndices:**
  - cada um abre com "O que contém" e "Quando consultar";
  - do Apêndice A saiu a frase sobre o intervalo de setembro ser mais estreito que o t pareado, que repetia o Apêndice B (lá mantida);
  - o Apêndice D virou a Tabela 22, com as colunas Item | Onde está | Gerado por | Aparece no artigo em, em sete linhas;
  - os caminhos estão em Consolas, quebram depois de / e _, e não levam os sinais < > do estilo ABNT de URL;
  - os números de tabela e figura da Tabela 22 foram conferidos no PDF.
- **Impressão:** fonte das tabelas em 10 pt (≥ 9 pt), 0 *overfull* (nada passa da margem), páginas de resultados e apêndices renderizadas em tons de cinza e vistas.

## 4. Verificação

| Verificação | Resultado |
|---|---|
| Valores no PDF, antes × depois (`valores_antes_depois.csv`, 961 valores distintos) | 0 valores saíram. Novos: `−23,2` e `12,2` (intervalo D−C do teste, `teste_resumo.csv`: −23,196 e +12,210); `−179` e `−83` (sinal das diferenças já citadas como "179 e 83 a menos"; `bcd_resumo.csv`). 41 valores mudaram de contagem: duplicação entre as Tabelas 8 e 18, números de tabela e página, e "−2,66"/"−1,88", que passaram do texto para a tabela. |
| D×C recalculado de `bcd_resumo.csv` | km −2,66 / −1,88 / −1,23 / −2,04 / −0,62%; atendidos −179 / −83 / −41 / −25 / +29; −41/11.126 = 0,37% e −25/14.532 = 0,17% ("até 0,4%") |
| `scripts/compute_article_derived_values.py --check` | 21/21 conferem (valores listados na saída do script e em `reports/diagnostics/consistency/article_derived_values/derived_values.csv`) |
| `scripts/verify_frozen_results.py` | git_3e65f3b 138/138; Parquet 40/40; pré-registro 19/19; falhas 0 |
| `scripts/sync_article_figures.py --check` | 3 figuras, 0 problemas |
| `pytest` | 208 aprovados, 0 falhas, 0 pulados |
| `ruff check` e `ruff format --check` | limpos |
| Compilação | XeLaTeX → BibTeX → XeLaTeX ×2: 0 erros, 0 *overfull*, 0 citação ou referência indefinida. 8 *underfull* (7 antigos + 1 no parágrafo do Apêndice D com caminhos) |
| Páginas | 40. Corpo e referências em 1–24 (antes 1–23), dentro do limite de 25. Apêndices A (25), B (30), C (38), D (39). Tabelas 1–22 e Figuras 1–4 em sequência |

PDF depois: `article/ARTIGO_ATRIBUICAO_HUNGARO.pdf`, SHA-256 `734DC5F85F74C3E0C6C969AC8552BAE894AD72A081ED3EFCA4C8E9A81EC9AED7`.

Depois desta rodada, a pedido dos autores, o PDF final passou a se chamar `article/TCC 2026-2 - Entony Jovino - Raphael Simões - Orientador Rober Marcone Rosi.pdf` (gerado por `scripts/build_article.py`). O vínculo do orientador também mudou para "Professor e orientador do Centro Universitário Espírito-Santense (FAESA)". O texto e os números do artigo não mudaram, por isso o SHA-256 acima não vale para o PDF renomeado.

## 5. Limitações e pendências

- A afirmação "os efeitos quase se compensam" é leitura dos totais, não medição do mecanismo.
- O rótulo de R-30 em `.claude/rules/fleet_assignment.md` ("a vantagem de C sobre D também não [se confirmou]") continua com o mesmo sentido. Os autores podem alinhá-lo à leitura de troca (R-37).
- Nada foi commitado nem adicionado ao stage.
