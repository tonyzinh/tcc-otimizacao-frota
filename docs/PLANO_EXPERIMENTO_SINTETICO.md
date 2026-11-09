# Plano do experimento sintético (Grande Vitória)

Origem: mudança de escopo de 08/11/2026 (`docs/REGISTRO_DECISOES.md`, R-23). Este plano vale para a fase sintética; os planos de extração e de comparação de vários algoritmos estão arquivados.

## 1. Pergunta e escopo

**Pergunta:** em quais condições de distribuição espacial e temporal da demanda um algoritmo guloso de reposicionamento preventivo reduz os quilômetros sem passageiros em uma frota simulada na Grande Vitória, em comparação com uma política de espera no destino?

- Só dados operacionais sintéticos. Geografia pública (IBGE, OpenStreetMap/ODbL); demanda, frota e jornadas são hipóteses experimentais. Nenhuma estatística de dado privado.
- Políticas: **A** espera no destino (sem reposicionamento); **B** guloso (`GulosoMarginal`, α=0,2, ρ=2,5 km, salto máximo do cenário) com previsão do histórico sintético, decisão única antes da operação (D+1), "não reposicionar" admitido, reposicionamento integralmente no custo. Mesmo despacho, raio e regra de espera em A e B.
- Fora de escopo: outros algoritmos, otimização em tempo real, dados reais, reposicionamento contínuo.

## 2. Geografia

Municípios: Vitória, Vila Velha, Serra, Cariacica (parte da Grande Vitória). Recorte operacional: pontos a ≤ 20 km por via (ida e volta) do Centro de Vitória. Pontos de parada = um nó de via por célula H3 r8 (≥ 20 nós, centro a ≤ 350 m de via), na maior componente fortemente conexa; distâncias = menor caminho pela rede (Dijkstra), sem linha reta sobre a água. Zonas de planejamento H3 r7 (sensibilidade: r6 e r8). Fontes, URLs, licenças e SHA-256: `data/geografia/manifesto_geografia.json` (gerado por `scripts/baixar_geografia.py`).

Limites assumidos: rede OSM como proxy de acessibilidade; sem sentido de tráfego dinâmico; velocidade constante.

## 3. Gerador e parâmetros

`src/tcc_frota/sintetico/gerador.py` (versão 1.0.0). Cada parâmetro com nome, unidade, valor, justificativa e classe (hipótese experimental ou informação geográfica) em `tabela_parametros`, exportada a cada execução em `parametros.csv`. Frota homogênea de 100 veículos, jornadas de 9 h iniciando em {6, 8, 10, 12} h, veículos parados onde terminaram a jornada anterior, escala de D+1 conhecida no corte. Previsão e realização são objetos separados (`previsao` ≠ `pedidos`); histórico de 28 dias gerado com canais de semente independentes do dia avaliado. κ (corridas/veículo-hora) é calibrado simulando a referência nos 3 últimos dias do histórico, não suposto.

## 4. Matriz de cenários (congelada)

Definida em `src/tcc_frota/sintetico/matriz.py` antes de qualquer resultado do guloso; hash da matriz + parâmetros operacionais + versão do gerador: ver §9. S1 uniforme; S2 concentrada e previsível; S3 frota inicialmente desequilibrada; S4 mudança inesperada de demanda; S5 demanda que migra de região ao longo do dia; S6 relação frota/demanda baixa/intermediária/alta (variantes `*_frota_abundante` e `*_frota_escassa` de S2 e S3, 4/8/14 pedidos por veículo). Sensibilidades: salto máximo 6 e 10 km; resolução H3 6 e 8; erro de previsão controlado (σ=0,5); previsão perfeita (**diagnóstico idealizado**, nunca resultado principal).

As concentrações são hipóteses sintéticas localizadas no mapa; não representam fluxos reais.

## 5. Contabilidade

KM vazio = busca (aproximação até o embarque) + reposicionamento. Retorno e outros vazios: não modelados (zero, declarado). Movimentos ocorrem no início da jornada do veículo e entram integralmente no custo, inclusive antes da primeira solicitação. Pedidos não atendidos no encerramento são contados como não atendidos; serviços em curso terminam sem truncar o custo (o simulador contabiliza a corrida iniciada). A e B têm a mesma assinatura de entrada (SHA-256), verificada a cada par.

## 6. Repetições e fases

| Fase | Sementes | Uso |
|---|---|---|
| Piloto | 1–5 | calibrar mundo (só a referência A) e dimensionar n |
| Desenvolvimento | 101–120 (20) | explorar, diagnosticar mecanismo, corrigir o guloso se houver erro |
| Avaliação | 9001–9040 (40, **reservadas**) | única rodada da configuração congelada |

Piloto (n=5): desvio-padrão do Δkm entre ≈ 37 e 82 km por execução; meia-largura do IC95% com n=40 ≈ 25 km (≈ 1% do km vazio de A). Sementes independentes; nenhuma escolhida. O comando `scripts/executar_sintetico.py --fase avaliacao` recusa rodar se o plano não contiver o hash da configuração (§9).

Cenário que parecer favorável só no desenvolvimento é **hipótese exploratória** e precisa se confirmar na avaliação reservada.

## 7. Métricas e regra de classificação

Principal: km vazio total (diferença pareada B − A por semente). Complementares: km de busca, de reposicionamento, atendidos (quantidade e proporção), espera média e P90, km por atendimento, tempo do algoritmo, movimentos planejados e executados.

**Atendimento preservado** (critério experimental, definido antes das execuções; não é SLA): razão média pareada de atendidos B/A ≥ 0,995 **e** P90 de espera médio de B ≤ 1,05 × o de A.

Classes por cenário (IC95% bootstrap sobre sementes, 10.000 reamostragens, semente 20261108):
- `reducao`: limite superior do IC < 0 e atendimento preservado.
- `reducao_com_perda`: limite superior < 0, atendimento não preservado (não conta como redução).
- `piora`: limite inferior > 0.
- `sem_diferenca_detectavel`: demais casos; reportar a meia-largura do IC (poder).

Relato: média, dp, IC, frequência de melhora e piora, por cenário (`scripts/analisar_sintetico.py`). Sem correção formal de múltiplas comparações entre os 5 cenários principais além de reportar todos; as variantes são sensibilidades, não hipóteses independentes.

## 8. Linguagem de conclusão

Permitido: "Nas condições sintéticas especificadas, o algoritmo apresentou (ou não) redução de km vazio em relação à referência." Proibido: concluir sobre a operação real da V1 Viagens.

## 9. Congelamento

Congelado em 08/11/2026, após o desenvolvimento (sementes 101–120, `reports/sintetico/desenvolvimento/`).

- Hash (matriz + parâmetros operacionais + versão do gerador): `716adc2ed3563281c50eb504c6d9a7d12790bef7369521fe5cdbb4b06957ad63` (igual ao do piloto: a matriz não foi alterada após ver resultados).
- Alterações no guloso após o desenvolvimento: **nenhuma**. O desenvolvimento não revelou erro de implementação: o km de reposicionamento planejado (`km_modelo`) coincide com o simulado (ex.: 49,3 km em S2/101), todos os movimentos planejados foram executados, A e B têm a mesma assinatura. Os resultados de desenvolvimento (B pior que A em 21 de 22 cenários; ver `analise/`) não motivaram ajuste de α, ρ, salto ou previsão: não se reexecuta variando algo até "dar certo".
- Mecanismo observado (desenvolvimento, exploratório): o reposicionamento custa ≈ 30–60 km por dia e a redução de km de busca é de apenas ≈ 0–9 km; o objetivo do guloso é cobertura esperada − α·km, não km vazio. Detalhes e limites em `docs/REGISTRO_DECISOES.md` (R-24).
- Próximo passo: rodar uma única vez `python scripts/executar_sintetico.py --fase avaliacao` (sementes 9001–9040).
