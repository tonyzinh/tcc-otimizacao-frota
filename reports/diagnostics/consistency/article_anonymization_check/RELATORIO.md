# Rodada 9: retirada dos identificadores da empresa (09/11/2026)

Só o artigo e o PDF mudaram. Nenhum número, tabela de resultados ou conclusão mudou. Nada foi commitado nem adicionado ao stage. Fora do artigo, só foram gravados este relatório, os arquivos de conferência desta pasta e as entradas de registro (R-33 e a seção 15 da conformidade).

## 1. Busca antes de editar

**Onde se buscou:** todos os `.tex`, `.bib`, `.cls`, `.sty` e `.bst` de `article/` (fora de `build/`); o texto e os metadados dos PDFs de `article/figures/`; e o texto e os metadados do PDF compilado.

**Termos, sem diferenciar maiúsculas:** "V1", "Viagens", "Prime" (palavra inteira), "região 1" e os códigos de serviço "1, 11, 12 e 19".

**Lista completa:** `ocorrencias_antes.csv`, com origem, linha ou página, termo e trecho.

| Origem | Local | Termo | Trecho |
|---|---|---|---|
| `appendices/apendices.tex` | linha 355 | V1, região 1, serviços, Prime | "Recorte dos dados reais: produto V1, região 1 (Grande Vitória), serviços 1, 11, 12 e 19, excluídos os serviços Prime." |
| PDF compilado | p. 36 (Apêndice D) | os mesmos | o mesmo trecho |
| `appendices/apendices.tex` | linha 32 | Viagens | "Duração das viagens: a duração de cada corrida…" |
| `sections/02-fundamentacao.tex` | linha 68 | Viagens | "A atribuição entre veículos e viagens também foi formulada…" |
| `sections/04-resultados-discussao.tex` | linha 83 | Viagens | "a duração das viagens é entrada observada" |
| PDF compilado | p. 7, 15, 25 | Viagens | os três trechos acima |
| PDF compilado | p. 5 e 6 | V1 | veículos V1, V2 e V3 do exemplo hipotético da Tabela 2 (no fonte, notação matemática $V_1$) |
| `figures/mapa_recorte_h3.png` | — | imagem raster | sem texto extraível; não é usada no PDF (o artigo inclui `mapa_recorte_h3.pdf`, sem ocorrências) |

**Metadados do PDF:**
- título: o novo;
- autor: os dois autores;
- assunto: "Ciência da Computação – FAESA";
- palavras-chave: as do resumo;
- criador e produtor: "LaTeX with hyperref" e "MiKTeX-dvipdfmx".

Nenhum deles tinha ocorrência.

**Outras buscas sem ocorrência no artigo:**
- `v1_viagens` e caminhos de `data/extraido`;
- `.bib`, legendas e textos das figuras em PDF.

## 2. O que foi substituído

**Apêndice D, recorte.** O trecho foi trocado pelo texto pedido, com uma alteração: "Recorte dos dados reais: um produto de transporte por aplicativo, na região da Grande Vitória, restrito a quatro tipos de serviço e sem os serviços de categoria superior. Cenário de disponibilidade: J (jornada realizada). Os códigos internos do sistema de origem constam **do código de extração** do repositório e não são reproduzidos aqui."

**Divergência com o pedido:** o texto pedido dizia "arquivos de configuração". Os códigos não estão em `configs/`. Eles estão em `src/tcc_frota/data/extraction/filtro.py` (`REGIAO_GRANDE_VITORIA`, `SERVICOS_V1`), em `entidades.py` e na documentação de dados. Para a frase ser verdadeira, trocou-se por "código de extração".

**Metodologia (3.3).** "(códigos e exclusões no Apêndice D)" passou a "a quatro tipos de serviço, sem os serviços de categoria superior (Apêndice D)". O Apêndice D não traz mais os códigos, e a exclusão dos serviços de categoria superior, retirada do corpo na rodada 8, volta descrita de forma genérica.

**Descrição da operação.** Desde a rodada 8, o corpo já usava sempre "uma empresa de transporte por aplicativo que opera na Grande Vitória (ES)". Não sobrou outra forma de nomear a operação.

**Caminhos e identificadores.** Nenhum caminho, arquivo ou coluna citado no artigo contém "v1" ou o nome da empresa. Os caminhos de código e de resultados do Apêndice D foram mantidos. Nada foi renomeado no repositório.

## 3. O que ficou de propósito

| Ocorrência | Motivo |
|---|---|
| "viagens" (3 vezes no fonte, 3 no PDF) | Palavra comum do português, em minúscula, no sentido de corridas. Não é o nome do produto nem identifica a empresa. |
| "V1", "V2", "V3" no exemplo da Tabela 2 (p. 5–6) | São os veículos 1, 2 e 3 de um exemplo com valores hipotéticos ($V_1$ no fonte). Não têm relação com o código do produto. Trocar a notação mudaria o exemplo e a fundamentação sem ganho de anonimato. Se preferirem zero ocorrências literais, basta renomear para outra letra. |
| "SQL Server" e "Elasticsearch" (Apêndice A) | Nomes de tecnologias genéricas, não da empresa. |
| `mapa_recorte_h3.png` em `article/figures/` | Arquivo do repositório, não incluído no PDF. Não foi alterado. |

## 4. Verificação

**Busca no PDF final e nos metadados** (`ocorrencias_depois.csv`):
- nenhuma ocorrência de "Prime", "região 1", dos códigos de serviço ou de "V1" como código de produto;
- restam só os itens da seção 3;
- nos metadados, nenhuma ocorrência.

**Resultados congelados** (`hashes_congelados.csv`):
- `reports/tcc_final`: 19 de 19 iguais ao pré-registro;
- arquivos rastreados: 138 de 138 iguais a HEAD;
- os 197 hashes são idênticos aos da rodada 8.

**Números** (`numeros_antes_depois.csv`): 876 valores distintos antes e depois, todos em comum. Os códigos 1, 11, 12 e 19 saíram do Apêndice D, mas não eram resultados, e esses valores aparecem em outros pontos do texto.

**Compilação:**
- 0 citações ou referências indefinidas;
- 0 caixas estouradas;
- 37 páginas; corpo da p. 2 ao fim das referências na p. 23 (22 páginas);
- apêndices A–D nas p. 24, 29, 35 e 36, em sequência;
- PDF copiado para `article/ARTIGO_ATRIBUICAO_HUNGARO.pdf`.

**Testes:** `pytest` deu 203 testes, 0 falhas, 0 erros e 0 pulados, em 8,4 s (`pytest_junit.xml`).

**Lint:** `ruff check .` sem erros; `ruff format --check .` com 127 arquivos formatados.

**Repositório:** `git status` de `src`, `tests`, `configs` e `scripts` mostra só alterações anteriores a esta rodada; nada foi tocado aqui.
