#!/usr/bin/env bash
# Campanha ODS retomável, UM leitor pesado por vez (ES roda em fluxo próprio). Repetir o comando retoma.
# Ordem (08/11/2026, rev. 3): o que a primeira comparação A x B no desenvolvimento exige vem antes do que é só diagnóstico.
#  1 jornada+compromissos da fatia P0 (07-13/03) | 2 núcleo de desenvolvimento 01/02-31/03 (demanda, status, veículo)
#  3 compromissos nos dias-alvo 09-15/03 | 4 restante da fatia P0 (log de status, Cobli, reposicionamento) | 5 vínculos de dev
#  6 Cobli/compromissos/reposicionamento de dev | 7 aquecimento 07/12-31/01 | 8 replicação e final reservada (integridade) | 9 aquecimento 22/07-15/09
set -u
cd "$(dirname "$0")/.."
NUC="solicitacao status_solicitacao veiculo"
VINC="veiculo_condutor jornada_motorista log_status_motorista"
OUT="reposicionamento compromissos_externos telemetria_cobli"
run() { echo "### $1"; shift; ODS_ENT="$1" ES_ENT=" " scripts/extract_v1_period.sh "$2" "$3"; }
run "1 jornada+compromissos P0 07-13/03" "jornada_motorista compromissos_externos" 2026-03-07 2026-03-13
run "2 P1 nucleo dev 01/02-31/03" "$NUC" 2026-02-01 2026-03-31
run "3 compromissos dias-alvo 14-15/03" "compromissos_externos" 2026-03-14 2026-03-15
run "3b compromissos 09-10/03 antes da fatia (D dos alvos)" "compromissos_externos" 2026-03-08 2026-03-09
run "4 restante P0 07-13/03" "log_status_motorista telemetria_cobli reposicionamento" 2026-03-07 2026-03-13
run "5 dev vinculos 01/02-31/03" "$VINC" 2026-02-01 2026-03-31
run "6 dev compromissos/cobli/reposicionamento" "$OUT" 2026-02-01 2026-03-31
run "7 aquecimento 07/12-31/01" "solicitacao status_solicitacao" 2025-12-07 2026-01-31
run "8 replicacao 16-30/09" "$NUC $VINC $OUT" 2026-09-16 2026-09-30
run "8 final reservada 01-25/10 (integridade)" "$NUC $VINC $OUT" 2026-10-01 2026-10-25
run "9 aquecimento 22/07-15/09" "solicitacao status_solicitacao" 2026-07-22 2026-09-15
echo CAMPANHA-FIM
