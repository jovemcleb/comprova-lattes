"""Tabelas explícitas de mapeamento XML Lattes -> schemas canônicos.

Baseadas em `.specs/features/m1-parser/xml-mapping.md`, `grammar-analysis.md`,
`event-role-contract.md` e no XSD oficial do Extrator CNPq (AD-011 / AD-012).
"""

from __future__ import annotations

import re
import unicodedata

from comprova_lattes.schemas import ActivityStatus, LattesCategory

_WHITESPACE_RE = re.compile(r"\s+")

ACADEMIC_TAG_SUBTYPES: dict[str, str] = {
    "GRADUACAO": "GRADUACAO",
    "ESPECIALIZACAO": "ESPECIALIZACAO",
    "MESTRADO": "MESTRADO",
    "MESTRADO-PROFISSIONALIZANTE": "MESTRADO_PROFISSIONALIZANTE",
    "DOUTORADO": "DOUTORADO",
    "POS-DOUTORADO": "POS_DOUTORADO",
    "LIVRE-DOCENCIA": "LIVRE_DOCENCIA",
    "ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU": "ENSINO_FUNDAMENTAL",
    "ENSINO-MEDIO": "ENSINO_MEDIO",
    "ENSINO-MEDIO-SEGUNDO-GRAU": "ENSINO_MEDIO",
    "CURSO-TECNICO-PROFISSIONALIZANTE": "CURSO_TECNICO_PROFISSIONALIZANTE",
    "RESIDENCIA-MEDICA": "RESIDENCIA_MEDICA",
    "APERFEICOAMENTO": "APERFEICOAMENTO",
}

COMPLEMENTARY_TAG_SUBTYPES: dict[str, str] = {
    "FORMACAO-COMPLEMENTAR-DE-EXTENSAO-UNIVERSITARIA": "EXTENSAO_UNIVERSITARIA",
    "FORMACAO-COMPLEMENTAR-CURSO-DE-CURTA-DURACAO": "CURTA_DURACAO",
    "FORMACAO-COMPLEMENTAR-CURTA-DURACAO": "CURTA_DURACAO",
    "MBA": "MBA",
    "OUTROS-TIPOS-DE-FORMACAO-COMPLEMENTAR": "OUTROS",
    "OUTROS": "OUTROS",
}

EVENT_TAG_SUBTYPES: dict[str, str] = {
    "PARTICIPACAO-EM-CONGRESSO": "CONGRESSO",
    "PARTICIPACAO-EM-SEMINARIO": "SEMINARIO",
    "PARTICIPACAO-EM-SIMPOSIO": "SIMPOSIO",
    "PARTICIPACAO-EM-OFICINA": "OFICINA",
    "PARTICIPACAO-EM-ENCONTRO": "ENCONTRO",
    "PARTICIPACAO-EM-EXPOSICAO": "EXPOSICAO",
    "PARTICIPACAO-EM-FEIRA": "FEIRA",
    "PARTICIPACAO-EM-OLIMPIADA": "OLIMPIADA",
    "OUTRAS-PARTICIPACOES-EM-EVENTOS": "OUTRAS_PARTICIPACOES",
    "OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS": "OUTRAS_PARTICIPACOES",
}

TECHNICAL_PRODUCTION_TAG_CATEGORIES: dict[str, LattesCategory] = {
    "APRESENTACAO-DE-TRABALHO": LattesCategory.APRESENTACAO_TRABALHO,
    "ORGANIZACAO-DE-EVENTO": LattesCategory.ORGANIZACAO_EVENTO,
}

TECHNICAL_PRODUCTION_TAG_SUBTYPES: dict[str, str] = {
    "APRESENTACAO-DE-TRABALHO": "APRESENTACAO_DE_TRABALHO",
    "ORGANIZACAO-DE-EVENTO": "ORGANIZACAO_DE_EVENTO",
}

# Tags válidas do XSD dentro de DEMAIS-TIPOS-DE-PRODUCAO-TECNICA fora do escopo AD-012.
OUT_OF_SCOPE_TECHNICAL_PRODUCTION_TAGS: frozenset[str] = frozenset(
    {
        "CARTA-MAPA-OU-SIMILAR",
        "CURSO-DE-CURTA-DURACAO-MINISTRADO",
        "DESENVOLVIMENTO-DE-MATERIAL-DIDATICO-OU-INSTRUCIONAL",
        "EDITORACAO",
        "MANUTENCAO-DE-OBRA-ARTISTICA",
        "MAQUETE",
        "PROGRAMA-DE-RADIO-OU-TV",
        "RELATORIO-DE-PESQUISA",
        "MIDIA-SOCIAL-WEBSITE-BLOG",
        "OUTRA-PRODUCAO-TECNICA",
    }
)

STATUS_TOKEN_MAP: dict[str, ActivityStatus] = {
    "CONCLUIDO": ActivityStatus.CONCLUIDO,
    "CONCLUÍDO": ActivityStatus.CONCLUIDO,
    "EM_ANDAMENTO": ActivityStatus.EM_ANDAMENTO,
    "EM ANDAMENTO": ActivityStatus.EM_ANDAMENTO,
    "EM-ANDAMENTO": ActivityStatus.EM_ANDAMENTO,
    "INCOMPLETO": ActivityStatus.INCOMPLETO,
    "PARTICIPOU": ActivityStatus.PARTICIPOU,
    "INDEFINIDO": ActivityStatus.INDEFINIDO,
}

# Equivalências estritamente inequívocas para papel de participação em eventos (AD-010).
# Valores desconhecidos permanecem None em `participation_role` com valor bruto preservado.
PARTICIPATION_ROLE_MAP: dict[str, str] = {
    "ouvinte": "OUVINTE",
    "palestrante": "PALESTRANTE",
    "conferencista": "PALESTRANTE",
    "apresentador": "APRESENTADOR",
    "apresentadora": "APRESENTADOR",
    "apresentacao de trabalho": "APRESENTADOR",
    "organizador": "ORGANIZADOR",
    "organizadora": "ORGANIZADOR",
    "comissao organizadora": "ORGANIZADOR",
    "participante": "PARTICIPANTE",
    "congressista": "PARTICIPANTE",
}

_XSD_AND_DTD_CONFIRMED_NOTE = (
    "Tag confirmada no XSD do Extrator e na DTD comunitária; "
    "conformidade com exportação da UI não verificada."
)
_XSD_ONLY_CONFIRMED_NOTE = (
    "Tag confirmada no XSD oficial do Extrator (ausente da DTD comunitária); "
    "conformidade com exportação da UI não verificada."
)
_LEGACY_ONLY_NOTE = (
    "Fallback legado ausente do XSD oficial do Extrator e da DTD comunitária; "
    "conformidade com exportação da UI não verificada."
)

UNVERIFIED_VARIANT_TAGS: dict[str, str] = {
    "MESTRADO-PROFISSIONALIZANTE": _XSD_AND_DTD_CONFIRMED_NOTE,
    "POS-DOUTORADO": _XSD_AND_DTD_CONFIRMED_NOTE,
    "LIVRE-DOCENCIA": _XSD_AND_DTD_CONFIRMED_NOTE,
    "RESIDENCIA-MEDICA": _XSD_AND_DTD_CONFIRMED_NOTE,
    "ENSINO-MEDIO": _LEGACY_ONLY_NOTE,
    "ENSINO-MEDIO-SEGUNDO-GRAU": _XSD_AND_DTD_CONFIRMED_NOTE,
    "FORMACAO-COMPLEMENTAR-CURTA-DURACAO": _LEGACY_ONLY_NOTE,
    "MBA": _XSD_AND_DTD_CONFIRMED_NOTE,
    "OUTROS-TIPOS-DE-FORMACAO-COMPLEMENTAR": _LEGACY_ONLY_NOTE,
    "OUTROS": _XSD_AND_DTD_CONFIRMED_NOTE,
    "PARTICIPACAO-EM-SEMINARIO": _XSD_AND_DTD_CONFIRMED_NOTE,
    "PARTICIPACAO-EM-OFICINA": _XSD_AND_DTD_CONFIRMED_NOTE,
    "PARTICIPACAO-EM-ENCONTRO": _XSD_AND_DTD_CONFIRMED_NOTE,
    "PARTICIPACAO-EM-EXPOSICAO": _XSD_ONLY_CONFIRMED_NOTE,
    "PARTICIPACAO-EM-FEIRA": _XSD_ONLY_CONFIRMED_NOTE,
    "PARTICIPACAO-EM-OLIMPIADA": _XSD_ONLY_CONFIRMED_NOTE,
    "OUTRAS-PARTICIPACOES-EM-EVENTOS": _LEGACY_ONLY_NOTE,
    "OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS": _XSD_AND_DTD_CONFIRMED_NOTE,
}


def normalize_role_token(raw_value: str) -> str:
    """Normaliza rótulo textual de papel para consulta determinística na tabela explícita."""
    decomposed = unicodedata.normalize("NFKD", raw_value)
    without_accents = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    cleaned = without_accents.replace("-", " ").replace("_", " ").casefold().strip()
    return _WHITESPACE_RE.sub(" ", cleaned)


def resolve_participation_role(
    participation_type_raw: str | None,
    participation_form_raw: str | None,
) -> tuple[str | None, str | None]:
    """Resolve papel de participação apenas por equivalências inequívocas.

    Retorna `(participation_role, audit_note)`. Nunca infere papel a partir de
    `NATUREZA` nem inventa categoria quando há valor desconhecido ou conflito.
    """
    type_role = (
        PARTICIPATION_ROLE_MAP.get(normalize_role_token(participation_type_raw))
        if participation_type_raw is not None
        else None
    )
    form_role = (
        PARTICIPATION_ROLE_MAP.get(normalize_role_token(participation_form_raw))
        if participation_form_raw is not None
        else None
    )

    if type_role is not None and form_role is not None and type_role != form_role:
        return (
            None,
            (
                "conflito entre @TIPO-PARTICIPACAO e @FORMA-PARTICIPACAO; "
                "participation_role mantido None sem inferência"
            ),
        )
    if type_role is not None:
        return type_role, None
    if form_role is not None:
        return form_role, None
    if participation_type_raw is not None or participation_form_raw is not None:
        return (
            None,
            (
                "@TIPO-PARTICIPACAO/@FORMA-PARTICIPACAO fora da tabela explícita; "
                "valor bruto preservado e participation_role mantido None"
            ),
        )
    return None, None
