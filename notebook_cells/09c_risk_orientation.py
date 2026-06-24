# ============================================================
# CÉLULA 09C — Orientação do risco e subtipo de exclusão digital
# ============================================================
# Camada de classificação sobre `risco_texto` (NÃO altera a extração da
# célula 7 nem a padronização da 9b). Roda após a padronização e antes do
# export, derivando três campos por regex auditável:
#
#   - orientacao_risco       ∈ {cidadao, estado, ambos, indefinido}
#   - subtipo_exclusao       ∈ {digital_only, acessibilidade,
#                               disponibilidade_uptime, nenhum}
#   - orientacao_confidence  ∈ {alta, baixa}   (baixa = sinal fraco/ambíguo)
#
# Motivação (nota técnica): a matriz de risco do PTD registra majoritariamente
# riscos ENDÓGENOS ao Estado (fornecedor, equipe, orçamento, cronograma). A
# dimensão DISTRIBUTIVA — o serviço digital excluir o cidadão sem acesso,
# dispositivo ou letramento — aparece em pouquíssimos riscos. Esta célula
# isola essa dimensão para quantificá-la.
#
# AUDITORIA: os padrões ficam como CONSTANTES NOMEADAS abaixo, comentadas,
# para revisão manual. Há falsos positivos esperados (o léxico de orientação
# é heurístico) — por isso `orientacao_confidence`. A classificação é
# determinística e idempotente; reexecutar não muda o resultado.
import re
import unicodedata


def _ro_norm(text):
    """Minúsculas, sem acento, espaços colapsados — base para os regex."""
    t = unicodedata.normalize("NFKD", str(text or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().lower()


# ------------------------------------------------------------------
# TABELA DE PADRÕES DE EXCLUSÃO (ordem = prioridade na classificação)
# ------------------------------------------------------------------
# Aplicados sobre o texto JÁ normalizado (sem acento, minúsculo). O primeiro
# subtipo que casar vence. digital_only e acessibilidade (exclusão real) têm
# prioridade sobre disponibilidade_uptime (falso-amigo técnico).
EXCLUSAO_PATTERNS = {
    # Serviço ofertado só por canal digital, excluindo quem não tem acesso.
    # Inclui o radical `exclus` (corrige cobertura: pega "risco de exclusão
    # digital", que padrões só de "digital only" perdem).
    "digital_only": (
        r"(somente|exclusivamente|apenas|unica)[^.]{0,20}\bdigital"
        r"|digital[\s\-]?only"
        r"|exclusao\s+digital"
        r"|barreira[^.]{0,35}(acesso|dispositivo|digital|internet)"
        r"|nao\s+(possu|tem|teria|dispoe)[^.]{0,25}(acesso|dispositivo|internet|celular)"
    ),
    # Acessibilidade / inclusão de grupos específicos. Tokens de ALTA precisão:
    # `vulnerab` (pega "vulnerabilidade de segurança") e o radical solto
    # `defici` (pega "deficiência de recursos") foram DELIBERADAMENTE excluídos
    # por gerarem falso-positivo — exige-se contexto de pessoa/disability.
    "acessibilidade": (
        r"acessibilidade|\blibras\b|letrament|analfabet|inclusao\s+digital"
        r"|pessoas?\s+com\s+defici|baixa\s+escolaridade|\bidos[oa]s?\b"
    ),
    # FALSO-AMIGO: (in)disponibilidade/uptime de sistema. É risco TÉCNICO de
    # operação, NÃO de exclusão distributiva — mantido separado de propósito
    # para a NT mostrar a distinção. Exige `sistema/plataforma/portal` perto de
    # `(in)disponibilidade` (evita pegar "indisponibilidade dos donos de
    # serviço", que é risco de pessoal, não de uptime).
    "disponibilidade_uptime": (
        r"(in)?disponibilidade[^.]{0,40}(sistema|plataforma|portal)"
        r"|sistemas?\s+de\s+acesso\s+para\s+o\s+cidad"
    ),
}

# ------------------------------------------------------------------
# LÉXICO DE ORIENTAÇÃO (sujeito afetado pelo risco)
# ------------------------------------------------------------------
# cidadao: usuário externo / sociedade / público-alvo do serviço.
ORIENT_CIDADAO = (
    r"\bcidad|usuari[oa]s?\s+(final|externo|do servico)|popula(c|ç)"
    r"|sociedade|publico[\s\-]?alvo|benefici|requerente|contribuinte"
    r"|exclusao\s+digital|acessibilidade|\bidos[oa]s?\b|pessoas?\s+com\s+defici"
)
# estado: órgão / projeto / fornecedor / equipe / orçamento (endógeno).
ORIENT_ESTADO = (
    r"fornecedor|contrat|equipe|servidor|pessoal|rotativ|or(c|ç)ament"
    r"|capacidade\s+(tecnica|interna|operacional)|governan(c|ç)|projeto"
    r"|cronograma|prazo|area\s+de\s+negocio|gestao|infraestrutura|legado"
    r"|recurso|integra(c|ç)|resistencia|engajamento|patrocin|priori"
    r"|capacita|treinament|metodolog|escopo|complexidade|maturidade"
    r"|tecnologia|sistema legado|aquisic|licita"
)


def classify_risk_orientation(risco_texto):
    """Classifica um texto de risco. Retorna (orientacao, subtipo, confianca).

    Determinística e tolerante a texto vazio/ruidoso (não levanta exceção).
    """
    norm = _ro_norm(risco_texto)
    if not norm:
        return ("indefinido", "nenhum", "baixa")

    # --- subtipo de exclusão (prioridade pela ordem do dict) ---
    subtipo = "nenhum"
    for nome, pattern in EXCLUSAO_PATTERNS.items():
        if re.search(pattern, norm):
            subtipo = nome
            break

    # --- orientação ---
    has_cid = bool(re.search(ORIENT_CIDADAO, norm))
    has_est = bool(re.search(ORIENT_ESTADO, norm))
    # Exclusão explícita (digital_only/acessibilidade) é, por definição,
    # voltada ao cidadão — força o sinal mesmo que o léxico não pegue.
    if subtipo in ("digital_only", "acessibilidade"):
        has_cid = True

    if has_cid and has_est:
        orientacao = "ambos"
    elif has_cid:
        orientacao = "cidadao"
    elif has_est:
        orientacao = "estado"
    else:
        orientacao = "indefinido"

    # --- confiança ---
    # alta: exclusão explícita OU exatamente um lado do léxico acionado.
    # baixa: ambíguo (ambos), sem sinal (indefinido), ou só uptime.
    if subtipo in ("digital_only", "acessibilidade"):
        confianca = "alta"
    elif orientacao in ("cidadao", "estado"):
        confianca = "alta"
    else:
        confianca = "baixa"

    return (orientacao, subtipo, confianca)


def annotate_risk_orientation(risks):
    """Aplica a classificação a uma lista de RiskEntry (in-place)."""
    for r in risks:
        orient, subtipo, conf = classify_risk_orientation(r.risco_texto)
        r.orientacao_risco = orient
        r.subtipo_exclusao = subtipo
        r.orientacao_confidence = conf
    return risks


# ---- Execução (no notebook; descartada no carregamento defs-only dos testes) ----
if "all_risks" in globals() and all_risks:
    annotate_risk_orientation(all_risks)
    from collections import Counter as _Counter
    _orient_ct = _Counter(r.orientacao_risco for r in all_risks)
    _subt_ct = _Counter(r.subtipo_exclusao for r in all_risks)
    print("=" * 60)
    print("ORIENTAÇÃO DO RISCO (célula 09c)")
    print("=" * 60)
    print("  orientacao_risco:", dict(_orient_ct.most_common()))
    print("  subtipo_exclusao:", dict(_subt_ct.most_common()))
    _n_excl = sum(1 for r in all_risks
                  if r.subtipo_exclusao in ("digital_only", "acessibilidade"))
    _org_excl = sorted({r.orgao_sigla for r in all_risks
                        if r.subtipo_exclusao in ("digital_only", "acessibilidade")})
    print(f"  exclusão digital (digital_only|acessibilidade): "
          f"{_n_excl} riscos em {len(_org_excl)} órgãos — {', '.join(_org_excl)}")
    print("=" * 60)
