> Cópia versionada de `RELATORIO.md` (rodada 6) em que o nome de usuário da máquina foi trocado por `<usuário>` (1 ocorrência). O original fica local, congelado e fora do versionamento (`.gitignore`). Nenhuma outra alteração.

# Rodada 6: simplificação do artigo e verificação (09/11/2026)

Nenhuma análise foi refeita nem removida. Só o texto e a organização mudaram. Nada foi commitado nem adicionado ao stage.

## 1. Resultados congelados

O script de conferência está no scratchpad da sessão; a saída fica em `hashes_congelados.csv`.

- **`reports/tcc_final`:** 19 de 19 arquivos com SHA-256 igual à tabela do pré-registro. O pré-registro (`docs/V2_PREREGISTRO.md`) está no git, commit `cb00ee3`.
- **Arquivos rastreados pelo git** nos quatro diretórios congelados: 138 de 138 com SHA-256 igual ao do blob em HEAD (`3e65f3b`), depois de normalizar o fim de linha.
- **Parquets de execução de `reports/atribuicao_final`:** são ignorados pelo git e não têm SHA-256 registrado no congelamento. Por isso, conferiram-se os totais.
  - Os totais por política (km vazio e atendidos) são iguais aos de `analise/*_absolutos.csv`, que é rastreado.
  - O SHA-256 atual foi gravado para referência futura.
- **Datas de modificação:** a mais recente nos diretórios congelados é de 09/11/2026, às 10:35.
- **Falhas:** 0.

Não existe registro de hash para os cerca de 4.180 arquivos não rastreados de `reports/sintetico_v2`. Para eles, vale só a data de modificação; não houve conferência de conteúdo.

## 2. Números do texto

A comparação foi valor a valor entre todas as seções e apêndices de antes e de depois; a lista completa está em `numeros_antes_depois.csv`.

- **Volume:** 705 valores distintos antes e 699 depois, 696 em comum.
- **Só no novo:**
  - `2,3`: atendidos por dia no treino (98/43), de `janelas_treino_por_dia.csv`, pedido pela rodada.
  - `0.87`: o mesmo 0,87% do português, agora também no abstract.
  - `0.7`: largura do mapa.
- **Só no antigo:**
  - Os valores do abstract encurtado (0.36, 1.40, 2.74, 3.3, 7.4). Todos continuam no texto em português.
  - Números de seção citados no texto (3.5, 3.6, 4.1).
  - A largura antiga do mapa (0.78).

Diferença do pedido: a queda da participação do km vazio em outubro é **0,85 p.p.** (21,630% para 20,776%, em `base_por_dia.csv`). O texto mantém "0,9" e não "0,8". O 0,8 vem da subtração das participações já arredondadas.

## 3. Limitações

As oito limitações antigas, (i) a (viii), estão na lista "O que este estudo não mostra" (Seção 4.6):

| Limitação antiga | Item novo |
|---|---|
| (i) validação | simulador fiel |
| (ii) disponibilidade | o que a política saberia |
| (iii) distância | distâncias reais |
| (iv) aceite, recusa, cancelamento e tentativas | simulador fiel |
| (v) cadastro | o que a política saberia |
| (vi) uma empresa | generalização |
| (vii) despacho simplificado | economia real |
| (viii) sem produção | economia real |

A lista acrescenta a equivalência sem margem, a linha reta que ignora a baía e o fato de a verificação viária cobrir só 4 dias. As demais ressalvas ficaram no Apêndice A:

- verificação estrutural das pontes;
- seleção da espera;
- sementes vistas antes da adoção;
- falta de carimbo externo no congelamento.

## 4. OneDrive e dados

- **Cliente de sincronização:** o OneDrive foi desinstalado pelo usuário em 15/10/2026, às 19:14. Isso aparece no registro (`UserInitiatedUninstall=1`, sem contas e sem executável). O último log do cliente é desse dia.
- **`data/` não foi sincronizada por esta máquina.** Todos os arquivos foram criados a partir de 06/11/2026.
  - A pasta continua dentro de `C:\Users\<usuário>\OneDrive\...`. Se o OneDrive for reinstalado, ela passa a sincronizar.
- **`src/data`, apagada na rodada 5:** não está na lixeira, porque `Remove-Item` apaga direto, e não tem histórico do OneDrive.
- **Lixeira do Windows:** há duas pastas `data` vindas deste repositório.
  - A primeira, de 0,98 GB, foi apagada em 14/10/2026, às 19:14, **quando o OneDrive ainda estava instalado**.
  - A segunda, de 7,17 GB, foi apagada em 15/10/2026, às 21:11.
  - Não foram abertas nem apagadas.
  - Se o OneDrive sincronizava entre 18/09 e 15/10, cópias podem existir na nuvem (lixeira ou histórico de versões). Isso não pode ser verificado daqui.
- **Texto das Declarações:** foi ajustado para descrever essa situação.

## 5. Compilação

- **Páginas:** 33 no total. O corpo vai da p. 2 (introdução) à p. 21 (fim das referências), 20 páginas. Os apêndices A a D começam em página nova, na p. 22.
- **Avisos:** 0 caixas estouradas; 0 citações ou referências indefinidas.
- **Testes:** 203 aprovados, 0 falhas.
- **Lint:** Ruff limpo.
