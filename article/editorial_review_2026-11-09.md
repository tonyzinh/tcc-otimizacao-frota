# Revisão editorial do artigo — 09/11/2026

## Conferência de completude acadêmica (revisão atual)

Esta seção descreve o PDF atual e substitui, para organização do texto e paginação, os registros históricos abaixo. Foram conferidos diretamente o esquema da página da biblioteca FAESA, o guia institucional de 2024 e, apenas como exemplo de organização, o TCC de Marcelo Miranda e Thiago Poggian. As regras conflitantes seguem a precedência registrada em `article/compliance_report.md`; o artigo de referência não foi usado como norma.

| Elemento solicitado | Onde aparece no artigo | Ajuste e coerência verificada |
|---|---|---|
| Contexto, delimitação e decisão | Introdução, primeiro parágrafo; Metodologia, “Despacho em lotes” | Km vazio definido como aproximação estimada; o Húngaro forma pares apenas no lote corrente, sem previsão ou reposicionamento. |
| Pergunta de pesquisa | Introdução, segundo parágrafo | Frase interrogativa inclui C×A e C×B, km vazio, atendimento e condições de comparação com entradas comuns. |
| Hipótese original | Introdução, terceiro parágrafo; Considerações finais, segundo | Mantida a expectativa anterior de redução de km nas duas comparações; atendimento preservado continua critério adicional. A conclusão distingue os períodos em que ambos ocorreram daqueles em que o serviço falhou. |
| Objetivo geral | Introdução, quarto parágrafo; Considerações finais, primeiro | “Avaliar” substitui a formulação implícita; alcançado como comparação no simulador, sem inferir economia operacional. |
| Objetivos específicos | Introdução, quinto parágrafo; Revisão da literatura e Metodologia; Considerações finais, terceiro | Formulação, implementação e verificação, avaliações com entradas comuns, comparação de distância/atendimento/espera e exame dos limites têm correspondência no método e nos resultados. |
| Justificativa | Introdução, sexto parágrafo | Relevância da troca entre distância e serviço e contribuição de separar espera pelo lote da atribuição conjunta; combustível, emissões e dinheiro não são resultados medidos. |
| Síntese metodológica | Introdução, sétimo parágrafo | Resume simulação, dados históricos e sintéticos, políticas e métricas; detalhes permanecem na Metodologia. |
| Desenho da pesquisa | Metodologia, “Desenho e políticas comparadas” | Classificação quantitativa e comparativa justificada pelas diferenças calculadas sob entradas comuns; avaliação histórica contrafactual e retrospectiva; cenários sintéticos separados. |
| Dados, inclusão e tratamento | Metodologia, “Dados reais” e “Cenários sintéticos”; Tabela 2; Apêndice A | Origem, períodos, pedidos sem agendamento, limiares de elegibilidade, disponibilidade reconstruída e informação retrospectiva do avaliador são explícitos. |
| Políticas, calibração e períodos | Metodologia, Quadro 2, “Despacho em lotes” e “Congelamento e origem da janela de 60 s” | A/B/C sob entradas comuns; D marcado como posterior. Parâmetros de março e seleção de 60 s separados da recalibração posterior. |
| Métricas e inferência | Metodologia, “Métricas e estatística”; Tabelas 3–5 | Denominadores, critério de atendimento, espera, unidade diária, intervalo de confiança e caráter exploratório dos sintéticos preservados. |
| Verificação, validação e reprodução | Metodologia, abertura e “Dados reais”; Resultados, “Limitações”; Apêndices A–B | Testes do algoritmo separados da validação parcial de componentes e da validação operacional não alcançada. Código, configurações e manifestos permitem conferir o trabalho; dados históricos exigem acesso autorizado. |
| Resposta e limites | Considerações finais, quatro parágrafos | Resposta direta: menos km nos períodos congelados, porém perda de atendimento em C×A/outubro; hipótese de redução de km sustentada nesse recorte, expectativa conjunta apenas parcialmente sustentada. Teste posterior e validade operacional não foram tratados como confirmação. |

**Inconsistências corrigidas:** a introdução tinha objetivo geral e etapas condensados em uma frase, pergunta limitada à referência imediata e hipótese distante da exposição dos critérios de serviço. A conclusão não nomeava explicitamente o status da hipótese nem em que sentido o objetivo foi alcançado. A metodologia descrevia os procedimentos, mas não justificava o desenho quantitativo, comparativo e retrospectivo. A redação atual preserva os resultados congelados, as análises posteriores, a falha de atendimento em outubro, o teste inconclusivo e a confidencialidade das entradas.

**Paginação e execução:** após a correção do alinhamento e do espaço entre seção e subseção, o PDF recompilado termina as referências na página 24; os apêndices ocupam as páginas 25–29, total 29. Não foram alterados dados, parâmetros, código de simulação ou conclusões numéricas. A compilação terminou sem caixas transbordadas.

**Uniformidade dos elementos tabulares:** a revisão visual posterior aplicou a mesma grade aos dois quadros e às sete tabelas do artigo e às 13 tabelas do suplemento. A primeira interpretação havia limitado a grade aos quadros; a correção atende ao pedido expresso do proprietário. A divergência com a orientação do esquema FAESA sobre linhas verticais em tabelas está registrada em `article/compliance_report.md` e na decisão R-47. Dados e resultados não foram alterados.

## Mapa de estrutura e orçamento

| Origem | Ação | Destino e função |
|---|---|---|
| Resumo e abstract extensos | Reescrever | Sínteses equivalentes dos achados decisivos, inclusive outubro e teste posterior |
| Introdução e fundamentação | Manter e polir | Problema, comparação A–C, exemplo, formulação e escopo |
| Fluxograma do antigo Apêndice A | Mover | Metodologia, no ponto da decisão por lote |
| Algoritmo em pseudocódigo | Retirar por redundância | Fluxograma, formulação e descrição do método permanecem |
| Tabelas de resumo, valores absolutos e contrastes | Manter | Perguntas distintas: síntese, denominadores e contrastes congelados |
| Gráfico central do antigo Apêndice B | Mover | Resultados congelados |
| Recalibração e teste em um parágrafo | Reescrever | Procedimento, achado, variação temporal e interpretação separados |
| Quatro apêndices | Fundir e selecionar | Apêndices A e B no PDF; séries diárias, grades completas, mapa e rastreio no suplemento entregue |
| Conclusão extensa | Reescrever | Resposta, atendimento, teste, limite operacional e próximos passos |

Após a revisão integral da redação, o orçamento observado é de 22 páginas até o fim das referências e 6 páginas de apêndices, total de 28. A tipografia e as margens existentes foram mantidas.

Na revisão da narrativa, a introdução passou a apresentar o problema e o desenho das comparações sem explicar o algoritmo passo a passo. A discussão interpreta C×A, C×B e D, enquanto as tabelas guardam os valores detalhados. A conclusão responde à pergunta de pesquisa sem recapitular a grade de percentuais; preserva a perda de atendimento em outubro e a inversão de C×B no teste posterior.

A passada de continuidade reescreveu o exemplo didático, separou o desenho da validação na metodologia e distinguiu observação, simulação e interpretação nas análises posteriores. Nenhum número de tabela foi recalculado.

## Registro de inconsistências e limites

| Local | Evidência | Correção ou pendência |
|---|---|---|
| Metodologia: setembro/outubro e teste | Plano e decisões locais distinguem seleção de janela/método da recalibração posterior | Setembro/outubro são externos à seleção; 26/10–08/11 é o único teste chamado fora da amostra na rodada posterior. Independência operacional plena não demonstrada. |
| Apêndice A: sintéticos “confirmatórios” | Plano previa 20 testes com Holm, mas resultados sintéticos foram vistos antes da adoção | Preservados plano e correção; conclusão classifica a evidência sintética como exploratória. |
| Metodologia e declarações: congelamento | Hashes e manifestos locais, sem registro externo com carimbo verificável | O texto nomeia o mecanismo local e evita chamar de pré-registro externo. |
| Antiga Tabela 15, atual Tabela 10 | Mediana de aproximações observadas versus média de km por atendido simulada, em populações distintas | Nota explicita que a diferença não é erro diretamente comparável. Sem recálculo de dados individuais. |
| Método e resultados: denominadores | Pedidos elegíveis incluem cancelados como demanda; aceite observado exige registro de motorista a caminho; atendimento é pedido servido pelo simulador | Definições mantidas nos respectivos contextos; diferenças não foram igualadas. |
| Análises posteriores: compromisso | Relatórios não registraram violações de compromisso | Nota na tabela do teste informa que ausência não equivale a zero. |
| Método: informação temporal | Jornada realizada e duração observada/mediana diária vêm de reconstrução retrospectiva; o simulador usa a duração para filtrar pares com conflito de compromisso | Texto distingue entradas do avaliador do que a política recebe diretamente e explicita a influência indireta da duração na elegibilidade. O impacto de substituir essa informação exigiria novo experimento, não feito nesta revisão. |
| Algoritmo Húngaro | Código usa custo inteiro, bônus de cardinalidade, colunas fictícias e potenciais | Formulação preservada; nenhum experimento foi substituído. |
| Teste de 12 dias e mecanismo do guloso | Intervalos incluem zero; proximidade futura da demanda não foi medida | “Pouco poder” trocado por amostra curta e imprecisão; explicação causal mantida como hipótese. |
| Nove variantes sintéticas | Documentação informa apenas outro sorteio | Texto conserva a ressalva: não são nove condições operacionais distintas. |
| Normas e referência visual | O guia institucional segue indisponível. O PDF de referência e sua análise passaram a estar disponíveis em `.pack/` após a revisão inicial | A referência confirma um padrão sóbrio de Arial e margens estimadas de 30/20/30/20 mm, mas não é norma institucional. A formatação existente foi preservada. |

O código de simulação não foi alterado nesta revisão. Nenhuma divergência nova que justificasse recalcular os resultados congelados foi resolvida por alteração de algoritmo.

## Conferência editorial final dos subtítulos e elementos gráficos (09/11/2026)

Os cinco marcadores de parágrafo em Resultados e discussão foram convertidos em subtítulos independentes, em caixa alta regular, seguidos pelo texto em novo parágrafo. Os oito marcadores do Apêndice A e seus equivalentes no suplemento foram separados do texto e destacados em caixa alta e negrito. Isso corrige o caso “FATOR RUA/RETA E ESCOLHA. O km é...” apontado pelo proprietário. O título dos apêndices também ficou em negrito. Títulos de tabelas, quadros e figuras foram centralizados e colocados em negrito, com 6 pt até o elemento; a nota “Fonte” ficou a 6 pt abaixo. A primeira página ficou sem número, e o Abstract conserva o número 2.

O PDF principal termina na página 30, com referências até a 25; o suplemento termina na 19. Houve ajuste de 12 para 8 pt no espaço entre parágrafos dos apêndices para preservar o limite de páginas, sem cortar texto ou alterar métricas. Inspeção visual das páginas 2, 14 e 28 e extração das páginas 1, 25, 26 e 30 confirmaram o resultado. A compilação terminou sem caixas transbordadas ou remissões indefinidas.

**Correção posterior da leitura do exemplo:** o proprietário esclareceu que o negrito desejado é o dos cabeçalhos dentro de cada tabela, não o do título externo. Todos os títulos externos voltaram ao peso regular; os cabeçalhos internos foram destacados, o conteúdo foi reduzido para 9,5 pt com maior folga vertical, e as notas “Fonte” foram abreviadas. A distinção entre os dois valores arredondados para 50,3 na tabela de validação foi preservada na prosa do suplemento. O PDF principal passou a 29 páginas, com referências até a 24; o suplemento permanece com 19 páginas. As tabelas das páginas 14 e 11 foram conferidas visualmente, sem corte ou sobreposição.

**Equações (1)–(2):** as duas prioridades do objetivo e as três restrições foram separadas em linhas alinhadas, conforme a observação do proprietário. A página 6 foi conferida visualmente após a compilação: índices, sinais, numeração e texto estão legíveis; o sentido matemático e as referências `eq:obj` e `eq:rest` não mudaram.

**Correção de legibilidade posterior:** o proprietário informou que as equações ainda não eram compreensíveis. O corpo agora define $N$ e $K$ em palavras, mostra só a ordem da decisão na equação (1) e explica as restrições em frases curtas. A notação completa foi transferida ao Apêndice A, onde a equação das restrições passou a ser a (3). A página 6 e o início do apêndice foram conferidos; o PDF principal tem 30 páginas, referências até a 24, sem caixas transbordadas ou remissões indefinidas. A formulação científica e o algoritmo permanecem os mesmos.

## Conferência da referência e entrega final

O PDF de referência em `.pack/referencia/` tem 24 páginas, de acordo com a inspeção página a página do pacote. `analise_referencia/metadados.md` mede o início recorrente do texto em 30 mm da borda esquerda e 30 mm do topo e estima margens direita e inferior de 20 mm. `tipografia.md` registra Arial 12 pt na prosa; `guia_editorial.md` registra sete quadros descritivos, sem tabelas quantitativas ou equações. Por isso, o artigo manteve seções numeradas, fórmulas e tabelas numéricas próprias do estudo, sem copiar o padrão de quadros da referência. A ausência do guia institucional impede certificar conformidade integral.

O script `scripts/build_article.py` agora verifica o código de saída de cada etapa de XeLaTeX/BibTeX antes de copiar o PDF; anteriormente podia copiar um arquivo antigo após uma falha. A cadeia foi executada com sucesso em 09/11/2026. `article/build/main.pdf` e o PDF com nome de entrega foram gerados na mesma execução: 28 páginas A4. O log final não contém erros de LaTeX, referências ou citações indefinidas nem caixas *overfull*. As 28 páginas foram renderizadas e examinadas em mosaicos: não foram identificados cortes, sobreposições ou tabelas ilegíveis; a página 28 termina com espaço livre após o último apêndice. A conferência visual é editorial, não certificação de norma.
