# Padrões de Nomenclatura

> Documento fictício, criado para o MVP do DocAssist. Não reproduz nenhuma norma real.

Este guia define como nomear repositórios, branches, papéis de identidade e recursos de
infraestrutura da organização fictícia "Departamento de TI Exemplo".

## Repositórios e projetos

- Formato: `<sigla-do-sistema>-<camada>`, tudo em minúsculas e separado por hífen.
- Camadas aceitas: `api` (backend), `web` (frontend), `worker` (processamento assíncrono),
  `lib` (biblioteca compartilhada) e `infra` (scripts de infraestrutura).
- Exemplos: `agenda-api`, `agenda-web`, `protocolo-worker`, `comum-lib`.
- Nomes não podem conter o nome de pessoas, de fornecedores ou de versões (`v2`, `novo`).

## Branches

| Tipo | Padrão | Exemplo |
|------|--------|---------|
| Funcionalidade | `feature/<id-da-tarefa>-<descricao-curta>` | `feature/ABC-123-filtro-por-data` |
| Correção comum | `fix/<id-da-tarefa>-<descricao-curta>` | `fix/ABC-140-erro-paginacao` |
| Correção urgente em produção | `hotfix/<versao>-<descricao-curta>` | `hotfix/2.4.1-timeout-login` |
| Preparação de release | `release/<versao>` | `release/2.5.0` |

A branch de hotfix sempre parte da tag de produção e leva no nome a versão de patch que
será gerada. Descrições usam no máximo cinco palavras, em minúsculas e com hífens.

## Papéis de identidade (roles)

- Papéis específicos de um sistema: `<sigla-do-sistema>_<papel>`, por exemplo
  `agenda_gestor`, `agenda_leitor`.
- Papéis compartilhados entre vários sistemas usam o prefixo `global_`, por exemplo
  `global_administrador` e `global_auditor`.
- Papéis técnicos de contas de serviço usam o prefixo `svc_`, por exemplo `svc_agenda_api`.
- Nunca criar papéis com o nome de uma pessoa ou de uma unidade organizacional.

## Recursos de infraestrutura

- Namespaces do Kubernetes: `<sigla-do-sistema>-<ambiente>` (`agenda-dev`, `agenda-hml`,
  `agenda-prd`).
- Bancos de dados: `db_<sigla-do-sistema>`; schemas seguem o nome do módulo.
- Variáveis de ambiente: maiúsculas com underscore, prefixadas pela sigla do sistema
  (`AGENDA_DB_URL`).
