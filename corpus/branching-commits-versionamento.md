# Branches, Commits e Versionamento

## Estratégia de branches

Usamos uma variação do Git Flow, com cinco tipos de branch:

- `master`: sempre reflete o que está em produção. Ninguém commita diretamente aqui; só
  recebe merge vindo de `release/*` ou `hotfix/*`, e sempre após aprovação de pelo menos
  um revisor sênior.
- `develop`: branch de integração contínua, recebe merges de `feature/*` já revisadas.
- `feature/<descrição-curta>`: uma branch por funcionalidade em desenvolvimento, criada a
  partir de `develop`.
- `release/x.y.z`: criada a partir de `develop` quando um conjunto de funcionalidades está
  pronto para ir a homologação. Só recebe correções pontuais, não novas funcionalidades.
- `hotfix/<descrição-curta>`: criada a partir de `master` para corrigir um problema urgente
  em produção, sem esperar o ciclo normal de release.

Branches devem ser **excluídas após o merge**. Uma rotina periódica de limpeza remove
branches obsoletas que os times esqueceram de apagar, mas o ideal é que cada responsável
exclua a própria branch assim que o merge for confirmado.

## Padrão de commits

Adotamos Conventional Commits. O formato é `tipo(escopo opcional): descrição breve`, com
os tipos: `feat` (nova funcionalidade), `fix` (correção de bug), `refactor`
(refatoração sem mudança de comportamento), `build` (mudanças de build/dependências),
`ci` (mudanças de pipeline), `docs` (documentação), `style` (formatação), `db` (mudanças
de banco de dados) e `revert` (reversão de commit anterior).

Exemplos:
- `feat(login): adiciona autenticação por certificado digital`
- `fix(relatorios): corrige cálculo de total na exportação CSV`
- `db(usuarios): adiciona coluna data_ultimo_acesso`

Recomenda-se pelo menos um commit por dia útil trabalhado em uma branch ativa, para manter
o histórico granular e facilitar revisão.

## Versionamento semântico

Releases seguem versionamento semântico `MAJOR.MINOR.PATCH`:
- `MAJOR`: mudança incompatível com versões anteriores.
- `MINOR`: nova funcionalidade compatível com versões anteriores.
- `PATCH`: correção de bug compatível com versões anteriores.

Toda release recebe uma tag Git correspondente à versão (`v1.4.2`, por exemplo), criada no
momento em que a branch `release/x.y.z` é promovida para `master`.

## Release notes

As notas de release hoje são escritas manualmente pelo responsável técnico, seguindo um
modelo com seções fixas ("Novidades", "Correções", "Mudanças internas"), mesmo que o
histórico de commits já siga o padrão Conventional Commits — não existe automação que
gere o rascunho das notas a partir dos commits da release.
