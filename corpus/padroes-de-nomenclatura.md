# Padrões de Nomenclatura

## Repositórios e projetos

Nome do repositório sempre em minúsculas, separado por hífen, no formato
`<sigla-sistema>-<camada>`, por exemplo `sgp-api` (API do Sistema de Gestão de Processos)
ou `sgp-web` (frontend do mesmo sistema). Evitar abreviações pouco óbvias; preferir siglas
já usadas oficialmente pelo sistema.

## Branches

- Feature: `feature/<ticket>-<descricao-curta>`, ex.: `feature/HOR-123-filtro-avancado`
- Hotfix: `hotfix/<ticket>-<descricao-curta>`, ex.: `hotfix/HOR-456-corrige-login`
- Release: `release/<major.minor.patch>`, ex.: `release/2.3.0`

O prefixo `HOR-` corresponde ao código do sistema de rastreamento de tarefas interno;
branches sem número de ticket associado são aceitas apenas para ajustes triviais de
documentação.

## Papéis e permissões (identidade)

Papéis no provedor de identidade seguem o padrão `<sistema>_<perfil>`, em letras
minúsculas e underscore, por exemplo `sgp_administrador`, `sgp_operador_leitura`. Papéis
genéricos compartilhados entre sistemas usam o prefixo `global_`, como `global_auditor`.

## Banco de dados

- Tabelas: plural, snake_case, sem prefixo de sistema quando o schema já é dedicado ao
  sistema (ex.: `usuarios`, `solicitacoes`, `log_operacoes`).
- Colunas: snake_case, sempre no singular (ex.: `data_criacao`, `usuario_id`).
- Chaves estrangeiras: `<tabela_referenciada_singular>_id`, ex.: `usuario_id`.
- Índices: `idx_<tabela>_<coluna(s)>`.
- Scripts de migration: ver o documento "Migrations de Banco de Dados" para o padrão de
  nome de arquivo.

## Imagens Docker

Nome da imagem segue `<registry>/<sigla-sistema>/<camada>:<tag>`. Tags mutáveis como
`latest` ou `develop` são aceitas apenas em desenvolvimento; homologação e produção devem
sempre referenciar uma tag imutável correspondente à versão semântica (`2.3.0`, não
`latest`).
