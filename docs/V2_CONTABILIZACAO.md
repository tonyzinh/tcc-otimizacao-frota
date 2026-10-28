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
- Esta é a interpretação operacionalizada a partir da descrição do proponente; se a intenção era outra, o desvio D8 do pré-registro deve ser revisto.
- O trecho noturno não é "KM morto em disponibilidade" no sentido estrito; a correção mede o custo líquido de **trocar** o destino noturno do motorista. A contabilização da v1 (bruta) continua reportada ao lado.
- A premissa do regime B (motorista aceita dormir/partir da zona-alvo sem custo de tempo) continua não verificada.
