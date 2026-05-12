## 11d. Fila de Revisão Humana — `PTD_REVIEW`

Agrega casos não-canonizáveis (`fuzzy_low`, `unmatched`, `fuzzy_high` baixa-confiança) por `(field, original)`, anexando sugestão canônica, score, método de match, contagem e até 5 exemplos contextuais. O dashboard expõe esta estrutura num painel "Revisão" com filtros, ordenação por impacto e snippet de alias copiável — turnam o tail invisível em fila acionável.

A cardinalidade do array é proporcional aos `*_original` distintos no tail; o conjunto de **categorias** continua fixo (5 escalas + 5 buckets de `*_method`).
