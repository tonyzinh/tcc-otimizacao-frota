-- Executar apenas em catálogo onde o usuário tenha CREATE SCHEMA/CREATE VOLUME.
-- Sintéticos exclusivamente; não fazer upload automático de extratos corporativos.
CREATE SCHEMA IF NOT EXISTS workspace.tcc_frota_synthetic;
CREATE VOLUME IF NOT EXISTS workspace.tcc_frota_synthetic.inputs;
-- Troque `workspace` somente após verificar o catálogo disponível na sua conta.
