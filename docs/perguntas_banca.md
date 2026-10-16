# Perguntas prováveis da banca (com respostas curtas)

Baseadas na execução `20261016T013428Z` ([resultados reais](resultados_reais.md)). Todos os números são estimativas de simulação retrospectiva.

**1. O trabalho tinha como objetivo reduzir o KM morto e não conseguiu. Então o modelo falhou?**
O modelo foi avaliado com honestidade e a hipótese H1 foi rejeitada: em nenhuma configuração o KM vazio estimado por corrida caiu (+2,6% a +35,8% na janela principal). Isso é um resultado: pela desigualdade triangular, reposicionar só economiza quando cria atendimento ou corrige o despacho míope, e isso foi raro nos dados. O mesmo sinal apareceu em setembro na base antiga e na nova, com demanda total.

**2. Se o KM vazio sobe, para que serve o reposicionamento?**
Ele aumentou um pouco o atendimento (até +2,1% com o guloso intermediário e +2,9% com a regra de limiar em setembro, de 1,6 a 2,3 corridas por dia) e reduziu o tempo até o passageiro (cerca de 10 s). Se isso vale a pena depende da margem por corrida e do custo por km, que não temos. Por isso a resposta é apresentada como ponto de equilíbrio (margem > e × custo/km).

**3. Por que o exploratório deu +8% de corridas e o resultado final, no máximo, +3%?**
O desenho final é mais estrito: a recomendação só é executada na primeira disponibilidade do motorista e dentro do limite de distância; as posições são as conhecidas no corte; corridas agendadas ocupam a frota; a paciência foi calibrada pelos tempos reais (o sistema declara `NaoAtendida` com cerca de 113 s). O sinal é o mesmo; a magnitude é menor e mais defensável.

**4. O baseline é simulado. Como saber se ele representa a operação?**
Ele foi calibrado nos dias 2–15 de cada mês para reproduzir o aceite e o tempo de busca observados. Na janela principal, fica de 1,4 a 4,6 p.p. acima do aceite real, e o tempo mediano até o passageiro (564–576 s) está perto da busca observada (595–604 s). A comparação é sempre preventivo × baseline simulado, com os mesmos pedidos, frota e distância (assinatura SHA-256 conferida); nunca preventivo × histórico.

**5. Os parâmetros não foram ajustados até aparecer ganho?**
Não. As grades e o critério de escolha foram registrados antes do teste (DT014), e a escolha usou só os dias de calibração de março. A grade inteira de α aparece no teste, e setembro usou os parâmetros congelados de março. Houve uma única correção depois da primeira execução: o regime B passou a usar a última posição de D, como estava especificado (DT015). As duas versões estão reportadas e dão resultados da mesma ordem.

**6. Haversine não é distância real. Isso não invalida tudo?**
A distância é Haversine × fator rua/reta medido nos próprios dados (1,30–1,38 na busca, n = 369–466 por período; 1,48–1,50 nas viagens, n > 6 mil). A sensibilidade de 1,2 a 1,6 muda a magnitude, mas o KM vazio por corrida sobe em todos os casos. Os valores são estimativas e assim são rotulados; não são odômetro.

**7. Saber a escala do dia seguinte (regime B) é realista?**
Depende da empresa: é uma DECISÃO DO ALUNO, a confirmar. Com a escala prevista às 20h (regime A), a previsão acerta 61–66% dos motoristas, só um quarto das recomendações é executado e o ganho em corridas desaparece. O trabalho deixa explícito que o efeito só existe se a escala for conhecida.

**8. Por que a previsão escolhida é uma simples média? Não seria melhor um modelo de aprendizado de máquina?**
A média do mesmo dia da semana teve o menor WAPE por zona-hora na calibração (0,967 contra 1,010 da Poisson e 1,082 da naïve). No teste de março, também teve o menor erro do total da janela (12,9%). Trocar pela Poisson na sensibilidade não muda o resultado do reposicionamento. Modelos mais pesados ficam como trabalho futuro: o gargalo não é a previsão.

**9. Com 15–16 dias de teste por mês, dá para concluir alguma coisa?**
Dá para afirmar o que é consistente entre os meses, regimes e sensibilidades: KM vazio por corrida maior em toda configuração que reposiciona, e ganho de corridas pequeno. Os IC (bootstrap de dias) e os p-valores (permutação exata) estão em todas as tabelas. O ganho do guloso em março não é significativo, e o texto diz isso.

**10. O que a empresa deveria fazer com esse resultado?**
Não usar o reposicionamento preventivo para reduzir KM. Se o objetivo for atendimento na rampa matinal, testar em campo uma regra simples (proporcional ou guloso conservador) com escala conhecida, medir KM e corridas com dados reais e decidir com o próprio custo por km e margem por corrida. A perda no pico das 17–19h não parece ser de posicionamento (55% das não aceitas tinham motorista livre a até 2 km) e pede outra investigação.
