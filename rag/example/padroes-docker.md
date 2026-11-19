# Padrões Docker

> Documento fictício, criado para o MVP do DocAssist. Não reproduz nenhuma norma real.

## Arquivos de cada projeto

Todo projeto tem dois arquivos de imagem:

- **`Dockerfile`**: usado pelo pipeline para gerar a imagem que vai para os ambientes
  (dev, hml e prd). É multi-stage: o primeiro estágio compila e roda os testes, o último
  contém apenas o artefato final sobre uma imagem base mínima, roda com usuário sem
  privilégios e não inclui ferramentas de build.
- **`local.Dockerfile`**: usado apenas na máquina do desenvolvedor. Inclui ferramentas de
  depuração, recarregamento automático do código e monta o código-fonte como volume. Nunca
  é usado pelo pipeline.

Além deles, o `docker-compose.yml` sobe o projeto localmente junto com as dependências
(banco de dados, fila), sempre com o `local.Dockerfile`.

## Boas práticas de imagem

- Usar sempre uma tag fixa da imagem base (nunca `latest`).
- Copiar primeiro os arquivos de dependências e só depois o código, para aproveitar o cache.
- Manter um `.dockerignore` que exclua `.git`, segredos, logs e artefatos locais.
- Expor uma rota de verificação de saúde e declarar `HEALTHCHECK`.
- Não guardar segredos na imagem: eles entram por variáveis de ambiente no momento da
  execução.

## Tags das imagens

As imagens são publicadas no registro de artefatos com a versão semântica (`2.5.0`) e com
o hash curto do commit. A tag `latest` não é usada em nenhum ambiente.
