# Padrões Docker para Projetos

## Dois Dockerfiles por projeto

Cada projeto mantém dois arquivos de build de imagem:

- `Dockerfile`: usado pela pipeline de CI/CD para gerar a imagem que vai para homologação
  e produção. Deve ser enxuto, multi-stage quando aplicável, e nunca incluir ferramentas
  de desenvolvimento (debugger, hot-reload, etc.).
- `local.Dockerfile`: usado apenas para desenvolvimento local, pode incluir ferramentas
  extras e montar volumes para hot-reload do código.

## Variáveis de ambiente

Toda variável de ambiente usada pela aplicação deve estar documentada em um arquivo
`.env.example` no repositório, sem valores reais — apenas nomes de variáveis e, quando
útil, um valor de exemplo não sensível. O arquivo `.env` real (com valores reais) nunca é
commitado; está sempre no `.gitignore`.

## docker-compose para ambiente local

Projetos que dependem de outros serviços (banco de dados, cache, fila) devem fornecer um
`docker-compose.yml` que sobe o ambiente local completo com um único comando, incluindo
dados de exemplo (seed) quando aplicável, para que um novo desenvolvedor consiga rodar o
projeto localmente sem depender de acesso a ambientes compartilhados.

## Boas práticas obrigatórias

- Não rodar o processo principal como usuário `root` dentro do container.
- Fixar a versão da imagem base (nunca usar `latest` como base), para builds
  reprodutíveis.
- Minimizar o número de camadas e o tamanho final da imagem.
- Toda imagem publicada passa por varredura automática de vulnerabilidades antes de ficar
  disponível para homologação ou produção; vulnerabilidades críticas bloqueiam a
  publicação.
