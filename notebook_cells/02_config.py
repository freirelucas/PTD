# ============================================================
# CÉLULA 2 — Configuração, Constantes e Estruturas de Dados
# ============================================================
import time, pickle, unicodedata, re, json, logging, difflib
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path
from datetime import datetime

import requests
import pandas as pd
from bs4 import BeautifulSoup
from tqdm.auto import tqdm

# --------------- URLs e parâmetros de rede ------------------
BASE_URL = ("https://www.gov.br/governodigital/pt-br/"
            "estrategias-e-governanca-digital/"
            "planos-de-transformacao-digital")
REQUEST_DELAY = 2.0        # segundos entre requests ao gov.br
MAX_RETRIES   = 4
REQUEST_TIMEOUT = 90
HTTP_HEADERS  = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.5",
}

# --------------- Vocabulários canônicos ---------------------
CANONICAL_EIXOS = [
    "Serviços Digitais e Melhoria da Qualidade",
    "Unificação de Canais Digitais",
    "Governança e Gestão de Dados",
    "Segurança e Privacidade",
    "Projetos Especiais",
]

# Mapa Eixo → lista de Produtos (44 produtos oficiais)
CANONICAL_PRODUTOS: Dict[str, List[str]] = {
    "Serviços Digitais e Melhoria da Qualidade": [
        "Disponibilização em Acesso Digital",
        "Disponibilização de datas/cronograma na Agenda Gov.Br",
        "Evolução do Serviço",
        "Implantação da Área Logada Gov.Br",
        "Implantação da Experiência LabQ",
        "Implementação do VLIBRAS",
        "Integração à ferramenta de acompanhamento das solicitações",
        "Integração à ferramenta de avaliação da satisfação dos usuários",
        "Realização de Autodiagnóstico de Qualidade",
        "Revisão da descrição dos serviços",
        "Oferta de agendamento digital",
        "Integração à ferramenta de solicitação de atendimento presencial",
        "Implantação do Atendimento Virtual",
    ],
    "Unificação de Canais Digitais": [
        "Implantação do Design System",
        "Integração ao Login Único",
        "Integração ao Pagtesouro",
        "Integração com Assinatura Digital Gov.br",
        "Migração de APPs móveis para a loja do Gov.br",
        "Migração de Portal Institucional",
        "Migração de Serviço para Plataforma Unificada",
    ],
    "Governança e Gestão de Dados": [
        "Abertura de bases de dados",
        "Adequação à LGPD",
        "Catalogação de bases de dados no Portal de Dados",
        "Criação de Comitê de Governança de Dados",
        "Elaboração de Plano de Dados Abertos",
        "Elaboração do PDTIC",
        "Elaboração/Revisão da POSIC",
        "Implantação de processo de gestão de dados",
        "Implantação do inventário de bases de dados",
        "Implementação da interoperabilidade de dados",
        "Integração de dados ao Conecta Gov.br",
        "Integração de dados ao Datamart",
        "Melhoria da qualidade de bases de dados",
        "Nomeação de Encarregado de Dados Pessoais",
        "Obtenção de certificação de bases de dados",
        "Publicação de dados no Portal de Dados Abertos",
        "Realização de Inventário de Dados",
        "Relatório de Impacto à Proteção de Dados Pessoais",
        "Resposta a demandas de compartilhamento",
        "Utilização de dados do Conecta Gov.br",
    ],
    "Segurança e Privacidade": [
        "Adequação ao Framework de Privacidade e Segurança da Informação",
        "Elevação do nível de maturidade em privacidade e segurança",
    ],
    "Projetos Especiais": [
        "Iniciativa de Transformação Digital",
        "Projeto Especial de Transformação Digital",
    ],
}

# Lista flat de todos os produtos para busca
ALL_PRODUTOS = [p for prods in CANONICAL_PRODUTOS.values() for p in prods]

# Mapa reverso: produto → eixo canônico
PRODUTO_TO_EIXO = {}
for eixo, prods in CANONICAL_PRODUTOS.items():
    for p in prods:
        PRODUTO_TO_EIXO[p] = eixo

# Escalas do Documento Diretivo (tabela de riscos)
PROBABILIDADE_SCALE = [
    "raro", "pouco provável", "provável",
    "muito provável", "praticamente certo",
]
IMPACTO_SCALE = [
    "muito baixo", "baixo", "médio", "alto", "muito alto",
]
TRATAMENTO_OPTIONS = ["mitigar", "eliminar", "transferir", "aceitar"]

# ---------- Órgãos que compartilham PDFs (grupos) ----------
ORGAN_GROUPS: Dict[str, List[str]] = {
    "MD":   ["MD", "CEX", "CM", "COMAER", "CENSIPAM", "FOSORIO", "HFA"],
    "MEC":  ["MEC", "CAPES", "EBSERH", "FNDE", "FUNDAJ", "IBC", "INEP", "INES"],
    "MF":   ["MF", "RFB", "STN", "PGFN"],
    "MMA":  ["MMA", "IBAMA", "ICMBIO", "SFB", "JBRJ"],
    "MT":   ["MT", "ANTT", "DNIT"],
    "MIDR": ["MIDR", "CODEVASF", "SUDAM", "SUDECO", "SUDENE"],
    "MDA":  ["MDA", "CONAB"],
}
# Reverso: sigla membro → sigla cabeça do grupo
MEMBER_TO_GROUP = {}
for head, members in ORGAN_GROUPS.items():
    for m in members:
        if m != head:
            MEMBER_TO_GROUP[m] = head

# --------------- Dataclasses --------------------------------
@dataclass
class OrganInfo:
    sigla: str
    nome_completo: str
    grupo: Optional[str] = None          # sigla do cabeça, se agrupado
    url_diretivo: Optional[str] = None
    url_entregas: Optional[str] = None
    pdf_path_diretivo: Optional[str] = None
    pdf_path_entregas: Optional[str] = None

@dataclass
class RiskEntry:
    orgao_sigla: str
    risco_texto: str = ""
    probabilidade_original: str = ""
    probabilidade_normalizada: str = ""
    impacto_original: str = ""
    impacto_normalizado: str = ""
    tratamento_original: str = ""
    tratamento_normalizado: str = ""
    acoes_tratamento: str = ""
    extraction_confidence: str = "high"    # high / medium / low
    needs_review: bool = False
    review_reason: Optional[str] = None

@dataclass
class DeliveryEntry:
    orgao_sigla: str
    tabela_tipo: str = ""                  # pactuada / concluida / cancelada
    servico_acao: str = ""
    produto_original: str = ""
    produto_normalizado: str = ""
    eixo_original: str = ""
    eixo_normalizado: str = ""
    area_responsavel: Optional[str] = None
    data_pactuada: Optional[str] = None
    data_entrega: Optional[str] = None
    pactuado: Optional[str] = None         # Sim / Não (concluídas)
    justificativa: Optional[str] = None    # (canceladas)
    extraction_confidence: str = "high"
    needs_review: bool = False
    review_reason: Optional[str] = None

@dataclass
class ProcessingError:
    orgao_sigla: str
    document_type: str     # diretivo / entregas
    stage: str             # download / extraction / standardization
    error_type: str
    error_message: str
    timestamp: str = ""
    url: Optional[str] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

# Contêineres globais
all_organs: List[OrganInfo] = []
all_risks: List[RiskEntry] = []
all_deliveries: List[DeliveryEntry] = []
all_errors: List[ProcessingError] = []

print(f"Configuração carregada: {len(ALL_PRODUTOS)} produtos canônicos em {len(CANONICAL_EIXOS)} eixos")