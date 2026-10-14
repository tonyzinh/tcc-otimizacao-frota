-- Consultas de inspeção somente para tabelas sintéticas de exemplo.
-- Ajuste catálogo/schema antes de executar; nenhuma query acessa dados corporativos.
SELECT run_id, scenario, requests, served, coverage,
       pickup_km, reposition_km, total_km
FROM workspace.tcc_frota_synthetic.gold_metrics
ORDER BY run_id, scenario;

SELECT run_id, split, zone, hour, request_count
FROM workspace.tcc_frota_synthetic.gold_demand
ORDER BY run_id, split, hour, zone;
