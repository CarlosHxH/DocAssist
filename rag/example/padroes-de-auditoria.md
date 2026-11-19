# Padrões de Auditoria

> Documento fictício, criado para o MVP do DocAssist. Não reproduz nenhuma norma real.

Todo sistema deve registrar três tipos de log de auditoria: **logs de acesso**, **logs de
operações** e **logs de entidades**. Os três são enviados à plataforma central de logs e
guardados por cinco anos.

## Logs de acesso

Registram cada tentativa de autenticação e cada encerramento de sessão: data e hora com
fuso, identificador do usuário, endereço de origem, resultado (sucesso ou falha) e motivo
da falha. Tentativas que falham cinco vezes seguidas geram alerta para o time de segurança.

## Logs de operações

Registram as ações de negócio executadas pelo usuário (emitir, aprovar, cancelar,
exportar). Cada registro contém o usuário, a operação, os parâmetros relevantes (sem dados
sensíveis), o resultado e o identificador de correlação (`correlation_id`) da requisição.

## Logs de entidades

Registram as alterações em entidades persistidas: tabela, chave do registro, tipo de
alteração (inclusão, alteração, exclusão), valores anteriores e novos e o usuário
responsável. São gravados na mesma transação da alteração, para que nunca exista mudança
sem registro.

## Regras gerais

- Logs de auditoria nunca podem ser alterados nem excluídos pela aplicação.
- Senhas, tokens e documentos pessoais não podem aparecer em nenhum log; campos assim são
  mascarados.
- Todo registro leva o `correlation_id`, para que os três tipos de log possam ser cruzados
  durante uma investigação.
