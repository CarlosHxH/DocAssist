# Portal de Acesso

> Documento fictício, criado para o MVP do DocAssist. Não descreve nenhum sistema real.

## Visão geral

O Portal de Acesso é o sistema fictício que centraliza o controle de quem pode usar cada
sistema interno. Em vez de cada sistema manter os próprios usuários e permissões, todos
consultam o Portal, que concede, revisa e revoga acessos em um único lugar.

## Hierarquia de dados

O Portal organiza as permissões em quatro níveis:

1. **Sistema**: cada aplicação cadastrada (ex.: Agenda, Protocolo).
2. **Módulo**: uma área funcional dentro do sistema (ex.: Agendamentos, Relatórios).
3. **Funcionalidade**: uma ação específica dentro do módulo (ex.: criar agendamento).
4. **Perfil**: um conjunto de funcionalidades atribuído aos usuários.

Um usuário recebe um ou mais perfis; as permissões efetivas são a união das
funcionalidades desses perfis.

## Principais funções

- Solicitação de acesso pelo próprio usuário, com aprovação do gestor da área.
- Revisão periódica de acessos a cada seis meses.
- Aceite de termo de uso no primeiro acesso a cada sistema.
- Relatórios de auditoria de concessões e revogações.

## Roteiro de implantação

O roteiro tem três fases, somando 12 semanas:

- **Fase 1, semanas 1 a 4:** cadastro de sistemas, módulos, funcionalidades e perfis.
- **Fase 2, semanas 5 a 8:** solicitação e aprovação de acesso e termo de uso.
- **Fase 3, semanas 9 a 12:** revisão periódica, relatórios de auditoria e integração dos
  primeiros sistemas.
