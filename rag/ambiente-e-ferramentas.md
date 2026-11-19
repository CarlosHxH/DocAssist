# Ambiente e Ferramentas

> Documento fictício, criado para o MVP do DocAssist. Os nomes de servidores são
> exemplos (`exemplo.internal`) e não existem.

## Controle de versão e CI/CD

- **GitLab** (`git.exemplo.internal`): repositórios, merge requests e pipelines de CI/CD.
  Todo projeto tem um `.gitlab-ci.yml` com as etapas build, test, quality, package e deploy.
- **Runners** em Kubernetes executam os jobs do pipeline.

## Registro de artefatos

- **Nexus** (`artefatos.exemplo.internal`): registro de imagens Docker e de pacotes Maven e
  npm. O pipeline publica as imagens com a versão semântica e o hash do commit.

## Qualidade e segurança

- **SonarQube**: análise estática; o pipeline falha se a cobertura de testes ficar abaixo
  de 70% ou se surgirem problemas bloqueantes.
- **Dependency-Track**: inventário de dependências e alerta de vulnerabilidades conhecidas.

## Execução e observabilidade

- **Kubernetes** com **Rancher** para gerenciar os clusters de dev, hml e prd.
- **Elastic Stack** (Elasticsearch, Kibana e APM) para logs, métricas e traces.

## Identidade

- **Keycloak** para autenticação única dos sistemas, com papéis nomeados segundo o guia de
  Padrões de Nomenclatura.
