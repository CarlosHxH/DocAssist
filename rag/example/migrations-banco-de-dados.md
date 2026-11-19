# Migrations de Banco de Dados

> Documento fictício, criado para o MVP do DocAssist. Não reproduz nenhuma norma real.

## Nome dos scripts

Os scripts de migration seguem o formato `V<AAAAMMDDHHMM>__<descricao_em_snake_case>.sql`,
por exemplo `V202603151430__cria_tabela_agendamento.sql`. O prefixo com data e hora evita
conflito de numeração entre branches. Scripts repetíveis (views, funções) usam o prefixo
`R__`, por exemplo `R__view_agendamentos_ativos.sql`.

## Regras de escrita

- Um script por mudança lógica; nunca editar um script que já foi aplicado em algum ambiente.
- Toda migration deve ser compatível com a versão anterior da aplicação, para permitir
  rollback do deploy. Remover ou renomear coluna é feito em duas releases: primeiro a
  aplicação deixa de usar a coluna, depois a coluna é removida.
- Índices em tabelas grandes são criados de forma concorrente, sem bloquear a tabela.
- Dados sensíveis não podem aparecer nos scripts.

## Checklist antes de abrir o pull request

Antes de abrir o pull request com uma migration, o desenvolvedor deve:

1. rodar a migration do zero em um banco local limpo e também sobre uma cópia anonimizada
   de homologação;
2. confirmar que a versão anterior da aplicação continua funcionando com o banco migrado;
3. medir o tempo de execução e informar no pull request se passar de um minuto;
4. descrever no pull request o impacto esperado (tabelas afetadas, bloqueios, volume de
   dados);
5. pedir revisão de um DBA quando a migration alterar tabelas com mais de um milhão de
   linhas.

## Execução

As migrations rodam automaticamente na inicialização da aplicação, com a ferramenta de
versionamento de schema, antes de a aplicação começar a receber tráfego.
