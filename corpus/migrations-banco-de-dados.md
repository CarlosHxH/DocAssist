# Migrations de Banco de Dados

## Padrão de nome de arquivo

Scripts de migration seguem o padrão:

```
V_AAAAMMDD_NNN__tipo_descricao.sql
```

- `AAAAMMDD`: data de criação do script.
- `NNN`: número sequencial de três dígitos dentro do mesmo dia, começando em 001.
- `tipo`: um entre `ddl` (mudança de estrutura), `dml` (mudança de dados) ou `seed`
  (dados iniciais/massa de teste).
- `descricao`: breve, em snake_case, descrevendo o que o script faz.

Exemplo: `V_20250312_001__ddl_cria_tabela_solicitacoes.sql`.

## Organização de pastas

- `migrations/changelog/`: scripts que efetivamente alteram o banco, aplicados em ordem
  lexicográfica (por isso a data e o número sequencial no nome são essenciais).
- `migrations/rollback/`: script de reversão correspondente a cada script de changelog,
  com o mesmo nome base e sufixo `_rollback`.
- `migrations/seed/`: dados de massa para ambiente de desenvolvimento e testes.
- `migrations/util/`: scripts de apoio que não fazem parte do changelog principal
  (consultas de diagnóstico, por exemplo).

## Checklist obrigatório antes de abrir o pull request

1. O script é idempotente (pode ser executado mais de uma vez sem causar erro ou
   duplicar dados)?
2. Existe um script de rollback correspondente, testado?
3. O script foi revisado por pelo menos uma segunda pessoa (peer review de SQL)?
4. O script contém comentários explicando alterações não óbvias (por que um índice foi
   criado, por que uma coluna foi tornada nullable, etc.)?
5. Para mudanças em tabelas grandes, foi avaliado o impacto de performance/lock durante a
   execução em produção?

## Execução

Hoje a execução dos scripts em cada ambiente é manual: o responsável técnico roda o script
na ordem correta, direto no ambiente de banco correspondente, e anexa a evidência de
execução (print do resultado, linhas afetadas) ao chamado de mudança. Não há uma
ferramenta de migration automatizada rodando os scripts como parte da pipeline.
