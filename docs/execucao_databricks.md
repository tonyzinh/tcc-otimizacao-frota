# Execução no Databricks Free Edition

**Estado:** notebooks e SQL preparados, sem execução ou autenticação em workspace nesta entrega. Use **somente dados sintéticos**. A [documentação oficial de limites](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations) informa que Free Edition usa computação serverless, com cotas e recursos reduzidos. Confirme os limites e permissões da sua conta antes de executar; não há garantia de disponibilidade contínua.

1. Abra o repositório em um Git folder do Databricks. Em cada notebook, informe `project_root` como caminho absoluto do repositório em `/Workspace/...`; o notebook adiciona `src/` ao caminho de importação. A [documentação de importação](https://docs.databricks.com/aws/en/ldp/import-workspace-files) descreve esse ajuste para código fora da pasta do notebook.
2. Verifique catálogo disponível e permissões de criação. O exemplo usa `workspace.tcc_frota_synthetic`, mas o nome pode diferir. Ajuste widgets e, se desejar, execute `databricks/setup/create_objects.sql`. O notebook 01 também cria schema e volume gerenciado sintéticos. A [documentação de volumes](https://docs.databricks.com/aws/en/volumes/utility-commands) descreve a criação de volumes gerenciados.
3. Execute `01_auditoria.py` a `07_simulacao.py` em ordem, mantendo os mesmos `catalog`, `schema`, `pipeline_run_id`, `seed` e `target_date`. O volume armazena apenas os dois CSVs gerados. Bronze, Silver e Gold são tabelas Delta identificadas por `run_id`.
4. Confira contagens e exclusões em Silver, previsão e recomendações Gold, cobertura e métricas do replay. O notebook 07 confere que a quantidade de recomendações persiste no Gold.

Não instale PySpark como dependência adicional no notebook serverless: a [orientação oficial de dependências](https://docs.databricks.com/aws/en/compute/serverless/dependencies) alerta que isso pode quebrar a sessão. O pacote local não depende de PySpark; o adaptador importa o Spark fornecido pelo ambiente. Não há exigência de serviço pago, API de rotas, Jobs ou Deploy Bundle.

**Limites:** nenhum notebook foi testado no Databricks aqui. A coleta para o núcleo Python é limitada a 10 mil linhas sintéticas. Dados reais exigiriam autorização específica, contratos e transformações distribuídas adicionais; a simples existência de notebooks não valida integração ou escala.
