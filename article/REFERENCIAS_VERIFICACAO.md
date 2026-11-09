# Verificação das referências pendentes (rodada 3, 09/11/2026)

Separação usada: **A** = verificação bibliográfica (autores, título, ano, periódico/editora, páginas, DOI); **B** = verificação da afirmação que o artigo atribui à obra. Nada aqui foi inventado: onde o texto não foi lido, está escrito.

## A. Verificação bibliográfica

| Obra | Fonte consultada | Resultado |
|---|---|---|
| Kirkpatrick, Gelatt, Vecchi (1983). *Science* 220(4598), 671–680 | Crossref (API) e cópia do PDF do artigo | Confere com o `.bib` (autor "S. Kirkpatrick Jr." no Crossref; o `.bib` usa "S."; a ABNT do PDF mostra "KIRKPATRICK, S."). |
| Toth & Vigo (eds.) (2002). *The Vehicle Routing Problem*. SIAM | Crossref (DOI 10.1137/1.9780898718515) | Título, editores, editora, ano e ISBN conferem. Página da editora respondeu 403. |
| Banks, Carson, Nelson, Nicol (2010). *Discrete-Event System Simulation*, 5ª ed. | Catálogo da Pearson e registros de biblioteca (busca web) | 5ª edição, © 2010 (publicada em 2009), ISBN 978-0-13-606212-7 / 0-13-606212-1; imprint Prentice Hall. Folha de rosto **não** consultada. |
| Pavone, Smith, Frazzoli, Rus (2012). *IJRR* 31(7), 839–854 | Crossref | Confere. |
| Kontou, Garikapati, Hou (2020). *Transp. Res. C* 121, art. 102826 | Crossref e registro OSTI | Confere (art. 102826, sem páginas). |
| Pouls, Ahuja, Glock, Meyer (2025). *Ann. Oper. Res.* 350(1), 235–268 | Crossref | Confere (publicado online em 2022; fascículo de jul/2025). |
| Cormen et al. | — | **Removido do artigo e do `.bib`.** A edição consultada nunca foi identificada e nenhum trecho foi lido; a conciliação título/ano/editora entre edições (inglesa e brasileira) não pôde ser feita. |

## B. Obra × afirmação × evidência

| Obra | Afirmação no artigo | Seção | Evidência consultada | Situação |
|---|---|---|---|---|
| Kirkpatrick et al. 1983 | Recozimento simulado aceita piora temporária da solução corrente, diferente de guardar a melhor encontrada | 2.4 | Texto do artigo (cópia em PDF): "The case ΔE > 0 is treated probabilistically: the probability P(ΔE) = exp(−ΔE/kBT)" (critério de Metropolis). Página não anotada (colunas embaralhadas na extração) | B verificada no texto, sem página |
| Toth & Vigo 2002 | O VRP constrói rotas completas | 2.1 | Apenas título, ISBN e escopo do livro (catálogo); capítulos não consultados | Restrita a definição geral do VRP; o apoio das variantes (coleta e entrega, *dial-a-ride*) foi **movido** para Cordeau & Laporte (2007) e Berbeglia et al. (2010) |
| Banks et al. 2010 | Estudo conduzido como simulação de eventos discretos | 3.1 | Catálogo e escopo do livro (simulação de eventos discretos); capítulo não consultado | Uso genérico (nome da técnica); B não verificada por trecho |
| Pavone et al. 2012 | Política de rebalanceamento em modelo fluido que minimiza o número de viagens de rebalanceamento, validada em simulação e em experimentos de hardware | 2.4 | Resumo (Crossref): "fluid model… minimizing the number of rebalancing trips… simulated… and in hardware experiments" | Sustentada pelo resumo; texto integral **não lido** |
| Kontou et al. 2020 | Reduções de 53 % a 82 % das milhas vazias por viagem (RideAustin e DiDi Chuxing), supondo estacionamento de curta duração sem restrição | 2.4 | Resumo (OSTI): "68%–82% and 53%–60% reduction of trip-level deadheading miles… assuming unconstrained short-term parking" | Sustentada pelo resumo; texto integral **não lido**. O "por viagem" corresponde a *trip-level* |
| Pouls et al. 2025 | Reposicionamento guiado por previsão: redução média de cerca de 3,5 p.p. na rejeição de pedidos e melhora das esperas, não de viagens vazias | 2.4 | Resumo (Crossref): "reduces request rejection rates by an average of 3.5 percentage points and improves customer waiting and ride times" | Sustentada pelo resumo; "não de viagens vazias" é leitura do artigo sobre o que o resumo relata (rejeição e tempos), sem texto integral |
| Pavone, Kontou, Pouls | Citados como exemplos de reposicionamento (introdução, 2.1) | 1, 2.1 | Os três resumos acima | Uso como exemplos de literatura, sem número |

## Auditoria de citações × bibliografia

- Chaves citadas no texto = entradas do `.bib` (22 após a remoção de Cormen); nenhuma entrada órfã, nenhuma duplicata.
- DOI e URL com formato conferido no `.bib`; o `bibtex` não emitiu avisos.
- O artigo declara, na Seção 2.4, que Pavone, Kontou e Pouls foram conferidos apenas nos resumos.
- Pendências remanescentes: texto integral dos três artigos de reposicionamento; capítulos de Toth & Vigo e Banks et al.; página do trecho de Kirkpatrick et al.
