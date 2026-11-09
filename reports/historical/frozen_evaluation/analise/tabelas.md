# Atribuição: resultados por período (gerado por `scripts/analisar_atribuicao_final.py`)


## Replicação 16–30/09/2026

### Valores absolutos por política (km vazio = busca; sem reposicionamento nesta linha)

| politica | dias | pedidos_elegiveis | atendidos | nao_atendidos | atendimento_pct | km_vazio_total | km_vazio_por_atendido | espera_media_s | espera_p90_s | violacoes_compromisso_por_politica | compromissos_entrada_inconsistente | tempo_computacional_total_s | tempo_computacional_por_dia_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A · mais próximo livre, despacho imediato | 15 | 16918 | 11125 | 5793 | 65.76 | 29,628.27 | 2.66 | 616.40 | 1,183.18 | 0 | 19 | 0.96 | 0.06 |
| B · mais próximo livre, lotes de 60 s | 15 | 16918 | 10950 | 5968 | 64.72 | 28,644.91 | 2.62 | 630.60 | 1,195.75 | 0 | 19 | 1.37 | 0.09 |
| C · atribuição conjunta (húngaro), lotes de 60 s | 15 | 16918 | 11141 | 5777 | 65.85 | 27,861.14 | 2.50 | 600.75 | 1,171.55 | 0 | 19 | 1.87 | 0.12 |

### Contrastes (variação de km vazio: negativo = redução; contraste principal = C × A)

| contraste | papel | dias | variacao_km_vazio_km (negativo = reducao) | variacao_km_vazio_pct (negativo = reducao) | diferenca_media_diaria_km | ic95_diferenca_media_diaria_km | dias_com_melhora | dias_com_piora | dias_iguais | diferenca_atendidos | diferenca_atendimento_pontos_percentuais | ic95_diferenca_media_diaria_atendidos | diferenca_nao_atendidos | diferenca_espera_media_s | diferenca_espera_p90_s | E1_sem_violacoes | E2_atendimento_preservado | E3_p90_nao_piorou | servico_preservado | classe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C × A | PRINCIPAL | 15 | -1,767.13 | -5.96 | -117.81 | (-132.97; -102.86) | 14 | 1 | 0 | 16 | 0.09 | (-6.20; 8.00) | -16 | -15.65 | -11.63 | True | True | True | True | reducao_com_servico_preservado |
| C × B | complementar | 15 | -783.77 | -2.74 | -52.25 | (-61.19; -43.10) | 14 | 1 | 0 | 191 | 1.13 | (6.80; 18.33) | -191 | -29.86 | -24.20 | True | True | True | True | reducao_com_servico_preservado |
| B × A | complementar | 15 | -983.36 | -3.32 | -65.56 | (-76.13; -54.79) | 14 | 1 | 0 | -175 | -1.03 | (-16.93; -6.53) | 175 | 14.21 | 12.58 | True | False | False | False | reducao_sem_servico_preservado |

## Avaliação final 01–25/10/2026

### Valores absolutos por política (km vazio = busca; sem reposicionamento nesta linha)

| politica | dias | pedidos_elegiveis | atendidos | nao_atendidos | atendimento_pct | km_vazio_total | km_vazio_por_atendido | espera_media_s | espera_p90_s | violacoes_compromisso_por_politica | compromissos_entrada_inconsistente | tempo_computacional_total_s | tempo_computacional_por_dia_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A · mais próximo livre, despacho imediato | 25 | 23523 | 14551 | 8972 | 61.86 | 39,205.01 | 2.69 | 620.98 | 1,189.68 | 0 | 17 | 1.27 | 0.05 |
| B · mais próximo livre, lotes de 60 s | 25 | 23523 | 14317 | 9206 | 60.86 | 37,756.74 | 2.64 | 633.38 | 1,201.45 | 0 | 17 | 2.00 | 0.08 |
| C · atribuição conjunta (húngaro), lotes de 60 s | 25 | 23523 | 14466 | 9057 | 61.50 | 37,228.72 | 2.57 | 615.81 | 1,181.70 | 0 | 17 | 2.57 | 0.10 |

### Contrastes (variação de km vazio: negativo = redução; contraste principal = C × A)

| contraste | papel | dias | variacao_km_vazio_km (negativo = reducao) | variacao_km_vazio_pct (negativo = reducao) | diferenca_media_diaria_km | ic95_diferenca_media_diaria_km | dias_com_melhora | dias_com_piora | dias_iguais | diferenca_atendidos | diferenca_atendimento_pontos_percentuais | ic95_diferenca_media_diaria_atendidos | diferenca_nao_atendidos | diferenca_espera_media_s | diferenca_espera_p90_s | E1_sem_violacoes | E2_atendimento_preservado | E3_p90_nao_piorou | servico_preservado | classe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C × A | PRINCIPAL | 25 | -1,976.29 | -5.04 | -79.05 | (-97.30; -62.79) | 25 | 0 | 0 | -85 | -0.36 | (-7.84; 0.88) | 85 | -5.17 | -7.98 | True | False | True | False | reducao_sem_servico_preservado |
| C × B | complementar | 25 | -528.02 | -1.40 | -21.12 | (-31.05; -11.50) | 16 | 9 | 0 | 149 | 0.63 | (1.52; 10.40) | -149 | -17.57 | -19.75 | True | True | True | True | reducao_com_servico_preservado |
| B × A | complementar | 25 | -1,448.27 | -3.69 | -57.93 | (-76.99; -42.03) | 25 | 0 | 0 | -234 | -0.99 | (-13.04; -5.88) | 234 | 12.40 | 11.77 | True | False | False | False | reducao_sem_servico_preservado |