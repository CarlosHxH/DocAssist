# Portal de Acesso (visão geral)

O Portal de Acesso é a plataforma centralizada de governança de identidade e acesso do
IHT, em desenvolvimento, que substituirá o controle de acesso fragmentado que hoje existe
em cada sistema individualmente.

## Modelo de dados

O portal organiza o acesso em uma hierarquia: **Sistema → Módulo → Funcionalidade →
Perfil → Usuário**. Um perfil agrupa um conjunto de funcionalidades liberadas dentro de um
módulo de um sistema; um usuário recebe um ou mais perfis, podendo ter perfis diferentes
em sistemas diferentes.

## Funcionalidades previstas

- Concessão e revogação de acesso com aprovação do gestor responsável pelo sistema.
- Trilha de auditoria completa de toda concessão, alteração e revogação de acesso.
- Aceite obrigatório de termo de uso antes do primeiro acesso a um sistema que lide com
  dados sensíveis.
- Resposta a incidentes: bloqueio automático de usuário e revogação em massa de tokens
  ativos em caso de suspeita de comprometimento de credenciais.
- Resolução de organização por subdomínio, permitindo que diferentes unidades
  organizacionais tenham URLs próprias apontando para o mesmo portal.

## Status

O Portal de Acesso está em fase de rascunho/planejamento, com um roteiro de implementação
dividido em quatro fases ao longo de dez semanas. A primeira fase cobre o modelo de dados
e a integração com o provedor de identidade central; fases posteriores cobrem a interface
de solicitação/aprovação de acesso e, por fim, a separação dos componentes em
microsserviços independentes.
