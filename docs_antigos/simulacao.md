# Simulador de eventos discretos

`simulation/engine.py` ordena eventos por `(timestamp, prioridade, sequência)`: liberação antes de compromissos, e ambos antes de novos pedidos. Eventos implementados: início de disponibilidade, começo/fim de compromisso externo, início/fim de reposicionamento, pedido, atribuição, chegada ao pickup, início/fim da viagem e pedido não atendido. Eventos simultâneos têm desempate determinístico.

Um veículo passa por INDISPONIVEL, LIVRE, REPOSICIONANDO, INDO_BUSCAR_PASSAGEIRO e EM_VIAGEM. A atribuição ocupa o carro antes de chegar ao passageiro. O término libera na posição de destino somente se a jornada ainda vigora. Compromisso externo bloqueia o carro entre início e fim; sem posição final conhecida, ele permanece indisponível depois. O simulador rejeita compromissos sobrepostos e reposições impossíveis.

O despacho simplificado escolhe o veículo livre mais próximo cuja viagem termina antes do fim da jornada e do próximo compromisso. Não há fila de espera nem reotimização do plano. Esse comportamento é **uma hipótese de baseline**, não reprodução comprovada da empresa. A assinatura SHA-256 das entradas e da configuração impede comparar replays com condições iniciais diferentes. Os mesmos pedidos são usados em ambos os cenários; posições posteriores são consequência da estratégia em cada replay.

Distâncias de pickup e reposicionamento são Haversine em linha reta. Tempo é calculado por velocidade constante experimental. Trânsito, recusa, cancelamento e mudança de demanda pela intervenção não são modelados. Corridas que atravessam a meia-noite permanecem ocupadas até o fim.
