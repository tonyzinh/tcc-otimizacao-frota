# Segurança e governança dos dados

- O núcleo local de experimento e seus testes usam dados sintéticos. Os notebooks `00` e `01` leem o Parquet real autorizado de um Volume, com confirmação explícita em cada execução, e apresentam apenas esquema ou agregados. O Parquet e os CSVs locais permanecem ignorados pelo Git.
- A CLI `audit-local --dataset-kind real` exige `TCC_REAL_DATA_AUTHORIZED=YES` **após autorização formal**. O adaptador de arquivos exige adicionalmente `TCC_EXTERNAL_DATA_AUTHORIZED=YES` para destino externo. Essas variáveis são barreiras técnicas, não substituem autorização institucional; não há upload automático implementado.
- Não introduza credenciais no repositório. Caminhos e ambiente são parâmetros, e `.env` é ignorado.
- Logs e artefatos compartilháveis contêm agregados; evite IDs pessoais, placas, telefones e trajetórias reais. A substituição de identificadores diretos ainda permite reidentificação por tempo/local; avalie granularidade, raridade e retenção antes de divulgar.
- Para dados reais autorizados, confirme finalidade, base de uso, acesso, localização de processamento, minimização e revisão de risco de reidentificação. Free Edition não deve receber dados corporativos sem aprovação específica para esse ambiente.
- Preservar originais; a auditoria deve produzir contagens e hashes, não exemplos de linhas confidenciais. Nenhuma rotina atual escreve sobre os CSVs de `data/`.

O usuário informou autorização para este Parquet no Databricks Free Edition. Ela não altera a exigência de escolher o workspace autorizado e confirmar `real_data_authorized=true` na execução. A auditoria não cria tabelas nem envia dados por conta própria. Consulte [execucao_databricks.md](execucao_databricks.md) antes de executar.
