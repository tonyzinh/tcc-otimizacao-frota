# Parecer de orientação (28/10/2026)

Escopo: `TCC_REFORMULACAO.md`, `TCC_ESTRUTURA.md`, `TCC_BANCA_V2.md`, `V2_CONTABILIZACAO.md` e `RELATORIO_V2.md`. Não revisei o código nem rodei nada; todo número abaixo vem desses documentos.

## Veredito

O trabalho é defensável e tem mérito: pergunta falseável, desfecho justificado empiricamente (a razão KM/corrida sobe mesmo quando o atendimento melhora), controle positivo, placebo, correção de múltiplos testes e desvios datados. A mudança de "algoritmo que reduz KM morto" para "protocolo de avaliação + regra de decisão NB(e*)" é a correta. O que falta é **delimitar melhor o alcance da conclusão** e fechar cinco pontos que a banca vai atacar.

## A. Pontos críticos (resolver antes da entrega)

**A1. O resultado primário depende de uma premissa não verificada.**
A contabilização primária (`start_at_origin`, regime B) assume que, nos dois braços, o motorista começa na última posição de D. Nos dados, o motorista começa a sessão em média a 3,5 km (mar) e 5,6 km (set) dessa posição (`V2_CONTABILIZACAO.md`). A interpretação de m1/m2 é "minha, a confirmar" (D8, D10) e ainda não foi confirmada por você ou pela empresa.
*Ação:* confirmar a interpretação e, no texto, escrever que o nulo é **condicional à premissa do regime B**. O descarte de "pagar nos dois braços" como artefato está bem fundamentado (o placebo gera 18 de 100 "reduções"), mas deixe claro que isso descarta a contabilização, não resolve a pergunta de se o plano poderia reduzir o trecho que o motorista já faz sozinho.

**A2. A força da conclusão não é a mesma para os dois desfechos.**
- *Forte:* KM vazio por corrida **aumenta** (98 de 162 linhas na F1; 0 reduções).
- *Mais fraca:* "benefício líquido não demonstrado para e* ≤ 30". Com 15–16 dias de teste por mês, o protocolo tem poder de 32–58% para ΔN = 1% e não distingue 0,25–0,5%. Falta o MDE do **NB(e*)**, só existe o de ΔKM e ΔN.
*Ação:* calcular o MDE de NB(e*) e reescrever a Introdução e as Considerações finais: "aumento robusto de KM/corrida; benefício líquido não demonstrado para e* ≤ 30, com poder para ganhos de corridas a partir de ~1–2%". Evitar "nulo bem testado" sem esse recorte.

**A3. A premissa do problema não bate com o enunciado original.**
O projeto parte de frota própria ou controlada, em que o KM morto é custo direto da empresa. Os dados e documentos falam de motoristas que aceitam corridas, "conformidade" e "custo privado para o motorista" (`TCC_REFORMULACAO.md` §5). A banca perguntará de quem é o custo.
*Ação:* definir uma vez, na Introdução, quem paga o KM vazio e quem decide mover o veículo, e usar isso para justificar o parâmetro de conformidade e o e*.

**A4. Quais hipóteses foram registradas antes e quais foram escritas depois?**
H1′ e H2′ estão no registro `dc1057e`. H3′ (oráculo) e H4′ (controle) aparecem na reformulação, **depois** dos resultados, com "Observado" ao lado.
*Ação:* dizer isso na tabela de hipóteses (coluna "Origem: registro inicial / adicionada após resultados") e chamar H4′ de **critério de validação do simulador**, não de hipótese de pesquisa.

**A5. A F1 parece contradizer H1′ e o texto não explica.**
Na F1 há linhas com NB > 0 e IC inteiro positivo já em e* = 20 (3 linhas) e 30 (9); H1′ é dada como refutada para e* ≤ 30 com base na F4 (0 linhas). Quem ler só a F1 verá o contrário.
*Ação:* explicar em um parágrafo qual contabilização e qual baseline cada família usa e por que a F4 é a que responde a H1′ (a F1 usa a contabilização bruta da v1; confirmar que é essa a razão antes de escrever).

## B. Melhorias importantes

1. **"Proposta" fina.** Hoje é um checklist e uma regra. Acrescente uma **calculadora de decisão** (script ou notebook): dado e* e os agregados diários, devolve NB(e*) com IC e a decisão. Inclua um exemplo resolvido. Isso é a "solução" tangível.
2. **Bibliografia ausente na estrutura.** Use as fontes do projeto (dissertações de Pimentel 2025 e Krohling 2024, artigo de IA em roteirização) e cite com referência completa a fonte dos "53–82% menos deadheading". Hoje a discrepância com a literatura está no texto sem citação.
3. **Números de um único dia.** "B1 ≈ 875, B3 ≈ 1 700 km/dia, coleta ≈ 313 km" vem de um dia de teste. Troque por média e desvio dos dias de teste.
4. **Alcance no título e no resumo.** Declare: janela 04–11 h, dois meses, 15–16 dias de teste por mês, setembro como replicação parcial.
5. **Grade ρ × conformidade é descritiva (sem p-valores).** Diga isso onde ela aparecer e defina ρ e conformidade no capítulo de metodologia, com um exemplo.
6. **Carimbo do protocolo.** Os commits do registro são de 11:30 a 12:01 do mesmo dia, em Git local. Faça `git push` para o remoto agora e descreva como "registrado no Git antes da execução, sem carimbo externo".
7. **Banca, pergunta 10.** Acrescente: "os mesmos planejadores funcionam quando existe oportunidade (7 de 7 no controle positivo)". É a melhor resposta a "o problema não é o algoritmo?".
8. **Banca, pergunta 3.** Inclua o MDE do NB(e*) assim que existir.

## C. Menores

- Padronizar "KM vazio" (simulado) e "KM morto" (conceito) em todo o texto.
- No Capítulo 9, responder à pergunta com uma frase por hipótese (H1′ refutada para e* ≤ 30 na F4; H3′ refutada; H4′ não refutada).
- Registrar no apêndice a lista de desvios D1–D13 em tabela única (data, motivo, efeito sobre decisões).

## Prompt para aplicar as correções (colar no Claude Code)

```text
Branch v2-extensoes. Leia docs_antigos/TCC_PARECER_ORIENTADOR.md e aplique, em commits separados e sem alterar reports/tcc_final/:
1. Calcular o MDE de NB(e*) (e* em {5,10,20,30,50}) com o mesmo método de fase1_mde.csv; salvar em reports/tcc_v2/fase1_mde_nb.csv.
2. Verificar por que a F1 tem NB>0 em e*=20–30 e a F4 não (contabilização/baseline de cada família) e escrever o parágrafo explicativo em docs_antigos/TCC_REFORMULACAO.md §3.
3. Trocar os números de um único dia (B1, B3, coleta) por média e desvio dos dias de teste, citando o arquivo.
4. Atualizar TCC_REFORMULACAO.md: coluna "Origem" na tabela de hipóteses, H4' como critério de validação, premissa do regime B como condição do nulo, quem paga o KM vazio, alcance (janela, meses, dias).
5. Atualizar TCC_ESTRUTURA.md (capítulo 6 com a calculadora de decisão, bibliografia, grade descritiva) e TCC_BANCA_V2.md (perguntas 3 e 10).
6. Criar a calculadora de decisão (src/tcc_frota/v3/decisao.py + exemplo em docs/) que recebe e* e os agregados diários e devolve NB(e*), IC e a decisão; com testes.
7. Rodar python -m pytest e reportar. Não invente números; se um resultado contradisser os documentos, pare e reporte.
```
