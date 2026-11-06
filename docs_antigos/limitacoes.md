# Limitações e ameaças à validade

**Atualizado em 16/10/2026 (rodada v2).** Toda conclusão se restringe ao comportamento do modelo nos períodos e premissas descritos em [resultados reais](resultados_reais.md). Um resultado nulo ou adverso deve ser mantido.

## Construto

1. **KM morto:** a definição corporativa segue pendente (DT003/RN010). Nesta rodada, KM vazio = busca + reposicionamento, como distância por rua **estimada** (Haversine × fator rua/reta calibrado). O retorno não é medido. Não é odômetro nem rota (RN012).
2. **Atendimento:** "corrida atendida" no simulador = pedido despachado a um motorista. O alvo observado de calibração é o aceite. Cancelamentos pós-aceite só entram na sensibilidade.
3. **Custo:** nenhum custo por km ou margem por corrida foi fornecido. O ponto de equilíbrio é apresentado como função desses valores, não como número.

## Dados

4. **Períodos:** dois meses (março e setembro/2026), uma região, 14 dias de calibração e 15–16 dias de teste por mês. Sazonalidade anual e eventos não estão cobertos.
5. **Frota:** fotos a cada 10 min. A posição no aceite e as sessões herdam essa resolução, e o enum de estados é inferido (DT010).
6. **Status:** o tratamento de cada status (RN004) é decisão do estudo, não homologação da empresa. `nU_DR_REAL` e `tX_H3INDEX_REPOSICIONAMENTO_REAL` têm semântica pendente e não foram usados.
7. **Caixa geográfica:** a Grande Vitória é aproximada por um retângulo (RN002 pendente).

## Simulação e contrafactual

8. **Baseline simulado:** despacho do motorista livre mais próximo dentro de um raio, com fila e paciência calibrados para reproduzir o aceite e a busca observados. É simplificação declarada (RN021), não a política real; o ajuste não é perfeito (ver tabela de ajuste do baseline).
9. **Velocidade e rotas:** velocidade constante e fator rua/reta único; sem trânsito por hora. A sensibilidade varia um parâmetro por vez.
10. **Comportamento:** demanda, adesão dos motoristas e tráfego não reagem à intervenção. A execução das recomendações segue regra fixa (DT014/DT015).
11. **Trajeto entre corridas:** motoristas ociosos ficam parados no simulador; na realidade, circulam.
12. **Destino e duração:** destino solicitado disponível para todos os pedidos; duração observada quando a corrida foi encerrada, senão estimada pela distância (fator e velocidade de viagem calibrados). A estimativa é idêntica entre cenários.

## Informação

13. **Regime B:** supõe escala conhecida para D+1 (a confirmar com a empresa) e usa a última posição de D, ou seja, o corte no fim de D. A primeira implementação usava posição às 20h e foi corrigida após a primeira execução (DT015); as duas variantes são reportadas.
14. **Regime C:** viola o corte e serve só como diagnóstico.

## Estatística

15. **Amostra:** com 15–16 dias pareados por período, os IC 95% por bootstrap de dias são largos para efeitos pequenos. O teste de permutação é exato até 16 dias. Não houve correção para comparações múltiplas; a leitura privilegia padrões consistentes entre períodos e regimes.
16. **Algoritmo:** o guloso não garante monotonicidade em α (DT014). A fronteira é empírica.

## Infraestrutura

17. **Databricks:** medalhão v2 executado e conferido no Free Edition em 15/10/2026. O sal da pseudonimização aparece no plano das consultas do workspace. Previsão e simulação rodam localmente.
