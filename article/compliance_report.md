# Relatório de conformidade do artigo e do repositório

Data: 09/11/2026 (rodada 3). Revisão feita por modelo de IA (Claude) sobre os arquivos do projeto. **Não é leitura humana independente de orientador ou banca.**

Entregas: `article/ARTIGO_ATRIBUICAO_HUNGARO.pdf` (fonte: `article/`, compilação em `article/README.md`), `article/reference_audit.md` (tabela obra × afirmação × evidência), este relatório.

## 0. Atualização da rodada 4 (09/11/2026, auditoria do parecer crítico)

Esta seção prevalece sobre os números das seções seguintes, que descrevem a rodada 3.

| Item | Resultado |
|---|---|
| Páginas | **29** no total; referências nas páginas 24–25 (terminam na **25**, dentro do limite de 25); Apêndices A, B e C nas páginas 26–29 |
| Compilação | XeLaTeX + BibTeX (`latexmk`): sem erro, sem citação ou referência indefinida, 0 *overfull hbox*; 24 chaves citadas = 24 entradas |
| Revisão visual | As 29 páginas renderizadas e vistas depois da última compilação |
| Testes | **202 aprovados**, 0 falhas (196 anteriores + 3 do guloso global + 3 de liberação do veículo e de par inelegível) |
| Lint | `ruff check` e `ruff format --check` sem erros |
| Experimento congelado | Inalterado. A reexecução posterior reproduziu os 120 resultados (dia × política) com diferença máxima de 0,0 km |
| Análises posteriores | `scripts/analyze_robustness_review.py` (subcomandos `base`, `sens`, `disp`, `contagens`, `janelas`, `componentes`, `simulado_a`, `viario`, `sintetico`); plano escrito antes em `reports/diagnostics/statistics/robustness_review/PLANO.md`; saídas agregadas e `RELATORIO.md` na mesma pasta. Dados reais processados localmente com autorização do proprietário restrita a esta rodada |
| Matriz do parecer | `article/review_response.md` |
| Código novo | `global_greedy` em `POST_HOC_POLICIES` (`src/tcc_frota/assignment/dispatch.py`), fora de `POLICIES`; não altera o experimento congelado |
| Pendência | Declaração do vínculo dos autores com a operação (marcada como pendente no artigo) |

## 1. Resumo

| Item | Resultado |
|---|---|
| Páginas | **25** no total; referências nas páginas 22–23 (terminam na **23**); Apêndices A e B nas páginas 23–25 |
| Compilação | XeLaTeX + BibTeX (`latexmk`): sem erro, sem citação ou referência indefinida, 0 *overfull hbox*, 0 avisos do BibTeX |
| Revisão visual | 25 páginas renderizadas e vistas; após as últimas edições, as páginas cujo texto mudou (12, 13, 23, 24, 25) foram vistas de novo e as demais têm texto idêntico ao inspecionado |
| Testes | 196 aprovados, 0 falhas, 0 pulados (ambiente do projeto, com dados locais) |
| Lint | `ruff check .` e `ruff format --check .` sem erros (171 arquivos) |
| Instalação limpa | Validada em cópia separada, com o lock preservado (ver §4) |
| Notebooks | 5 de 5 executados de ponta a ponta em kernel limpo, no ambiente do projeto e no ambiente limpo |
| Bloqueio material para enviar ao orientador | **Nenhum encontrado.** Pendências externas listadas no §9 |

## 2. Versão final

| Pendência | Verificado | Evidência | Situação | Consequência |
|---|---|---|---|---|
| PDF anexado × PDF do projeto | O arquivo anexado **não está acessível no disco** (nenhum `ARTIGO_ATRIBUICAO_HUNGARO.pdf` além das cópias do projeto) | Cópias encontradas: `article/` (versão final, SHA-256 `a0909adc…ac39`, 260 KB); versão do início desta rodada (SHA-256 `2defaa5f…a669`, 259.866 bytes, guardada em `..\tcc-otimizacao-frota_preservacao_2026-11-09\rodada3_antes\`); cópia antiga em `tcc-artigo-latex/atribuicao/` (SHA-256 `5cdc37d9…87a1`, 21 páginas, **diferente**) | Correspondência com o anexo **não confirmada** | Se o anexo for o de `2defaa5f…`, ele difere do final (referências, descrição geográfica, apêndice B) |
| PDF × fontes | `article/ARTIGO_ATRIBUICAO_HUNGARO.pdf` é byte a byte igual a `article/build/main.pdf`, compilado das fontes atuais | SHA-256 idênticos | Feito | — |
| Espaçamento | `\espacamentocorpo = 1,428` em `config/formatting.tex` (única definição); 1,428 × 14,5 pt = 20,7 pt = 1,5 linha do Word com Arial 12 | Comentário e valor no arquivo | Feito | 1,5 é **instrução do autor**; o guia FAESA não foi localizado |
| Manifestos | 201 manifestos de dados de `CONGELAMENTO.json` recalculados (SHA-256) contra `data/raw/` | 201 conferem, 0 divergentes, 0 ausentes | Feito | Resultados citados vêm de dados com identidade conferida |
| Cópia anterior | Guardada fora da árvore ativa | `rodada3_antes\` (PDF, fontes `.tgz` sem `build`, `uv.lock` anterior) | Feito | — |

## 3. Referências

Detalhe em `article/reference_audit.md`.

| Obra | A (bibliográfica) | B (afirmação) | Ação |
|---|---|---|---|
| Kirkpatrick et al. | Crossref confere | Texto lido: aceitação probabilística de pioras (critério de Metropolis); sem página | Mantida |
| Toth & Vigo | Crossref (DOI SIAM) confere | Só título e escopo; capítulos não lidos | Restrita à definição de VRP; variantes movidas para Cordeau & Laporte e Berbeglia et al. |
| Banks et al. | Catálogo da editora e bibliotecas; folha de rosto não vista | Uso genérico (nome da técnica) | Mantida, sem trecho |
| Cormen et al. | Edição nunca identificada | Nenhum trecho lido | **Removida** do texto e do `.bib` |
| Pavone, Kontou, Pouls | Crossref (e OSTI para Kontou) confere | Resumos sustentam as afirmações; **texto integral não lido**, e o artigo declara isso | Mantidas, sem acrescentar detalhes |

Auditoria: 22 chaves citadas = 22 entradas do `.bib`; nenhuma órfã nem duplicada.

## 4. Instalação limpa

Cópia do repositório sem `.venv`, `.git`, `data/` (privado) e `article/`, em pasta separada; `uv sync --frozen --extra test --extra quality --extra notebooks` com Python 3.12.14; sem `PYTHONPATH` nem `VIRTUAL_ENV`; o `.venv` do projeto não foi tocado.

| Etapa | Resultado |
|---|---|
| Instalação (67 pacotes, lock preservado) | OK |
| `import tcc_frota`, `tcc-frota --help` | OK |
| `python scripts/download_geography.py` (rede: IBGE e Overpass) | OK; baixa um **novo** instantâneo do OSM, diferente do congelado, usado só na cópia |
| `pytest` | 195 aprovados (cópia anterior à inclusão de um teste novo); depois, `tests/unit` rodou de novo na cópia, com o teste novo, e passou |
| `ruff check .` / `ruff format --check .` | sem erros |
| Exemplo sintético: `run-synthetic --scenarios S1 --seeds 101-102` e `analyze-synthetic` | OK (exemplo mínimo de 2 sementes; sem significância) |
| Figura: `tcc-frota figures` | OK |
| Notebooks (5) | 5 OK; no 01, sem os dados privados, o caderno imprime que eles faltam |

Correção de declaração (menor impacto): `uv.lock` não incluía o extra `notebooks` (`folium` e dependências). `uv lock` acrescentou 10 pacotes (branca, certifi, charset-normalizer, folium, idna, jinja2, markupsafe, requests, urllib3, xyzservices) e **não mudou nenhuma versão existente**; `uv lock --check` passa. Cópia do lock anterior em `rodada3_antes\`.

Grupos de dependência (documentados no README): execução; desenvolvimento (`test`, `quality`); notebooks (`notebooks`); fontes privadas (`fontes`, não instalado na validação). **Compilação LaTeX (XeLaTeX, BibTeX, `latexmk`, Arial) não é gerenciada pelo `uv.lock`**; vale para o artigo, não foi reinstalada em ambiente novo.

Limites da validação: sem os dados privados, os testes de regressão que exigem Parquet históricos são pulados na cópia limpa e o `run-historical` não foi exercitado. A cópia usou outro instantâneo do OSM; não prova reprodução bit a bit da linha B.

## 5. Notebooks (`notebook/`)

Todos executados por `scripts/run_notebooks.py` (kernel limpo por caderno, células de cima para baixo, com a ordem de execução 1…n conferida e sem erros). Resultado em `reports/manifests/notebooks_execucao.json`.

| # | Caderno | Finalidade | Dados | Figuras/arquivos | Dependência externa | Bloqueio |
|---|---|---|---|---|---|---|
| 01 | `01_data_overview.ipynb` | Visão geral dos dados do estudo | Catálogo de cenários, volumes congelados; testa a presença de `data/raw` | Nenhum | Nenhuma | Sem os dados privados só imprime a ausência |
| 02 | `02_hungarian_example.ipynb` | Exemplo didático 3×3 (conjunta × sequencial) | Valores hipotéticos definidos no próprio caderno | Nenhum | Nenhuma | — |
| 03 | `03_greater_vitoria_h3.ipynb` | Mapa H3 do recorte | `data/geographic/` (IBGE, OSM; públicos) | `reports/figures/study_area_h3_map.{pdf,png,html}` | Mapa interativo abre *tiles* OSM pela internet | Exige `download_geography.py` se `data/geographic` faltar |
| 04 | `04_historical_results.ipynb` | Resultados históricos | **Só agregados congelados** (`reports/historical/frozen_evaluation/analise/`); nada é reexecutado | Figuras de km, atendimento e ICs em `reports/figures/` | Nenhuma | — |
| 05 | `05_synthetic_results.ipynb` | Resultados sintéticos e limites de independência | `reports/synthetic/.../resumo_contrastes.csv` (congelado) | Resumo sintético em `reports/figures/` | Nenhuma | — |

Nenhum caderno substitui dados históricos por sintéticos: os históricos leem os agregados congelados e os sintéticos leem os congelados da linha B.

**Exceção UP031 (`%` em *strings*):** **removida.** As seis linhas dos cadernos 02, 04 e 05 foram convertidas em *f-strings*; o `per-file-ignores` que eu havia criado foi apagado de `pyproject.toml`. Não há exceção de lint nova; as exceções globais já existentes em `pyproject.toml` têm comentário de motivo (por exemplo B905, B023, E501).

## 6. Cobertura dos testes mantidos

A contagem (196) não prova validade operacional nem científica. Cobertura por tema:

| Tema | Testes (arquivo) |
|---|---|
| Húngaro | ótimo por força bruta, oráculo SciPy, empates, prioridade ao atendimento, matriz retangular em ambos os sentidos, lote vazio, sem veículo elegível, pares inviáveis (`test_assignment_dispatch.py`) |
| Comparadores A e B | mais próximo no raio, FIFO sem elegíveis, mesmas entradas e mesma assinatura para A e C (`test_assignment_dispatch.py`) |
| Lotes e informação | o atribuidor só vê pedidos já chegados e só decide em múltiplos de 60 s (`test_simulation_invariants.py`) |
| Espera | inclui o atraso até o lote; **novo:** espera = atraso do lote + deslocamento de aproximação, com igualdade numérica; nunca negativa |
| Unicidade, jornada e compromissos | pedido atendido no máximo uma vez; motorista não atende dois serviços ao mesmo tempo (instâncias aleatórias); fora da jornada e compromisso bloqueiam o despacho |
| Estados, posições, km | km vazio = aproximação + reposicionamento; posição futura nunca usada (`test_data_initial_position.py`); modo de fim de dia |
| Reprodutibilidade | congelados (`test_frozen_results.py`, com Parquet), estrutura, camadas, ausência de caminhos absolutos |

Lacuna concreta fechada: o teste da espera total (lote + deslocamento). Sem outras lacunas relevantes identificadas.

## 7. Equivalência após a reorganização

Verificação **parcial**, não reprodução integral:

| Verificação | Resultado | Evidência |
|---|---|---|
| 3 pares sintéticos (S1/20001, S3/20007, S2_frota_escassa/20040) | idênticos aos congelados | `reports/manifests/equivalencia_reorganizacao.json` |
| Tabelas dos dois períodos regeneradas dos Parquet congelados | idênticas | mesmo manifesto |
| 1 dia real (2026-09-16), A, B, C | idêntico (execução manual da reorganização) | registrado em `docs/repository_migration.md` §5; **o manifesto JSON atual não contém essa entrada** |

**Não executado:** `python scripts/check_equivalence.py --historical` (dias 2026-09-16 e 2026-10-01). Lê Parquet privados locais e os resultados congelados; roda A, B e C nesses dois dias com o código novo e compara; não usa fontes remotas; acrescenta um dia do período final. **Bloqueio:** exige `TCC_REAL_DATA_AUTHORIZED=YES`, que só o proprietário levanta; não o levantei. Comando e cuidado com o manifesto em `docs/reproducibility.md`. Os 40 dias e as 880 execuções sintéticas não foram reexecutados. Os manifestos antigos permanecem intactos.

## 8. Texto do artigo (coerência, geografia, paginação)

| Pendência | Correção | Local | Situação |
|---|---|---|---|
| "rede sintética (OSM)" | Reescrito: "cenários operacionais sintéticos, cuja operação é gerada artificialmente… rede viária derivada do OpenStreetMap"; separação explícita entre rede viária (modelo de custo), células H3 (pontos de parada e zonas do gerador; **não participam da atribuição**, confirmado no código: H3 só em `scenarios/` e `visualization/`), gerador de demanda e mapa de apresentação | Seções 2.1, 3.4 | Feito |
| Pontes | Só verificações estruturais; não se afirma ponte a ponte nem tempos validados | Seção 3.4; Apêndice B | Mantido |
| Elementos preservados | C×A principal e C×B complementar; E2 reprovado em outubro; −0,36 p.p. (85/23.523) × ≈ −0,58 % (85/14.551); espera só entre atendidos; linha sintética exploratória e complementar; sem economia operacional comprovada | Resumo, 3.6, 4, 5 | Conferido na leitura |
| Kuhn–Munkres e SciPy | Identificação vem da implementação própria; SciPy só como oráculo de teste | 2.3 | Conferido |
| "≈ 0,1 s/dia" | Relógio da chamada de simulação por dia, sem a construção do mundo | 4.1 | Conferido |
| Apêndice B | "535 testes" rotulado como do congelamento (código anterior à reorganização) | Apêndice B | Feito |
| Citação do IBGE | Parênteses aninhados removidos | 3.4 | Feito |
| Página 23 e Tabela 9 | Referências terminam na 23; o Apêndice A começa na 23; a **Tabela 9 é do Apêndice A** (resultados por cenário), vem depois do título e do texto do apêndice (cai na página 24 por falta de espaço) e é chamada no primeiro parágrafo do Apêndice A (o apêndice é chamado na Seção 4.2). Fica meia página em branco na 23, aceita | Apêndice A | Coerente |
| Paginação | 25 páginas; limite de 25 até o fim das referências cumprido com folga (23); Apêndices A e B contínuos e chamados no texto; são apêndices (autorais), sem anexos | — | Feito |

Formatação: Arial 12, margens 30/20/30/20 mm, A4, espaçamento do corpo 1,5 (**instrução do autor**), número no canto superior direito; as medidas vêm do **PDF-modelo** (inferência, não do guia). Título, autores e e-mails aprovados preservados. **Conformidade institucional integral não declarada**: o guia FAESA não foi localizado.

## 9. Pendências que dependem de informação externa

1. Guia FAESA e confirmação do orientador. Pergunta pronta (não enviada): *Professor, para a formatação final: (1) existe guia da FAESA para o TCC 2026-1? (2) o espaçamento do corpo deve ser 1,5 e o de legendas, tabelas e referências, simples? (3) margens 30/20/30/20 mm, Arial 12 e número no canto superior direito estão corretos? (4) o limite de 25 páginas inclui os apêndices?*
2. PDF anexado: correspondência não confirmada (arquivo inacessível).
3. TCC "(2).pdf": não existe no disco; usada a versão de 28/10/2026 (SHA-256 `6DA6D100…FAC034`).
4. Texto integral de Pavone, Kontou e Pouls; capítulos de Toth & Vigo e Banks et al.; página do trecho de Kirkpatrick et al.
5. `check_equivalence.py --historical`: depende do proprietário (§7).
6. Compilação LaTeX em máquina sem MiKTeX/TeX Live: não testada.
7. Revisão humana (orientador/banca): não houve.

## 10. Limpeza

Removidos: `.reorg_old/` (cópia idêntica em `arvore_antiga`, conferida por `diff`) e `.audit-deps/` (pacote `pyarrow` instalado à parte, ignorado pelo git e regenerável). Mantidos: `tcc-artigo-latex/atribuicao/` (cópia antiga de 21 páginas; guardada também em `artigo_atribuicao_antes_da_revisao.zip`, com o mesmo SHA-256 do PDF), caches ignorados e `article/build/` (regenerável). Nada foi commitado nem adicionado ao stage.

## 11. Rodada 5 (09/11/2026)

Seções alteradas: Resumo/Abstract, 2.3 (frase removida a pedido), 3.3 (d), 4.2 (sensibilidade, recalibração e teste fora da amostra, limites), Conclusão, Declarações, Apêndice B (`tab:sens` ampliada, `tab:valid` movida, `tab:r5`, `tab:mensal`, Figura `fig:r5`) e Apêndice C. Tabelas congeladas `tab:abs` e `tab:contr`: linhas de dados idênticas ao commit `3e65f3b` (só notas de fonte mudaram na rodada 4). Compilação: 32 páginas, referências terminam na p. 25, apêndices a partir da p. 26; 0 caixas estouradas, 0 referências/citações indefinidas. Testes: 203 aprovados, 0 falhas (junit); `ruff check` e `ruff format --check` limpos. `scripts/validar_baseline.py` não existe mais desde a reorganização (`3e65f3b`); a conferência dos congelados foi feita por `git status` (sem alterações em `reports/historical/frozen_evaluation`, `reports/synthetic`, `reports/tcc_final`, `resultados`). Título: mantido; sugestão não aplicada.

## 12. Rodada 6 (09/11/2026)

Texto simplificado sem nova análise. Corpo da p. 2 à p. 21 (20 páginas, limite 25); apêndices A–D a partir da p. 22, em página nova. Referências ocupam cerca de 1,5 página (o pedido previa 2 a 3; não foram acrescentadas referências). 0 caixas estouradas, 0 citações ou referências indefinidas. Tabelas: 1 problemas, 2 exemplo, 3 políticas, 4 períodos, 5 resumo (nova), 6 e 7 congeladas (linhas de dados inalteradas; rótulos E1–E3 trocados por texto), 8 sintéticos; apêndices: 9 planos de informação, 10–16. Testes: 203 aprovados, 0 falhas; Ruff limpo. Título mantido (decisão com o orientador). Declaração de vínculo, termos de acesso e conflito de interesse: campos marcados para preenchimento pelos autores.

## 13. Rodada 7 (09/11/2026)

Leitura dos resultados corrigida, sem mudar número congelado. Plano em `docs/REGISTRO_DECISOES.md` R-29 (17:57:10), antes das simulações. Nova Tabela 8 no corpo (B, C e D; D posterior); novas Tabelas 14 (intervalos C×B por variante) e 18 (conferência da coleta) no Apêndice B; demais tabelas renumeradas, 6 e 7 inalteradas. Corpo da p. 2 à p. 23 (22 páginas, limite 25); apêndices a partir da p. 24. 0 caixas estouradas, 0 citações ou referências indefinidas. Congelados: 19/19 + 138/138 iguais, 40 Parquets iguais à rodada 6. Testes: 203 aprovados, 0 falhas; Ruff limpo. Nota ao orientador visível na declaração não preenchida. Relatório: `reports/diagnostics/batching/global_greedy_comparison/RELATORIO.md`.

## 14. Rodada 8 (09/11/2026)

Título novo (cabeçalho e metadados do PDF). Declarações reduzidas a dados, código e dados e registro, por decisão dos autores. Resumo e abstract com o guloso global e com os 29 atendimentos a mais do teste. Nova Tabela 19 (dias do teste contra os mesmos dias da semana de outubro) no Apêndice B; Tabela 20 passa a ser a dos cenários sintéticos por cenário. 37 páginas; corpo da p. 2 à p. 23 (22 páginas); apêndices a partir da p. 24. 0 caixas estouradas, 0 citações ou referências indefinidas. Congelados iguais; 203 testes aprovados; Ruff limpo. Relatório: `reports/diagnostics/availability/test_period_weekday_comparison/RELATORIO.md`.

## 15. Rodada 9 (09/11/2026)

Identificadores da empresa (produto, região, serviços, categoria) retirados do Apêndice D e da metodologia; recorte descrito de forma genérica. Busca no fonte, nas figuras, no PDF e nos metadados antes e depois; restam só "viagens" (palavra comum) e V1–V3 do exemplo hipotético. 37 páginas; corpo da p. 2 à p. 23; 0 caixas estouradas, 0 indefinidas. Congelados iguais; 203 testes aprovados; Ruff limpo. Relatório: `reports/diagnostics/consistency/article_anonymization_check/RELATORIO.md`.
