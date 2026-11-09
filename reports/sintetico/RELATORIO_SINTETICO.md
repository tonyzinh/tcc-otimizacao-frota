# Relatório do experimento sintético (Grande Vitória) — 08/11/2026

Evidência: execução da avaliação reservada (sementes 9001–9040, 22 cenários, 880 pares) com a configuração congelada em `docs/PLANO_EXPERIMENTO_SINTETICO.md` §9 (hash da matriz `716adc2e…ad63`). Dados: `reports/sintetico/avaliacao/` (resultados por par, dados sintéticos em Parquet, `manifesto.json`, `parametros.csv`, `analise/`). Reprodução: `python scripts/executar_sintetico.py --fase avaliacao` e `python scripts/analisar_sintetico.py --entrada reports/sintetico/avaliacao`. Nível de evidência: **executado**; reproduzível dado o snapshot geográfico (SHA-256 no manifesto). Árvore de código com alterações não commitadas (`arvore_suja: true`; sem commit por instrução).

## Resultado

Nas condições sintéticas especificadas, o guloso **não** apresentou redução de km vazio em relação à espera no destino em nenhum dos 22 cenários: 21 foram `piora` (IC95% da diferença pareada inteiramente acima de 0) e 1 (`S3_res6`) `sem_diferenca_detectavel` (+6,8 km, IC −2,8 a +16,7). A conclusão vale só para este gerador e esta geografia.

| Cenário principal | km vazio A (médio) | Δ km (B−A) | IC95% | Δ % | frequência de melhora |
|---|---|---|---|---|---|
| S1 uniforme | 2.308 | +48,9 | 36,9 a 61,2 | +2,1 | 10% |
| S2 concentrada e previsível | 2.313 | +69,0 | 47,2 a 90,5 | +3,0 | 10% |
| S3 frota desequilibrada | 2.127 | +37,8 | 17,9 a 57,6 | +1,8 | 28% |
| S4 mudança inesperada | 2.519 | +59,3 | 35,7 a 82,5 | +2,4 | 22% |
| S5 demanda móvel | 2.385 | +67,3 | 42,0 a 93,3 | +2,8 | 20% |

Frota/demanda (S2 e S3 com 4/8/14 pedidos por veículo): piora em todas (+21 a +70 km). Salto máximo: 6 km (+152/+197) e 10 km (+176/+461 km, até +21%) piora de forma monotônica. Resolução H3: r8 piora mais (+85/+69), r6 menos (+28/+7). Previsão perfeita (diagnóstico idealizado) e erro controlado também pioram. A tabela completa está em `analise/resumo_por_cenario.md`. Atendimento: razão B/A de atendidos entre 1,00 e 1,11 e P90 de espera entre 0,98 e 1,01 (preservado por definição prévia em 21 de 22; o critério não importa, pois não houve redução).

## Mecanismo (inspeção; `scripts/inspecionar_mecanismo_sintetico.py`)

- O reposicionamento planejado é igual ao simulado (ex.: S2/101: 49,3 km) e todos os movimentos planejados são executados: não há erro de contabilidade.
- Em média 13–58 movimentos e 5–356 km de reposicionamento por dia; o km de busca varia de −9 a +105 km (positivo quando B atende mais corridas, p.ex. S3 com salto de 10 km: razão 1,11).
- O objetivo do guloso é cobertura esperada − α·km, não km vazio: ele troca km por atendimento esperado. A economia de busca (até ≈ 10 km) não paga o custo de mover (≈ 30–60 km). **Hipótese** (não testada por ablação): o desalinhamento objetivo×desfecho explica o resultado.
- Limitações do guloso observadas como indícios, não demonstradas isoladamente: dependência da previsão (previsão perfeita não resolve), sensibilidade à agregação e ao salto, decisão única sem revisão. Ordem de processamento, excesso de veículos por zona e perda de cobertura na origem **não foram investigados** com exemplos pequenos nesta rodada.

## Limites

Geografia pública (IBGE, OSM); demanda, frota, velocidade (25 km/h), jornada e destinos são hipóteses; frota homogênea; retorno e outros vazios não modelados; só pontos de parada por célula H3 r8; um recorte de 20 km do Centro de Vitória; sem validade externa demonstrada; sem relação com a operação real da V1 Viagens. Sem correção formal de múltiplas comparações; as sensibilidades não são hipóteses independentes. Não houve piloto de sensibilidade além do que consta no plano.

## Proposta de adequação do TCC (apenas proposta; não aplicada)

- **Título:** Avaliação de um algoritmo guloso de reposicionamento de frota em cenários sintéticos na Grande Vitória.
- **Problema:** frotas que aguardam solicitações percorrem km sem passageiros; reposicionar preventivamente pode reduzi-los ou apenas deslocar o custo.
- **Pergunta:** em quais condições de distribuição espacial e temporal da demanda um guloso de reposicionamento preventivo reduz o km sem passageiros em uma frota simulada, em relação à espera no destino?
- **Objetivo:** caracterizar, em cenários sintéticos reproduzíveis, quando o guloso reduz, não altera ou piora o km vazio, e por qual mecanismo.
- **Hipóteses (declaradas antes):** H1 o guloso reduz o km vazio em demanda concentrada e previsível; H2 não reduz com demanda uniforme; H3 piora com mudança inesperada. **Resultado:** H1 e H3 sem suporte além de piora geral; H2 compatível (piora também). Registrar como resultado negativo.
- **Metodologia:** §§1–7 de `docs/PLANO_EXPERIMENTO_SINTETICO.md`. **Resultados:** esta tabela. **Limitações:** acima. Explicar que a geografia é pública, a operação é sintética e a validade externa não foi demonstrada.
