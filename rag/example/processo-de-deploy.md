# Processo de Deploy

> Documento fictício, criado para o MVP do DocAssist. Não reproduz nenhuma norma real.

## Ambientes

| Ambiente | Origem | Gatilho | Aprovação |
|----------|--------|---------|-----------|
| Desenvolvimento (`dev`) | branch `develop` | automático a cada merge | não precisa |
| Homologação (`hml`) | tag `-rc.N` | manual, pelo time | líder técnico |
| Produção (`prd`) | tag final `vX.Y.Z` | manual, em janela de mudança | líder técnico + gestor do serviço |

## Deploy em desenvolvimento

O deploy em desenvolvimento é totalmente automático: todo merge em `develop` dispara o
pipeline, que roda os testes, gera a imagem e atualiza o namespace `<sistema>-dev`. Não há
aprovação humana nesse ambiente, porque ele pode ser quebrado e restaurado a qualquer momento.

## Deploy em produção

1. O time abre uma requisição de mudança com a versão, o resumo das alterações, o plano de
   rollback e o resultado da homologação.
2. O líder técnico e o gestor do serviço aprovam a requisição.
3. O deploy é feito dentro da janela de mudança (terças e quintas, das 19h às 21h), pelo
   job manual `deploy:prd` do pipeline, usando a mesma imagem já validada em homologação.
4. A estratégia é rolling update: as réplicas novas só recebem tráfego depois de passar na
   verificação de saúde (`/health`).
5. Após o deploy, o time acompanha os painéis de monitoramento por 30 minutos.

## Rollback

Se a taxa de erros passar de 2% ou a verificação de saúde falhar, o time executa o job
`rollback:prd`, que reaplica a imagem da versão anterior. Migrations de banco precisam ser
compatíveis com a versão anterior para que o rollback seja possível (ver o guia de
migrations).

## Hotfix

Hotfixes seguem o mesmo fluxo de produção, mas podem ser publicados fora da janela de
mudança com a aprovação do gestor do serviço, desde que exista um incidente aberto.
