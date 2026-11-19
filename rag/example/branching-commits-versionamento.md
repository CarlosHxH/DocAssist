# Branching, Commits e Versionamento

> Documento fictício, criado para o MVP do DocAssist. Não reproduz nenhuma norma real.

## Fluxo de branches

- `main` contém apenas código que está ou esteve em produção; cada release recebe uma tag.
- `develop` integra as funcionalidades concluídas e é publicada automaticamente no
  ambiente de desenvolvimento.
- Funcionalidades e correções nascem de `develop` e voltam para ela por merge request.
- Hotfixes nascem da última tag de `main`, são integrados em `main` e depois em `develop`.
- Os nomes de branch seguem o guia de Padrões de Nomenclatura.

## Conventional Commits

As mensagens de commit seguem o padrão Conventional Commits: `<tipo>(<escopo opcional>):
<descrição no imperativo>`. Os tipos aceitos pelo time são:

- `feat`: nova funcionalidade;
- `fix`: correção de defeito;
- `docs`: apenas documentação;
- `style`: formatação, sem mudança de comportamento;
- `refactor`: mudança de código que não corrige defeito nem adiciona funcionalidade;
- `test`: inclusão ou ajuste de testes;
- `chore`: tarefas de manutenção (dependências, scripts);
- `ci`: mudanças no pipeline de integração contínua;
- `perf`: melhoria de desempenho.

Commits com `BREAKING CHANGE:` no rodapé, ou com `!` após o tipo, indicam quebra de
compatibilidade. O pipeline rejeita commits fora do padrão.

## Versionamento semântico

As releases usam versionamento semântico no formato `MAIOR.MENOR.PATCH`:

- **MAIOR** sobe quando há quebra de compatibilidade (commit com `BREAKING CHANGE`);
- **MENOR** sobe quando entra ao menos um `feat` sem quebra;
- **PATCH** sobe quando só há `fix` ou `perf`.

A versão é calculada automaticamente pelo pipeline a partir dos commits desde a última tag.
A tag é criada no formato `v2.5.0` e gera as notas de release com a lista de commits
agrupada por tipo. Versões de pré-release usam o sufixo `-rc.N` (`v2.5.0-rc.1`) e só são
publicadas em homologação.
