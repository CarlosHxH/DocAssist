# Monitoramento e Observabilidade

## Painéis por sistema

Cada sistema em produção possui um conjunto padrão de painéis de observabilidade:

- **Visão Geral**: disponibilidade, taxa de erro agregada, uso de CPU/memória dos
  pods/instâncias.
- **Transações**: tempo de resposta por endpoint/rota, percentis (p50, p95, p99).
- **Dependências**: latência e taxa de erro nas chamadas a serviços externos (outros
  sistemas, banco de dados, filas).
- **Erros**: lista de exceções capturadas, agrupadas por tipo e frequência, com
  possibilidade de abrir o detalhe de uma ocorrência específica.

## Correlação de logs

Cada requisição recebe um identificador único de rastreamento (trace id), propagado entre
todos os serviços envolvidos no atendimento daquela requisição. Para investigar um
incidente, a prática recomendada é: localizar o erro no painel de Erros, copiar o trace id
associado, e usar esse id para filtrar o stream de logs e reconstruir toda a linha do
tempo da requisição — entrada, chamadas internas, chamadas externas e resposta final.

## Alertas

Alertas automáticos disparam notificação para o canal de plantão quando: taxa de erro de
um sistema ultrapassa um limiar por mais de 5 minutos consecutivos, latência p95 de algum
endpoint crítico dobra em relação à média da última semana, ou um serviço fica
indisponível (health check falhando).

## Prática atual de triagem

Hoje, quando um alerta dispara, a triagem inicial é manual: a pessoa de plantão precisa
abrir o painel de Erros, ler a stacktrace, correlacionar com o log completo via trace id, e
decidir se é um problema conhecido, uma regressão nova, ou uma falha de dependência
externa, antes de decidir se aciona o time responsável pelo sistema. Não existe hoje um
resumo automático que explique a causa provável de um erro a partir do stacktrace e do
contexto de logs correlacionados.
