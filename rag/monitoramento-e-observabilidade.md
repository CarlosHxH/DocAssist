# Monitoramento e Observabilidade

> Documento fictício, criado para o MVP do DocAssist. Não reproduz nenhuma norma real.

## Painéis de cada sistema

Todo sistema em produção tem três painéis na ferramenta de observabilidade:

1. **Painel de saúde**: disponibilidade, taxa de erros e tempo de resposta (p50, p95, p99).
2. **Painel de infraestrutura**: uso de CPU, memória e réplicas ativas por namespace.
3. **Painel de negócio**: volume das principais operações do sistema (ex.: agendamentos
   criados por hora).

## Alertas

- Taxa de erros acima de 2% por cinco minutos: alerta para o time responsável.
- Tempo de resposta p95 acima de dois segundos por dez minutos: alerta para o time.
- Sistema indisponível na verificação de saúde: alerta imediato para o plantão.

## Rastreamento de requisições

Cada requisição recebe um `correlation_id` na entrada (gerado pelo gateway ou pela própria
aplicação) que é repassado a todas as chamadas seguintes e gravado em todos os logs, nos
traces e nos logs de auditoria.

## Investigação de incidentes

Durante um incidente, a correlação de logs é feita pelo `correlation_id`: o time encontra
uma requisição com erro no painel de saúde, copia o identificador e filtra por ele na
plataforma central de logs, vendo em ordem tudo o que aconteceu em cada serviço. O trace
distribuído com o mesmo identificador mostra em qual chamada o tempo foi gasto. Ao final, o
time registra a linha do tempo e a causa no relatório do incidente.
