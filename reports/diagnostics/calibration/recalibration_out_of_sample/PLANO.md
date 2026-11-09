# Rodada 5: plano (escrito em 09/11/2026, 15:03 -03:00, antes de qualquer extração nova ou simulação de período novo)

Tudo nesta rodada é **análise posterior aos resultados congelados**. Os 120 resultados (dia × política) de setembro e outubro, os critérios E1–E3 e
os manifestos congelados não são alterados nem substituídos. Código: `3e65f3b` + alterações não commitadas (registradas por hash no congelamento).
Autorização: dados reais liberados pelo proprietário **só para esta rodada** (09/11/2026), leitura somente leitura, processamento local, saídas
agregadas nesta pasta. Nada individual (identificador, coordenada, registro) sai daqui.

## 0. Inventário (item 1), feito antes deste plano

`python scripts/pos_hoc_rodada5.py inventario`: só contagens por dia (SQL e ES). Saídas: `inventario_por_dia.csv`, `inventario_por_mes.csv`.

- Solicitações, jornadas e posições existem em todos os dias de 01/01 a 08/11/2026.
- Registro de posições: ~720 instantes por dia (um a cada 2 min) em **todos** os meses, inclusive fev, mar, set e out. A cobertura do registro é
  comparável; nenhum mês é excluído da calibração por cobertura (critério: média < 600 instantes/dia).
- A operação muda ao longo do ano, e isso é operação, não cobertura: pedidos em tempo real por dia 1.006 (jan), 1.199 (fev), 1.249 (mar),
  1.248 (abr), 1.195 (mai), 1.135 (jun), 980 (jul), 946 (ago), 1.042 (set), 874 (out). Motoristas por dia no registro de ofertas:
  102, 104, 107, 96, 89, 85, 77, 91, 85, 72.
- **Quebra em 31/10**: de 26 a 30/10 os volumes são como os de outubro (611–960 pedidos em tempo real e 65–85 motoristas no registro de ofertas
  por dia); de 31/10 a 08/11, 149–395 pedidos e 25–68 motoristas por dia. A quebra foi vista no inventário, antes de qualquer simulação.

## 1. Extração (item 2)

Entidades `ods/solicitacao`, `ods/status_solicitacao`, `ods/jornada_motorista`, `ods/veiculo_condutor`, `ods/compromissos_externos` e
`es/posicao_ofertas`, de 01/01 a 31/08/2026 e de 26/10 a 08/11/2026, com o extrator existente (somente leitura, HMAC-SHA256 com a mesma chave,
manifesto e SHA-256 por dia). Lotes já existentes **não** são regravados (sem `--forcar`), de modo que nenhum dado usado no congelamento muda.

Cadastro de veículos: **continua a fotografia de 08/11/2026** (a extração de hoje seria um dia depois e não traz o passado). Para jan–ago a
fotografia é posterior aos dias; veículos que saíram do cadastro não têm placa, e o compromisso correspondente fica "não atribuído" (contado).

## 2. Calibração (item 3), sem setembro nem outubro

Dias de calibração: todos os dias elegíveis de 01/01 a 31/08/2026 (regra (a) do artigo: entidades presentes, ≥ 300 instantes de posição,
≥ 200 pedidos em tempo real). Setembro, outubro e 26/10–08/11 **não** entram.

Medidas diretas (mesma construção da calibração de março, `v2/experiment.py::measured_parameters`, adaptada às entidades atuais):

- **Velocidade de aproximação**: distância aceite–chegada registrada (`NU_DISTANCIA_ACEITE_CHEGUEI`) ÷ (instante `CondutorChegou` −
  instante `CondutorACaminho`), corridas encerradas em tempo real, tempo ≥ 60 s e distância > 0,2 km. Mediana.
- **Fator rua/reta da aproximação**: a mesma distância ÷ linha reta entre a última posição do motorista no registro de ofertas até o aceite
  (no máximo 600 s antes) e a origem; linha reta ≥ 0,5 km. Mediana. (A ligação motorista ES × SQL usa o mesmo pseudônimo; conferido em 10/03:
  664 de 664 iguais.) A origem está arredondada a 3 casas (~110 m) pela regra de privacidade; declarado.
- Reporta n, mediana, quartis e P10/P90.

Ajuste de raio e paciência (mesmo critério da calibração original, `calibrate_simulator`): política A, grade de raio {2, 3, 4, 4,5, 5, 6, 8} km
× paciência {60, 90, 120, 180, 240} s, perda = (erro relativo do atendimento simulado contra o aceite observado)² + (erro relativo da espera
mediana simulada contra a busca mediana observada)²; desempate pelo menor raio e depois pela menor paciência.
- Aceite observado = fração dos pedidos em tempo real do dia com evento `CondutorACaminho`.
- Busca observada = mediana de (instante `CondutorChegou` − registro) nas corridas encerradas.
- **Desvio declarado**: a calibração original usou a janela 04–11 h; aqui usa-se o dia inteiro, que é a janela avaliada no experimento atual.

Modelo de aceite (opcional, **descritivo**): regressão logística do aceite em função da distância em linha reta até o motorista mais próximo
no registro de ofertas no instante do pedido (última posição em até 300 s) e da hora (faixas de 4 h), jan–ago. Não entra no simulador
(entrar mudaria o modelo de despacho, o que seria uma variante nova). Se a distância não puder ser montada para a maioria dos pedidos, dizer.

**Congelamento**: `calibracao_congelada.json` com parâmetros, n, dias usados, hash SHA-256 deste plano, do script e do código do simulador,
data e hora, e a frase "setembro, outubro e 26/10–08/11 não foram usados". Nenhuma simulação dos itens 3(a)–(c) roda antes dele; o script
recusa rodar sem o arquivo congelado.

## 3. Simulações (item 4), com os parâmetros congelados

Políticas A, B, C e a variante D (guloso global), janela de 60 s, mesmo motor e mesmo cenário J de disponibilidade.

(a) **Teste fora da amostra, 26/10–08/11** (resultado destacado): todos os dias elegíveis pela regra (a). Pelo inventário, 01/11 e 08/11
devem ficar fora por terem menos de 200 pedidos; a regra é aplicada aos dados extraídos, não ao inventário. Relato: total do período e dois
subperíodos fixados agora pela quebra vista no inventário: 26–30/10 e 31/10–08/11.

(b) Setembro e outubro com a calibração nova (rotulado como posterior), lado a lado com os resultados congelados.

(c) Corte mês a mês: para m de fevereiro a agosto, calibrar (medidas + grade) com os meses de janeiro a m − 1 e simular m com A, B e C.

## 4. Métricas (item 5)

- Tabela simulado × observado (aceite, aproximação, espera, motoristas) por período, com a calibração de março e com a nova.
- Efeitos C×A e C×B: total do período em %, ΔN, e IC95% da diferença média diária (t pareado e *bootstrap* de blocos circulares de 7 dias,
  10.000 reamostragens, semente 20261108). Para as variantes de sensibilidade da rodada 4, os mesmos intervalos a partir dos CSV por dia.
- Atendimento por dia em todos os períodos; contagem de variantes em que C atende mais ou menos que A.
- Fração do km total modelado (vazio + com passageiro) que é km vazio, em A e em C, e a redução de C×A em pontos percentuais do km total.
- E1–E3 (definições congeladas) nos períodos novos, como descrição.

## 5. Regras

Execução inválida (exceção, dado ausente) é registrada e contada. Nenhuma simulação é repetida mudando parâmetro para "melhorar" o resultado.
Toda decisão tomada depois de ver resultados vai para a seção "Decisões posteriores" de `RELATORIO.md`, com data.
