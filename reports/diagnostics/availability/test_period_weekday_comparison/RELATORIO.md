# Rodada 8: decisões dos autores e três pontos finais (09/11/2026)

Nenhum número congelado mudou. A única análise nova é a tabela dia a dia, feita a partir de agregados já gravados, sem simulação. Nada foi commitado nem adicionado ao stage.

## 1. Título

| Versão | Título |
|---|---|
| Português | Despacho em lotes com atribuição conjunta pelo algoritmo Húngaro: avaliação por simulação do km vazio em aplicativos de transporte |
| Inglês | Batch dispatching with joint assignment by the Hungarian algorithm: a simulation-based evaluation of empty kilometers in ride-hailing applications |

- Alterado em `article/config/metadata.tex`, que alimenta a primeira página e o campo `pdftitle`.
- O metadado do PDF foi conferido com PyMuPDF e traz o título novo.
- Nenhuma seção do texto citava o título antigo.

## 2. Declarações e descrição da operação

**Removidos:**
- a nota ao orientador;
- os campos de vínculo, termos de acesso e conflito de interesse;
- o trecho sobre o OneDrive e a sincronização, inclusive as datas de extração e de desinstalação.

**Mantidos:** dados (pseudonimização por HMAC-SHA256, só agregados), código e dados, e registro.

**Descrição da operação:** no corpo, a operação aparece só como "uma empresa de transporte por aplicativo que opera na Grande Vitória (ES)". Isso vale para o resumo, a introdução, a fundamentação, a metodologia, a conclusão e as declarações; o abstract usa a versão equivalente em inglês. "Serviços Prime" saiu da metodologia.

**Apêndice D:** continua com os códigos de produto, região e serviços, para rastreio. Não faz parte do corpo. Se também devem sair de lá, é uma frase a remover.

**Atenção:** sem a declaração de vínculo e de conflito de interesse, o artigo não informa nada sobre isso. Se a banca ou a revista exigir essa declaração, ela terá de voltar.

## 3. Resumo e abstract: guloso global

**Divergência com o pedido.** A frase pedida dizia que o guloso "atendeu o mesmo ou mais que o Húngaro com a calibração nova". Os dados (`rodada7/bcd_resumo.csv`) não sustentam isso em setembro e outubro:

| Período (calibração nova) | Atendidos, D − C | Em % de C | Km, D × C |
|---|---:|---:|---:|
| Setembro | −41 | −0,37% | −1,23% |
| Outubro | −25 | −0,17% | −2,04% |
| Teste 26/10–08/11 | +29 | +0,78% | −0,62% |

**Frase escrita:** "Um guloso global simples, que escolhe primeiro o par mais curto, teve menos km que o Húngaro; com a calibração refeita, atendeu quase o mesmo em setembro e outubro (até 0,4% a menos) e mais no teste, e a vantagem do Húngaro sobre ele não se confirmou." O abstract traz a versão equivalente.

## 4. Teste fora da amostra: 29 atendimentos a mais

Acrescentado no resumo, no abstract, na Tabela 5 (última coluna), na seção 4.3 e na conclusão: a atribuição conjunta atendeu 29 pedidos a mais que o lote simples, com o mesmo km por atendido (2,84).

| Política | Km vazio | Atendidos | Km por atendido |
|---|---:|---:|---:|
| C (atribuição conjunta) | 10.626,0 | 3.741 | 2,8404 |
| B (lote simples) | 10.534,0 | 3.712 | 2,8378 |

Os dois valores ficam iguais com duas casas; a diferença está na terceira.

## 5. Queda a partir de 31/10

**Plano:** registrado em `docs/REGISTRO_DECISOES.md`, R-31, às 09/11/2026 18:22:00, antes de montar a tabela.
- **Referência:** mediana dos mesmos dias da semana de 01–25/10, sem 12/10, que é feriado nacional.
- **Critério de queda:** pedidos abaixo de 80% da referência.
- **Ressalva:** os totais desses dias já tinham sido vistos nas rodadas 5 e 7.

**Dados e script:** `rodada7/dados_por_dia.csv` para pedidos e motoristas; `rodada5/teste_por_dia.csv` e `setout_por_dia.csv` para o atendimento em A com a calibração nova. Script: `scripts/pos_hoc_rodada8.py`. Saídas: `dia_a_dia.csv`, `referencia_outubro.csv`, `criterio.txt`.

| Dia | Semana | Pedidos | Out. | % de out. | Motoristas | Out. | Atendidos em A (%) | Out. (%) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 26/10 | seg | 611 | 909 | 67 | 85 | 78,0 | 69,7 | 64,9 |
| 27/10 | ter | 939 | 855 | 110 | 82 | 86,0 | 65,7 | 70,3 |
| 28/10 | qua | 960 | 1.028 | 93 | 81 | 80,0 | 66,7 | 69,4 |
| 29/10 | qui | 817 | 1.088 | 75 | 69 | 87,5 | 66,5 | 71,5 |
| 30/10 | sex | 682 | 1.139 | 60 | 75 | 88,5 | 70,7 | 66,3 |
| 31/10 | sáb | 215 | 883 | 24 | 41 | 57,5 | 47,9 | 48,4 |
| 01/11 | dom | 185 | 603 | 31 | 35 | 46,5 | — | 50,5 |
| 02/11 | seg (Finados) | 228 | 909 | 25 | 30 | 78,0 | 34,6 | 64,9 |
| 03/11 | ter | 309 | 855 | 36 | 68 | 86,0 | 55,0 | 70,3 |
| 04/11 | qua | 395 | 1.028 | 38 | 65 | 80,0 | 58,7 | 69,4 |
| 05/11 | qui | 335 | 1.088 | 31 | 60 | 87,5 | 58,2 | 71,5 |
| 06/11 | sex | 298 | 1.139 | 26 | 54 | 88,5 | 61,7 | 66,3 |
| 07/11 | sáb | 300 | 883 | 34 | 35 | 57,5 | 29,3 | 48,4 |
| 08/11 | dom | 149 | 603 | 25 | 25 | 46,5 | — | 50,5 |

- **Resultado pelo critério:** os quatro dias úteis de 03 a 06/11 tiveram queda (26–38% dos pedidos de outubro). Parte da queda é de calendário, mas não toda.
- **Motoristas:** caíram menos que os pedidos, para 61–81% de outubro.
- **Antes de 31/10:** 26, 29 e 30/10 já estavam abaixo do limite.
- **Causa:** continua desconhecida. A contagem por serviço segue não feita.

**No texto:**
- **Seção 4.3:** frase sobre o calendário e os dias úteis, com remissão à tabela.
- **Apêndice B:** parágrafo e nova Tabela 19.
- **Apêndice D:** rastreio da rodada 8.
- "Mudança de regime" já tinha saído na rodada 7 e não aparece no texto.

**Para o relatório, não para o artigo:** pelo calendário eleitoral da Constituição (primeiro e último domingos de outubro), 04/10 e 25/10 seriam domingos de eleição e entram na referência de domingo. Isso não foi verificado em fonte oficial. Os domingos do teste, 01 e 08/11, ficaram fora da simulação.

## 6. Verificação

**Resultados congelados** (`hashes_congelados.csv`):
- `reports/tcc_final`: 19 de 19 iguais ao pré-registro.
- Arquivos rastreados: 138 de 138 iguais a HEAD.
- 40 Parquets: iguais à rodada 7.
- Os 197 hashes são idênticos aos da rodada 7.

**Números** (`numeros_antes_depois.csv`):
- Nenhum valor que estava no texto saiu.
- Os valores novos vêm da Tabela 19, da frase do resumo ("0,4", "2,84"), do abstract ("0.4", "2.84") e das frases sobre o calendário.
- As datas do trecho do OneDrive saíram com o trecho, mas aparecem em outros pontos do texto, por isso não mudam a contagem.

**Compilação:**
- 0 citações ou referências indefinidas.
- 0 caixas estouradas.
- 37 páginas. O corpo, da introdução (p. 2) ao fim das referências (p. 23), tem 22 páginas, abaixo do limite de 25.
- Apêndices A–D a partir da p. 24, com tabelas numeradas em sequência até 20.
- PDF copiado para `article/ARTIGO_ATRIBUICAO_HUNGARO.pdf`.

**Testes:** `pytest` deu 203 testes, 0 falhas, 0 erros e 0 pulados, em 8,1 s (`pytest_junit.xml`).

**Lint:** `ruff check .` sem erros; `ruff format --check .` com 126 arquivos formatados, depois de formatar o script novo.

## 7. Registros

- `docs/REGISTRO_DECISOES.md`: R-31 (plano e resultado) e R-32 (decisões dos autores e divergência da frase do resumo).
- `article/RELATORIO_CONFORMIDADE.md`: seção 14.
