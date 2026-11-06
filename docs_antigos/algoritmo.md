# Modelo e algoritmo guloso

Para zona `r` e faixa `t`, `D(r,t)` é a média de pedidos históricos conhecidos no corte. Cada veículo elegível oferece capacidade experimental `q` por faixa. O proxy de pickup `P(x)` distribui a demanda aos veículos disponíveis por menor distância geodésica até cada zona, respeitando `q` e uma distância máxima experimental. A cobertura projetada é `C(x) = demanda atribuída / demanda prevista`.

O plano busca reduzir `J(x) = P(x) + R(x) + T(x)`, em quilômetros vazios **estimados**, sob `C(x) >= C_min`, `C(x) >= C(x_base)`, disponibilidade, compromissos e limites de movimento. `R` é reposicionamento; `T` seria retorno obrigatório validado, ausente neste MVP. `C_min` é parâmetro de sensibilidade, não SLA empresarial. A simulação calcula o resultado realizado **dentro do mundo sintético**, que continua distância estimada, e pode discordar da proxy de planejamento.

```text
iniciar posições e cobertura projetada do plano sem movimentos
enquanto houver veículo ainda não movido:
    enumerar pares elegíveis (veículo, zona)
    descartar movimento além do limite ou conflitante com jornada/compromisso
    recalcular pickup projetado e cobertura após cada candidato
    descartar candidato que reduza cobertura ou viole C_min
    escolher maior redução positiva de (pickup projetado + reposicionamento)
    em empate, escolher (ID do veículo, ID da zona) em ordem lexical
    registrar movimento e atualizar posições projetadas
    parar se nenhum candidato reduzir o objetivo
```

Essa é uma heurística determinística, sem garantia de ótimo global. Não usa demanda observada D+1. `Position` e `Recommendation` mantêm posição e custo; a saída pública do relatório agrega movimentos por zonas. A escolha de `q`, distância máxima e `C_min` é experimental e não política da empresa. A malha espacial simples está em `spatial/grid.py`, ajustada só com treino; o exemplo usa três zonas sintéticas fixas para transparência.
