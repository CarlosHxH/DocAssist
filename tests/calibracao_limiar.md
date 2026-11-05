# Calibração do limiar de similaridade (SIMILARITY_THRESHOLD)

O pipeline recusa responder quando a melhor similaridade de cosseno entre a pergunta e os
trechos indexados fica abaixo de um limiar — isso é o que evita alucinação em perguntas
fora do escopo da base. O limiar foi calibrado empiricamente rodando perguntas dentro e
fora do escopo e observando a separação dos scores.

## Perguntas dentro do escopo (esperado: score alto)

| Pergunta | Melhor score |
|---|---|
| Qual o padrão de nome para branch de hotfix? | 0.608 |
| Como funciona o deploy em produção? | 0.794 |
| Quais pastas organizam os scripts de migration? | 0.661 |
| Qual prefixo os papéis compartilhados entre sistemas usam no provedor de identidade? | 0.659 |

## Perguntas fora do escopo (esperado: score baixo)

| Pergunta | Melhor score |
|---|---|
| Qual a capital da França? | 0.351 |
| Que time vai ganhar a copa do mundo de 2026? | 0.378 |
| Qual a melhor receita de bolo de chocolate? | 0.380 |

## Decisão

Os scores dentro do escopo ficaram sempre acima de 0.51; os fora do escopo, sempre abaixo
de 0.38. O limiar foi definido em **0.40**, no meio dessa margem, para separar os dois
grupos com folga. Esse valor é específico do modelo de embeddings usado (`all-minilm`) e
do corpus; se o corpus crescer ou o modelo mudar, a calibração deve ser refeita (rodar os
testes acima novamente e ajustar `rag.SIMILARITY_THRESHOLD`).
