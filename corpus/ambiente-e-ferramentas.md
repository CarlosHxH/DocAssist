# Ambiente e Ferramentas que Operamos

Este documento descreve, em alto nível, as ferramentas e plataformas utilizadas pelas
equipes de desenvolvimento do Instituto Horizonte de Tecnologia (IHT) — organização
fictícia usada neste MVP como exemplo de órgão público de TI.

## Controle de versão e CI/CD

Usamos GitLab como plataforma central de código-fonte e pipelines de CI/CD. Cada projeto
possui um arquivo `.gitlab-ci.yml` que referencia templates compartilhados mantidos no
projeto "Templates-CI-Horizonte". As pipelines são organizadas por ambiente, em pastas
`ci/desenvolvimento`, `ci/homologacao` e `ci/producao`.

## Qualidade e segurança de código

Toda pipeline executa análise estática com SonarQube e varredura de dependências
vulneráveis com uma ferramenta de SCA (Software Composition Analysis). Falhas de
qualidade acima do limite configurado bloqueiam o merge para a branch principal.

## Registro de artefatos e imagens

Artefatos de build (bibliotecas, pacotes) ficam armazenados em um repositório Nexus
interno. Imagens Docker são publicadas em um registry privado com varredura automática de
vulnerabilidades antes da liberação para homologação ou produção.

## Orquestração e deploy

As aplicações rodam em clusters Kubernetes, um por ambiente (desenvolvimento, homologação,
produção), gerenciados através de um painel de administração interno. O deploy usa
templates Helm versionados junto ao código da aplicação.

## Observabilidade

Monitoramos aplicações com uma stack de observabilidade baseada em coleta de métricas,
logs centralizados e rastreamento distribuído (tracing). Cada sistema possui um painel
próprio com visão geral, taxa de erros, latência de transações e dependências externas.

## Identidade e acesso

A autenticação de usuários internos e de sistemas integrados é feita por um provedor de
identidade centralizado baseado no protocolo OIDC, com suporte a múltiplos domínios
organizacionais (multi-realm).

Essas ferramentas formam a base sobre a qual os demais documentos deste acervo (processo
de deploy, padrões de nomenclatura, padrões Docker, migrations, auditoria e monitoramento)
se apoiam.
