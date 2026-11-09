# Plano das análises pós-hoc do parecer (escrito em 09/11/2026, antes de executá-las)

Todas as análises abaixo são **pós-hoc**: foram definidas depois de conhecidos os resultados congelados de setembro e outubro, em
resposta ao parecer. Não substituem nem alteram o experimento congelado (`reports/atribuicao_final/`, `reports/sintetico_v2/`), cujos
números, critérios e classes permanecem como registrados. Autorização do proprietário para ler os dados privados locais nesta rodada:
dada em 09/11/2026, restrita a estas análises, processamento local, saídas só agregadas nesta pasta.

Entradas: os mundos (pedidos, motoristas, jornadas, compromissos) dos dias reais são lidos do cache da execução congelada
(`reports/runs/cache_comparacao/mundo_<dia>_d5cb1289caea.pkl`, mesmo hash do código do mundo registrado no manifesto congelado). As
variantes de disponibilidade reconstroem o mundo pelo código atual a partir dos Parquet locais.

## P1. Validação de componentes (sem ajuste de parâmetro)

Períodos: treino (01/02–15/03), validação (16–31/03), setembro (16–30/09), outubro (01–25/10). Pedidos de tempo real, como no estudo.
- Desfechos observados por período (`tx_status`) e fração de pedidos com corrida encerrada ou aceita, ao lado da fração atendida simulada em A.
- Distância de aproximação observada (`nu_distancia_aceite_cheguei`, m) nas corridas encerradas: n, nulos, mediana, P25, P75, média aparada (5%).
- Fator rua/reta e velocidade de aproximação observados no registro de ofertas: para instantâneos com `codigo_solicitacao` e passageiro
  não embarcado, razão `distancia_restante` / distância em linha reta até a origem do pedido (mesmo instante) e velocidade entre
  instantâneos consecutivos do mesmo pedido (queda de `distancia_restante` / intervalo). Filtros fixados agora: linha reta ≥ 0,3 km;
  razão em [0,8; 5]; intervalo entre 60 e 300 s; velocidade em (0; 120] km/h.
- Duração das viagens: é **entrada observada** do simulador (realizada, senão mediana do dia); não é componente modelado.
- Comparação com o simulado: distância de aproximação por atendido e espera em A (mesmo período). Populações diferentes (política e
  conjunto de atendidos diferentes); a diferença não é tratada como prova isolada de erro.

## P2. Disponibilidade

- Contagens por dia: motoristas no registro de ofertas, jornadas registradas (usadas e descartadas por motivo), motoristas simulados,
  motoristas distintos com corrida encerrada.
- Sensibilidade (setembro e outubro, todos os dias, A/B/C): (a) cenário E (só evidência do registro de ofertas, sem jornada);
  (b) cenário J com ponte de lacunas de 600 s e de 2.400 s (padrão 1.200 s); (c) redução determinística de 20% dos motoristas
  (exclui os motoristas com `int(SHA-256(identificador pseudonimizado), 16) % 5 == 0`: escolha por hash, não por resultado). Nenhum veículo é inventado; expansão artificial da oferta não é feita.

## P3. Distância, tempo e parâmetros

Setembro e outubro, todos os dias, A/B/C, um parâmetro por vez: fator 1,2 e 1,6; velocidade −25% e +25%; raio 3,5 e 5,5 km;
paciência 120 e 300 s. Distâncias viárias em subconjunto fixado por calendário (01, 08, 15 e 22/10): avaliar viabilidade com a rede OSM do
recorte sintético; executar só se a rede cobrir os pedidos e motoristas desses dias, senão registrar o motivo.

## P4. Sintético

- Verificar, por semente, se as variantes têm pedidos e frota idênticos ao cenário base (assinatura das entradas) e se os resultados de A,
  B e C coincidem.
- Apresentar as cinco famílias principais com dispersão entre sementes (mediana, P10, P90, mínimo e máximo de Δ% C×A e C×B).

## P5. Nova variante D (guloso global) e grade de janelas

- D: em cada lote, ordenar todos os pares elegíveis por (distância, chegada do pedido, id do pedido, id do motorista) e aceitar um par
  quando pedido e motorista ainda estão livres. Mesmas restrições, pedidos, veículos e janela que C.
- D×C com janela de 60 s: treino (desenvolvimento), setembro e outubro (diagnóstico, sem seleção). Reporta km, atendidos e espera.
- Grade de janelas {30, 60, 120} s para B, C e D **só no treino** (01/02–15/03). Nenhuma janela é escolhida ou reavaliada em
  setembro/outubro com base nesta grade.

## P6. Estatística

Tabela diária pareada (km e atendidos) de C×A e C×B em setembro e outubro, a partir dos resultados congelados; contagem de sinais;
sensibilidade do intervalo ao tamanho do bloco (3, 5 e 7 dias) só como descrição. Não se define margem de não inferioridade: não há
justificativa externa ou operacional documentada.

## P7. Significado prático e justiça

Setembro e outubro, A/B/C (reexecução sobre os mundos congelados; confere-se a igualdade com os números congelados): km economizado por
dia; km vazio sobre km total modelado (aproximação + trecho com passageiro dos atendidos, mesmo método de distância); comprimento médio
das viagens; P95, P99 e máximo da espera (entre atendidos); pedidos expirados; e, para B e C, pedidos que tiveram ao menos um lote com
veículo elegível e ainda assim expiraram (preteridos), e número de lotes em que cada pedido foi preterido.
