# Errata para a Nota Técnica (NT_PTDBR_Corpus_NT_4.docx)

Worksheet de correção para os autores aplicarem no `.docx` (o arquivo não está
no repositório). Cada item traz **onde**, **texto atual → texto corrigido** e a
fonte do valor. Fonte única dos números: `output/nota_tecnica_insumos.md`
(regenerado por `notebook_cells/11e_nt_insumos.py` sobre o snapshot
**2026-05-12**, commit `0d14ecd4`). Justificativas: `BALANCO_CONSISTENCIA.md`.

> Se a NT for atualizada para um run mais novo (handout §8 menciona dados ainda
> não commitados), regenerar os insumos primeiro e usar os novos valores — as
> correções abaixo valem para o snapshot 2026-05-12.

## A. Capa, data e formais

| # | Onde | Atual → Corrigido |
|---|---|---|
| A1 | Capa e Sinopse | "Abril de 2026" / "coletados em abril de 2026" → **"Maio de 2026"** / "coletados em maio de 2026" (manifest: 2026-05-12) — 3 ocorrências (capa, sinopse, §4) |
| A2 | Capa | "Nº XX/2026/Diest" → preencher o número definitivo antes da publicação |
| A3 | §4 + seção Agradecimentos | Declaração de uso de IA aparece **duplicada** (texto idêntico) → manter apenas na seção "Agradecimentos e Declaração de Uso de IA" |
| A4 | Todo o texto | Uniformizar grafia da sigla: dados usam `SGPR`; a NT usa `SG-PR` — escolher uma e aplicar globalmente |

## B. Totais e cobertura

| # | Onde | Atual → Corrigido |
|---|---|---|
| B1 | Tabela 5 (rodapé) e Ap. D.1 | Total de entregas "4.573" → **4.574** (sinopse e Tabela 3 já trazem 4.574) |
| B2 | Tabela 1, Ap. D.1 | Total de riscos "595" → **619** (sinopse e descrição do risks.csv já trazem 619) |
| B3 | Tabela 1 / §3.1 cobertura de riscos | "595 registros de 71 órgãos" / "71 de 86 (83%)" → **619 registros de 76 órgãos (51 próprios + 25 compartilhados); cobertura 83,5% (76/91)**. Se preferir o denominador 86 (= 91 − 5 sem Documento Diretivo), declarar: 76/86 = 88,4% |
| B4 | §2.1 (metodologia, contagem de PDFs) | "86 Diretivos + 91 Entregas = 177 PDFs … 98 únicos" → **61 Diretivos + 65 Entregas = 126 PDFs … 58 únicos** (valores do manifest do snapshot; os anteriores eram de run antigo) |

## C. Entregas

| # | Onde | Atual → Corrigido |
|---|---|---|
| C1 | Tabela 5 | Serviços Digitais "2.414 (52,8%)" → **2.418 (52,9%)**; Segurança e Privacidade "654 (14,3%)" → **644 (14,1%)**; Projetos Especiais "140 (3,1%)" → **148 (3,2%)**; Governança "124" → **123 (2,7%)**; total → **4.574 (100%)** |
| C2 | Ap. D.1 (eixos) | Governança "124" → **123**; demais valores de D.1 conferem (2.418/1.241/644/148) |
| C3 | §3.2 / Tabela 5 nota | "Integração à base de dados (110)" → **109**; o par de legados PPSI+Integração soma **452 (9,9%)**, não 453. Atenção: "Auto-avaliação… PPSI" (300) também é produto legado — se a NT citar "2 legados", reformular para "produtos legados com pactuação: PPSI 343, Auto-avaliação PPSI 300, Integração à base de dados 109, Interoperabilidade de Sistemas 14, além de 'Outros' 148" |
| C4 | §3.2 ("20 dos 44 canônicos…") | "20 aparecem ao menos uma vez; 24 têm zero" → **"16 dos 44 produtos canônicos têm ≥1 pactuação; 28 têm zero (os demais produtos pactuados são legados)"** |
| C5 | §2.4/Tabela 1 (padronização) | "93,2% correspondência exata; 6,8% fuzzy" (e qualquer resquício de "90,7%/9,3%") → **"73,4% match exato, 15,0% por alias determinístico (88,4% determinístico) e 11,6% por fuzzy ≥0,85; 0 não-reconhecidos"** (campo `produto_method`) |
| C6 | §2.4 (limiar) | "limiar fuzzy ≥ 0,85" → esclarecer: **aceite em 0,80; ≥0,85 sem revisão (`fuzzy_high`); 0,70–0,85 aceito com `needs_review`** |
| C7 | §3.2 (datas) | "Trinta por cento das datas… em dezembro" → **27,6% (das 2.903 datas parseáveis)** |
| C8 | Se houver menção à concentração (Lorenz) | "20% dos órgãos concentram mais da metade" → **"os 11 maiores órgãos (20%) detêm 49,3%"** |

## D. Riscos

| # | Onde | Atual → Corrigido |
|---|---|---|
| D1 | Figura 8 / §3.3 ("439 (74%)… 156 restantes dos quatro órgãos com colunas trocadas: CENSIPAM (26), ANTAQ (26), PRF (14), SUSEP (9)") | Narrativa de run antigo, pré-correção de column-shift. → **"592 riscos (95,6%) com probabilidade E impacto canônicos; 27 residuais concentrados em: DNOCS (6), MPOR (5), CVM (4), CADE (3), CENSIPAM (3), MJSP (2), IBAMA (1), IBGE (1), MMULHERES (1), PRF (1)"** |
| D2 | Tabela 6 (distribuição de probabilidade) | "Provável 182, Pouco provável 173, Muito provável 42, Raro 26, Praticamente certo 20" (sobre o subconjunto antigo) → **provável 234 · pouco provável 243 · muito provável 68 · raro 37 · praticamente certo 22 (604 canônicos, 97,6%)** |
| D3 | Tabela 6 (impacto) | "Alto 205, Médio 146, Muito alto 108, Baixo 45" → **alto 262 · médio 155 · muito alto 138 · baixo 46 (601 canônicos, 97,1%)** |
| D4 | Tabela 6 vs Ap. D.1 (tratamento) | Harmonizar com denominador explícito: **mitigar 487 = 84,1% dos 579 tratamentos simples = 78,7% dos 619 riscos; aceitar 60 (10,4%/9,7%); transferir 19 (3,3%/3,1%); eliminar 13 (2,2%/2,1%); +5 compostos; 18 vazios; 17 fora da escala (total canônico 584 = 94,3%)** |
| D5 | Ap. D.1 (zona crítica) | 218 ✓ confere com os dados — **manter 218** (ignorar o "141" do handout/insumos antigo) |
| D6 | Ap. D.1 (severidade máxima) | "11 registros… ANATEL, ANA, CAPES, INSS, MDHC, MME, MPO, MRE (2), SG-PR (2)" → **13 registros: ANA, ANATEL, CAPES, INSS, MDHC, MESP, MME, MPO (2), MRE (2), SGPR (2)** |
| D7 | §3.3 (ações de tratamento) | "23% ou 26 de 619 (4,2%)" (redação confusa; e descartar o "30%" do handout) → **"26 riscos (4,2%) sem ações de tratamento registradas"** |
| D8 | §3.3 (texto padrão SGD) | "52% reproduzem texto referencial (idêntico em ≥3 órgãos)" → **50,2% (311 riscos)** com a definição explícita: texto normalizado idêntico em ≥3 órgãos distintos |
| D9 | §3.3 (fornecedores) | "23 riscos em 22 órgãos… 15 na zona crítica" → **28 riscos em 26 órgãos próprios; 16 na zona crítica** (keyword "fornecedor" em `risco_texto`) |
| D10 | Se citado ("12 órgãos usam exclusivamente mitigar") | → **22 órgãos** (lista no insumos regenerado) |
| D11 | §3.3 (risco de pessoal, "24% dos órgãos não mencionam") | → **10 de 51 órgãos (20%)**, com a definição por keywords (pessoal/rotatividade/equipe/servidor/capacita) declarada |

## E. Metodologia e estrutura

| # | Onde | Atual → Corrigido |
|---|---|---|
| E1 | §2.6 (estrutura do corpus) | Schemas antigos ("9 colunas" / "11 colunas", com `id_risco`, `acoes_original`, `acoes_resolvidas`) → **deliveries.csv 19 colunas; risks.csv 18 colunas** (listas completas no insumos regenerado, seção 2.6) |
| E2 | §2.4 (contagem de aliases) | "19 aliases de produto / 10 de eixo" → **29 de produto / 14 de eixo** (após as correções deste ciclo; o gerador atualiza sozinho) |
| E3 | §2 (após próximo run) | Quando o pipeline rodar com o filtro de fragmentos, o corpus de entregas cai para ≈**4.545** (−29 fragmentos de 'Outros') — atualizar tabelas/figuras com o `nota_tecnica_insumos.md` regenerado |
| E4 | Apêndice E (91 órgãos) | Recontar `n_entregas`/`n_riscos` a partir dos CSVs do snapshot final antes de publicar (a tabela atual mistura runs) |

## F. Processo (recomendação ao fluxo editorial)

1. Antes de cada revisão da NT: `python notebook_cells/11e_nt_insumos.py output`
   e usar SOMENTE os números do `output/nota_tecnica_insumos.md` (carimbado com
   snapshot+commit). O teste `test_insumos_commitado_consistente_com_csvs`
   garante que o arquivo commitado nunca diverge dos CSVs.
2. Citar na NT o snapshot usado (data + commit), como o insumos já faz.
3. Decreto nº 12.198/2024 vs Portaria SGD/MGI nº 6.618/2024: a NT usa o
   Decreto para a EFGD e a Portaria para os PTDs — uso está correto; manter
   ambos nas referências (handout citava só a Portaria).
