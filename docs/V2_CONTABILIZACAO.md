# Contabilização de KM: correções m1 e m2 (v3)

Código: `src/tcc_frota/v3/sim.py` (`simulate3`). A v1 (`src/tcc_frota/v2/sim.py`) não foi alterada; com `fix_m1=False` e
`fix_m2=False` o `simulate3` reproduz a v1 bit a bit (`tests/unit/test_v3_sim.py`).

## m1: reposicionamento que passa do fim da sessão
No modo `inicio_turno` (regime A) a v1 executa o reposicionamento mesmo que o deslocamento termine depois do fim da sessão
do motorista, e conta todo o KM. Com `fix_m1`, o movimento só é executado se terminar dentro da sessão vigente; caso contrário o desfecho é
`excede_sessao` (não adesão). Isso reduz o KM de reposicionamento do plano. O regime B (`fim_do_dia`) não é afetado.

## m2: assimetria de posição noturna
No modo `fim_do_dia` (regime B, o principal) o motorista começa a sessão já na zona-alvo. A v1 cobra do plano o deslocamento da última
posição de D até o alvo, mas o baseline não paga o deslocamento natural da última posição de D até a posição observada no início da sessão.
Com `fix_m2`, os dois braços pagam esse trecho: `overnight_km` = distância ao alvo (se moveu) ou à posição observada (se não moveu), para
os mesmos motoristas (os que começam a trabalhar a partir de 30 min antes da janela). `empty_km_sim = busca + overnight_km + reposicionamento em serviço`.
A diferença entre braços passa a ser o custo **líquido** do plano em relação ao deslocamento que o motorista faria de qualquer forma.

Medida do trecho natural (dias de teste, janela 04–11): mediana 0,7 km, média 3,5 km (mar/2026) e 5,6 km (set/2026) por motorista-dia,
1 226 e 918 motoristas-dia, 72–76% acima de 0,2 km. É da mesma ordem do reposicionamento (limite de 3 km), logo a contabilização importa.

## Limites e leitura
- Esta é a interpretação operacionalizada a partir da descrição do proponente (D8). **Status atual: ver "Confirmação (D-B)" no fim deste arquivo**; o histórico abaixo (D8, D10) foi mantido.
- O trecho noturno não é "KM morto em disponibilidade" no sentido estrito; a correção mede o custo líquido de **trocar** o destino noturno do motorista. A contabilização da v1 (bruta) continua reportada ao lado.
- A premissa do regime B (motorista aceita dormir/partir da zona-alvo sem custo de tempo) continua não verificada.

## Revisão (desvio D10, 28/10/2026, antes da Fase 4)
O placebo de movimentos aleatórios mostrou que "pagar nos dois braços" (m2 como descrita acima) produz uma economia espúria:
ΔKM do placebo = +39,1 km/dia (mar) e +35,5 (set) na contabilização da v1, e **−20,9 e −31,5** em "pagar nos dois". A causa é que o planejador do
regime B parte da última posição de D, enquanto o mundo põe o baseline no ponto de login (3,5–5,6 km em média). Trocar um trecho noturno longo
por um movimento curto a partir da origem "economiza" KM sem nenhuma informação de demanda.

**m2 primária revisada:** `start_at_origin=True`. Os dois braços começam a sessão na última posição de D, como o regime B pressupõe. O plano
paga origem → alvo; o baseline não paga nada. "Pagar nos dois" (`fix_m2`) permanece como sensibilidade rotulada. A contabilização bruta da v1
(mundo `login`) é a terceira. As três são reportadas lado a lado; nenhuma é "o resultado".

Resultados da Fase 3 no campo `empty_km_sim` usam "pagar nos dois" (a Fase 3 rodou antes da revisão): leia como sensibilidade sujeita ao artefato acima.

## Confirmação (decisão D-B, 28/10/2026)
O autor do TCC (Entony Jovino) **confirmou em 28/10/2026** a interpretação vigente: a contabilização principal é `start_at_origin`, em que os dois braços começam a sessão na última posição de D, como o regime B pressupõe. Isso substitui a nota "interpretação a confirmar" da seção "Limites e leitura" e do D8/D10 do pré-registro, **sem apagá-los**: D8 (m2 como "pagar nos dois braços") e D10 (revisão para `start_at_origin`) permanecem como histórico. Nenhuma reexecução é necessária, pois os resultados da Fase 4 já usam essa contabilização. O resultado é condicional a essa premissa; "pagar nos dois braços" e a v1 bruta continuam como sensibilidades rotuladas. Fonte da confirmação: mensagem do autor na sessão de 28/10/2026 (sem documento externo).
