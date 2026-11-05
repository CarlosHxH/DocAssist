# Processo de Deploy

Este documento descreve como o deploy de aplicações acontece nos três ambientes do IHT:
desenvolvimento, homologação e produção.

## Desenvolvimento

O deploy em desenvolvimento é automático. Qualquer push nas branches `develop` ou em
branches `test/*` dispara a pipeline, que builda a imagem, roda os testes automatizados e,
se tudo passar, publica automaticamente no cluster de desenvolvimento. Não é necessário
aprovação humana nesta etapa.

## Homologação

O deploy em homologação também é automático, mas só é disparado a partir de branches
`release/x.y.z`. A pipeline builda uma imagem com a tag da release, roda a suíte completa
de testes de integração e publica no cluster de homologação. A equipe de QA valida a
versão homologada antes de autorizar a promoção para produção.

## Produção

O deploy em produção **é manual e exige aprovação em cadeia**. O fluxo é:

1. A imagem já testada em homologação é marcada como candidata a produção.
2. O responsável técnico abre um chamado no sistema de atendimento interno (ServiceDesk)
   descrevendo a mudança, o risco e o plano de rollback.
3. O chamado passa por aprovação do analista da equipe solicitante, do Product Owner (PO)
   responsável pelo sistema e, por fim, da equipe de operações (squad de infraestrutura),
   que efetivamente executa a publicação da imagem no cluster de produção.
4. Após o deploy, o responsável técnico registra a evidência de execução no próprio
   chamado (prints, logs ou relatório de smoke test).

Esse processo é propositalmente mais lento em produção para reduzir risco de incidentes,
mas é 100% manual — não existe automação hoje que gere o rascunho do chamado, resuma a
mudança a partir dos commits ou valide automaticamente se o checklist de pré-requisitos
foi cumprido.

## Rollback

Em caso de problema identificado após o deploy em produção, o rollback segue o mesmo fluxo
de aprovação, porém com prioridade máxima (chamado classificado como "emergencial"), e o
squad de infraestrutura pode executar a reversão para a última tag estável sem aguardar
todas as aprovações, desde que comunique a decisão em até 1 hora após a ação.
