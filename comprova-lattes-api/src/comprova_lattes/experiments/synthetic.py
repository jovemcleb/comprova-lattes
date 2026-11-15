"""Bancada fictícia determinística com certificados em português (rascunho assistido)."""

import hashlib
import random
from typing import Literal
from xml.etree.ElementTree import Element, SubElement, tostring

from pydantic import BaseModel, ConfigDict, model_validator

from comprova_lattes.matcher.models import ExtractedDocumentRecord, MatchStatus
from comprova_lattes.parser import parse_lattes_xml
from comprova_lattes.schemas.lattes import LattesCategory, LattesCurriculum

from .render import pdf, png, raster

SYNTHETIC_ACRONYMS = {"IF": "INSTITUTO FICTICIO"}

FIELD_LABELS: dict[str, str] = {
    "holder_name": "Titular",
    "activity_title": "Atividade",
    "event_name": "Evento",
    "participation_role_raw": "Papel",
    "issuer_institution": "Instituição emissora",
    "issuer_acronym": "Sigla da instituição",
    "issuer_name_acronym_evidence": "Identificação da instituição",
    "start_year": "Ano de início",
    "end_year": "Ano de conclusão",
    "activity_year": "Ano da atividade",
    "workload_hours": "Carga horária",
}
DOCUMENT_FIELD_LABELS = FIELD_LABELS

CATEGORY_ORDER: tuple[LattesCategory, ...] = (
    LattesCategory.FORMACAO_ACADEMICA,
    LattesCategory.FORMACAO_COMPLEMENTAR,
    LattesCategory.PARTICIPACAO_EVENTO,
    LattesCategory.APRESENTACAO_TRABALHO,
    LattesCategory.ORGANIZACAO_EVENTO,
)

CATEGORY_TEMPLATES: dict[LattesCategory, tuple[str, str]] = {
    LattesCategory.FORMACAO_ACADEMICA: (
        "CERTIFICADO DE FORMAÇÃO ACADÊMICA",
        "Registro sintético de formação acadêmica para conferência documental.",
    ),
    LattesCategory.FORMACAO_COMPLEMENTAR: (
        "CERTIFICADO DE FORMAÇÃO COMPLEMENTAR",
        "Registro sintético de formação complementar para conferência documental.",
    ),
    LattesCategory.PARTICIPACAO_EVENTO: (
        "DECLARAÇÃO DE PARTICIPAÇÃO EM EVENTO",
        "Registro sintético de participação em evento para conferência documental.",
    ),
    LattesCategory.APRESENTACAO_TRABALHO: (
        "CERTIFICADO DE APRESENTAÇÃO DE TRABALHO",
        "Registro sintético de apresentação de trabalho para conferência documental.",
    ),
    LattesCategory.ORGANIZACAO_EVENTO: (
        "DECLARAÇÃO DE ORGANIZAÇÃO DE EVENTO",
        "Registro sintético de organização de evento para conferência documental.",
    ),
}

DEFAULT_TEMPLATE: tuple[str, str] = (
    "CERTIFICADO DE REGISTRO CURRICULAR",
    "Registro sintético de atividade curricular para conferência documental.",
)

TEMPLATE_PROVENANCE: dict[str, object] = {
    "template_version": "ptbr-contract-draft-v1",
    "status": "draft_pending_human_validation",
    "composition_origin": "agent_assisted_draft",
    "human_approval_required_before_freeze": True,
    "methodological_independence_claimed": False,
    "same_model_family_preparation_risk": (
        "Agente da família Gemini participou da redação dos cabeçalhos e frases "
        "fixas em português; exige validação e aprovação humana antes do "
        "congelamento e não permite alegar independência metodológica frente "
        "ao extrator avaliado."
    ),
    "factuality_policy": (
        "Somente cabeçalhos/frases fixas neutras por categoria e rótulos do "
        "contrato; valores provêm exclusivamente do registro sem criar fatos, "
        "datas, horas, locais ou assinaturas."
    ),
}


def synthetic_acronyms(cases: tuple["Case", ...]) -> dict[str, str]:
    """Tabela explícita por emissor; preserva a identidade exclusiva da família."""
    return {
        f"{acronym}{c.issuer_id.upper()}": f"{name} {c.issuer_id.upper()}"
        for c in cases
        for acronym, name in SYNTHETIC_ACRONYMS.items()
    }


def alternative_identity(seed: int, family_id: str, domain: str) -> str:
    """Deriva sufixo hex neutro de 12 caracteres distinto de family_id em domínio alternativo."""
    normalized_family = family_id.lower()
    base = normalized_family.upper()
    for attempt in range(4):
        suffix = "" if attempt == 0 else f":{attempt}"
        candidate = (
            hashlib.sha256(f"{seed}:{normalized_family}:alt:{domain}{suffix}".encode())
            .hexdigest()[:12]
            .upper()
        )
        if candidate != base:
            return candidate
    raise RuntimeError("Falha ao derivar sufixo alternativo distinto")


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    case_id: str
    family_id: str
    template_id: str
    issuer_id: str
    partition: Literal["pilot", "final"]
    operator: str
    degradation: int
    xml: bytes
    curriculum: LattesCurriculum
    expected: MatchStatus
    gold: ExtractedDocumentRecord | None
    document: bytes | None
    mime_type: str


class Corpus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    seed: int
    cases: tuple[Case, ...]

    @model_validator(mode="after")
    def isolate(self):
        seen, ids = {}, set()
        for c in self.cases:
            if c.case_id in ids:
                raise ValueError("case_id duplicado")
            ids.add(c.case_id)
            for key in ("family_id", "template_id", "issuer_id"):
                identity = (key, getattr(c, key))
                if identity in seen and seen[identity] != c.partition:
                    raise ValueError("Vazamento entre piloto e final")
                seen[identity] = c.partition
        return self

    def select(self, partition: str) -> tuple[Case, ...]:
        if partition not in ("pilot", "final"):
            raise ValueError("Partição desconhecida")
        return tuple(c for c in self.cases if c.partition == partition)


def _xml(category: int, identity: str) -> bytes:
    root = Element("CURRICULO-VITAE")
    general = SubElement(root, "DADOS-GERAIS", {"NOME-COMPLETO": f"PESSOA FICTICIA {identity}"})
    attrs = {
        "SEQUENCIA-FORMACAO": "1",
        "NOME-INSTITUICAO": f"INSTITUTO FICTICIO {identity}",
        "NOME-CURSO": f"CURSO SINTETICO {identity}",
        "ANO-DE-INICIO": "2020",
        "ANO-DE-CONCLUSAO": "2024",
        "CARGA-HORARIA": "40",
        "STATUS-DO-CURSO": "CONCLUIDO",
    }
    if category == 0:
        parent = SubElement(general, "FORMACAO-ACADEMICA-TITULACAO")
        SubElement(parent, "ESPECIALIZACAO", attrs)
    elif category == 1:
        parent = SubElement(SubElement(root, "DADOS-COMPLEMENTARES"), "FORMACAO-COMPLEMENTAR")
        SubElement(parent, "FORMACAO-COMPLEMENTAR-DE-EXTENSAO-UNIVERSITARIA", attrs)
    else:
        if category == 2:
            parent = SubElement(
                SubElement(root, "DADOS-COMPLEMENTARES"), "PARTICIPACAO-EM-EVENTOS-CONGRESSOS"
            )
            tag = "PARTICIPACAO-EM-CONGRESSO"
            suffix = "DA-PARTICIPACAO-EM-CONGRESSO"
        else:
            parent = SubElement(
                SubElement(root, "PRODUCAO-TECNICA"), "DEMAIS-TIPOS-DE-PRODUCAO-TECNICA"
            )
            tag = ["APRESENTACAO-DE-TRABALHO", "ORGANIZACAO-DE-EVENTO"][category - 3]
            suffix = ["DA-APRESENTACAO-DE-TRABALHO", "DA-ORGANIZACAO-DE-EVENTO"][category - 3]
        child = SubElement(parent, tag, {"SEQUENCIA-PRODUCAO": "1"})
        basic = {"TITULO": f"TRABALHO SINTETICO {identity}", "ANO": "2024"}
        if category == 2:
            basic["TIPO-PARTICIPACAO"] = "PARTICIPANTE"
        SubElement(child, f"DADOS-BASICOS-{suffix}", basic)
        detail = {
            "NOME-INSTITUICAO" if category == 2 else "INSTITUICAO-PROMOTORA":
                f"INSTITUTO FICTICIO {identity}",
        }
        if category != 4:
            detail["NOME-DO-EVENTO"] = f"EVENTO FICTICIO {identity}"
        SubElement(child, f"DETALHAMENTO-{suffix}", detail)
    return tostring(root, encoding="utf-8", xml_declaration=True)


def _resolve_category_template(
    category: LattesCategory | str | int | None,
) -> tuple[str, str]:
    if category is None:
        return DEFAULT_TEMPLATE
    if type(category) is int:
        if 0 <= category < len(CATEGORY_ORDER):
            return CATEGORY_TEMPLATES[CATEGORY_ORDER[category]]
        raise ValueError(f"Categoria de certificado inválida: {category!r}")
    if isinstance(category, LattesCategory):
        return CATEGORY_TEMPLATES[category]
    if isinstance(category, str):
        try:
            resolved = LattesCategory(category)
        except ValueError as exc:
            raise ValueError(f"Categoria de certificado inválida: {category!r}") from exc
        return CATEGORY_TEMPLATES[resolved]
    raise ValueError(f"Categoria de certificado inválida: {category!r}")


def document_text(
    record: ExtractedDocumentRecord,
    layout: int = 0,
    category: LattesCategory | str | int | None = None,
) -> str:
    """Formata certificado sintético em português com rótulos do contrato.

    Rascunho de composição assistida por agente (ver TEMPLATE_PROVENANCE); exige
    aprovação humana antes do congelamento e não sustenta alegação de
    independência metodológica em relação ao extrator da mesma família Gemini.
    """
    if type(layout) is not int or layout < 0:
        raise ValueError("Layout deve ser inteiro não negativo")
    header, presentation = _resolve_category_template(category)
    fields = record.model_dump(
        exclude={
            "document_id",
            "extraction_status",
            "raw_metadata",
            "confianca_extracao",
            "categoria_sugerida",
        }
    )
    keys = list(FIELD_LABELS)
    if layout == 1:
        keys.reverse()
    elif layout not in (0, 1):
        random.Random(layout).shuffle(keys)
    lines = [f"{FIELD_LABELS[k]}: {fields[k]}" for k in keys if fields[k] is not None]
    return "\n".join((header, presentation, *lines))


def generate(*, seed: int, pilot_families: int, final_families: int) -> Corpus:
    """Cada família contém uma categoria e cinco operadores; tamanhos explícitos.

    Família inclui registro-base, emissor e template exclusivos; variantes do
    mesmo registro compartilham emissor. Identidades, layout e seed de ruído
    derivam de (seed, partition, index), mantendo o piloto invariável quando
    final_families muda e o padrão de ruído estável por família sem alterar a
    degradação. Categorias alternam em cada partição, com equilíbrio exato nos
    tamanhos aprovados múltiplos de cinco (10 famílias piloto = 50 casos e
    20 famílias finais = 100 casos). Rótulos são intenções, não anotações humanas.
    Templates textuais em português são rascunho de composição assistida por
    agente (TEMPLATE_PROVENANCE), pendente de validação humana antes do
    congelamento, sem alegação de independência metodológica ou conformidade XSD/DTD.
    """
    if pilot_families < 1 or final_families < 1:
        raise ValueError("Ambas as partições precisam de famílias")
    cases = []
    for partition, total in (("pilot", pilot_families), ("final", final_families)):
        for index in range(total):
            fid = hashlib.sha256(f"{seed}:{partition}:{index}".encode()).hexdigest()[:12]
            layout = int(fid, 16)
            category = index % 5
            xml = _xml(category, fid.upper())
            curriculum = parse_lattes_xml(xml)
            r = curriculum.records[0]
            base = {
                "holder_name": curriculum.full_name,
                "activity_title": r.title,
                "event_name": r.event_name,
                "issuer_institution": r.institution,
                "start_year": r.start_year,
                "end_year": r.end_year,
                "activity_year": r.end_year or r.start_year or 2024,
                "workload_hours": r.workload_hours,
                "participation_role_raw": "APRESENTADOR" if category == 3 else r.participation_role,
            }
            for variant, operator in enumerate(
                ("identity", "legitimate", "factual_mutation", "omission", "no_document")
            ):
                cid = hashlib.sha256(f"{fid}:{category}:{variant}".encode()).hexdigest()[:20]
                values = dict(base)
                expected = MatchStatus.VALIDADO
                if operator == "legitimate":
                    acronym = f"IF{fid.upper()}"
                    values["holder_name"] = values["holder_name"].replace(" ", "  ")
                    values["issuer_acronym"] = acronym
                    values["issuer_name_acronym_evidence"] = (
                        f"{values['issuer_institution']} - {acronym}"
                    )
                    values["activity_title"] = "X" + values["activity_title"][1:]
                elif operator == "factual_mutation":
                    if category in (0, 1):
                        values["workload_hours"] = 45 if category == 0 else 400
                    elif category == 2:
                        for field in ("activity_year", "start_year", "end_year"):
                            values[field] += 7
                    elif category == 3:
                        values["holder_name"] = (
                            f"PESSOA FICTICIA {alternative_identity(seed, fid, 'holder_name')}"
                        )
                    else:
                        values["issuer_institution"] = (
                            "INSTITUTO FICTICIO "
                            f"{alternative_identity(seed, fid, 'issuer_institution')}"
                        )
                    expected = MatchStatus.DIVERGENTE
                elif operator in ("omission", "no_document"):
                    values["holder_name"] = None
                    expected = MatchStatus.INCONCLUSIVO
                level = (category + variant + index) % 3
                mime = "image/png" if (category + variant) % 2 else "application/pdf"
                gold = data = None
                if operator != "no_document":
                    gold = ExtractedDocumentRecord(document_id=cid, **values)
                    image = raster(
                        document_text(gold, layout, category=r.category),
                        seed=layout,
                        degradation=level,
                        layout=layout,
                    )
                    data = (png if mime == "image/png" else pdf)(*image)
                cases.append(
                    Case(
                        case_id=cid,
                        family_id=fid,
                        template_id=f"t-{fid}",
                        issuer_id=fid,
                        partition=partition,
                        operator=operator,
                        degradation=level,
                        xml=xml,
                        curriculum=curriculum,
                        expected=expected,
                        gold=gold,
                        document=data,
                        mime_type=mime,
                    )
                )
    return Corpus(seed=seed, cases=tuple(cases))
