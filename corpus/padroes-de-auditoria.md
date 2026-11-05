# Padrões de Auditoria

Todo sistema do IHT deve registrar três tipos de log para fins de auditoria, cada um com
campos mínimos obrigatórios: quem, o quê, quando, onde e como.

## Logs de acesso

Registram tentativas de autenticação (sucesso e falha), logout e eventos de sessão. São
gerados automaticamente pelo provedor de identidade central e ficam retidos por, no
mínimo, 5 anos, conforme política de retenção institucional.

## Logs de operações

Registram ações relevantes realizadas pelos usuários dentro de cada sistema (criação,
edição, exclusão de registros; aprovação ou rejeição de solicitações; exportação de
dados). Cada sistema grava esses eventos em uma tabela própria (`log_operacoes`), seguindo
um vocabulário padronizado de ações (`CRIAR`, `EDITAR`, `EXCLUIR`, `APROVAR`, `REJEITAR`,
`EXPORTAR`, `VISUALIZAR_DADO_SENSIVEL`). O registro inclui usuário responsável, timestamp,
identificador do recurso afetado, valores antes/depois (quando aplicável) e origem da
requisição (IP, user agent).

## Logs de entidades

Capturam o histórico de alterações de entidades de negócio específicas (por exemplo, o
histórico completo de mudanças em uma "solicitação" ao longo do seu ciclo de vida),
permitindo reconstruir o estado do registro em qualquer momento do passado. Esses logs são
gerados automaticamente a partir do mapeamento objeto-relacional da aplicação, sem
necessidade de código adicional em cada funcionalidade.

## Regras gerais

- Nenhum log de auditoria pode ser editado ou apagado por usuários da aplicação — apenas
  por processos administrativos de retenção/expurgo, documentados e registrados em log
  próprio.
- Dados sensíveis (CPF, dados de saúde, dados de processos sigilosos) não devem aparecer
  em texto claro nos logs de operações; deve-se usar referência ao identificador do
  registro, não o dado em si.
- Toda nova funcionalidade que lida com dados sensíveis deve, no momento do
  desenvolvimento, já prever os três tipos de log descritos acima — auditoria não é algo
  adicionado depois, é parte do desenho da funcionalidade.
