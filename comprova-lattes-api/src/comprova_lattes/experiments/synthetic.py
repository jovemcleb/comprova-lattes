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

SYNTHETIC_ACRONYMS: dict[str, str] = {
    "I": "Instituto",
    "C": "Centro",
    "F": "Faculdade",
    "E": "Escola",
}

_HOLDER_FIRST_NAMES: tuple[str, ...] = (
    "Ana",
    "Bruno",
    "Carla",
    "Diego",
    "Elisa",
    "Fabio",
    "Gabriel",
    "Helena",
    "Igor",
    "Joana",
    "Lucas",
    "Marina",
    "Natalia",
    "Orlando",
    "Paula",
    "Rafael",
    "Sofia",
    "Tiago",
    "Vanessa",
    "Vitor",
)

_HOLDER_SURNAMES: tuple[str, ...] = (
    "Almeida",
    "Barbosa",
    "Campos",
    "Cardoso",
    "Dias",
    "Duarte",
    "Ferreira",
    "Freitas",
    "Gomes",
    "Lima",
    "Lopes",
    "Martins",
    "Mendes",
    "Moreira",
    "Nunes",
    "Oliveira",
    "Pereira",
    "Ribeiro",
    "Santos",
    "Teixeira",
)

_INSTITUTION_TYPES: tuple[str, ...] = ("Instituto", "Centro", "Faculdade", "Escola")

_INSTITUTION_PLACES: tuple[str, ...] = (
    "Aurora",
    "Bosque",
    "Cerrado",
    "Delta",
    "Fonte",
    "Gruta",
    "Horizonte",
    "Jardim",
    "Lago",
    "Monte",
    "Prado",
    "Ribeira",
    "Serra",
    "Vale",
)

_INSTITUTION_MODIFIERS: tuple[str, ...] = (
    "Azul",
    "Central",
    "Digital",
    "Global",
    "Integral",
    "Leste",
    "Municipal",
    "Norte",
    "Oeste",
    "Regional",
    "Sul",
    "Verde",
)

_EXCLUDED_ACRONYMS: frozenset[str] = frozenset(
    {
        "API",
        "CAD",
        "CAL",
        "CAM",
        "CAN",
        "CAR",
        "CAS",
        "CEP",
        "CIA",
        "CPF",
        "CSS",
        "CSV",
        "ECA",
        "ERA",
        "ESA",
        "EVA",
        "FAD",
        "FAP",
        "FIM",
        "FMI",
        "ICA",
        "IDA",
        "IDS",
        "IMA",
        "IML",
        "IRA",
        "ISO",
        "IVA",
        "MEC",
        "OAB",
        "OCR",
        "PDF",
        "PNG",
        "PUC",
        "SUS",
        "TCC",
        "USP",
        "XML",
    }
)

_TOPIC_PHRASES: tuple[str, ...] = (
    "Redes Locais",
    "Banco de Dados",
    "Sistemas Digitais",
    "Engenharia de Software",
    "Sistemas em Nuvem",
    "Arquitetura Web",
    "Ciência de Dados",
    "Lógica Aplicada",
    "Gestão de Projetos",
    "Qualidade de Software",
    "Modelagem de Processos",
    "Automação Rural",
    "Energia Solar",
    "Ensino de Ciências",
    "Educação Ambiental",
    "Direito Digital",
    "Saúde Coletiva",
    "Geoprocessamento Rural",
    "Estatística Aplicada",
    "Robótica Educacional",
    "Computação Gráfica",
    "Sistemas Embarcados",
    "Análise Territorial",
    "Inovação Tecnológica",
)

_ACADEMIC_TITLE_PREFIXES: tuple[str, ...] = (
    "Especialização em",
    "Formação em",
    "Aperfeiçoamento em",
    "Qualificação em",
)

_COMPLEMENTARY_TITLE_PREFIXES: tuple[str, ...] = (
    "Curso de",
    "Oficina de",
    "Extensão em",
    "Módulo de",
)

_ACTIVITY_TITLE_PREFIXES: tuple[str, ...] = (
    "Projeto de",
    "Estudo sobre",
    "Relato de",
    "Painel sobre",
    "Trabalho em",
    "Pesquisa sobre",
)

_EVENT_PREFIXES: tuple[str, ...] = (
    "Congresso de",
    "Encontro de",
    "Jornada de",
    "Mostra de",
    "Seminário de",
    "Simpósio de",
    "Fórum de",
    "Colóquio de",
)

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
    "template_version": "ptbr-contract-draft-v2",
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


def _stable_index(token: str, size: int) -> int:
    digest = hashlib.sha256(token.encode()).digest()
    return int.from_bytes(digest[:8], "big") % size


def institution_acronym(institution_name: str) -> str:
    """Deriva sigla curta determinística a partir das iniciais da instituição."""
    words = [part for part in institution_name.split() if part and part[0].isalnum()]
    return "".join(word[0].upper() for word in words)


def _holder_candidates() -> list[str]:
    return [f"{first} {last}" for first in _HOLDER_FIRST_NAMES for last in _HOLDER_SURNAMES]


def _institution_candidates() -> list[str]:
    return [
        f"{kind} {place} {modifier}"
        for kind in _INSTITUTION_TYPES
        for place in _INSTITUTION_PLACES
        for modifier in _INSTITUTION_MODIFIERS
        if f"{kind[0]}{place[0]}{modifier[0]}".upper() not in _EXCLUDED_ACRONYMS
    ]


def _pick_holder(seed_key: str, used: set[str]) -> str:
    two_word = _holder_candidates()
    total = len(two_word)
    for attempt in range(total):
        candidate = two_word[_stable_index(f"{seed_key}:{attempt}", total)]
        if candidate not in used:
            return candidate
    start = _stable_index(seed_key, total)
    for offset in range(total):
        candidate = two_word[(start + offset) % total]
        if candidate not in used:
            return candidate
    for first in _HOLDER_FIRST_NAMES:
        for last1 in _HOLDER_SURNAMES:
            for last2 in _HOLDER_SURNAMES:
                if last1 == last2:
                    continue
                candidate = f"{first} {last1} {last2}"
                if candidate not in used:
                    return candidate
    raise RuntimeError("Vocabulário de titulares esgotado")


def _pick_institution(
    seed_key: str,
    used_institutions: set[str],
    used_acronyms: set[str],
) -> str:
    candidates = _institution_candidates()
    total = len(candidates)
    for attempt in range(total):
        candidate = candidates[_stable_index(f"{seed_key}:{attempt}", total)]
        acronym = institution_acronym(candidate)
        if candidate not in used_institutions and acronym not in used_acronyms:
            return candidate
    start = _stable_index(seed_key, total)
    for offset in range(total):
        candidate = candidates[(start + offset) % total]
        acronym = institution_acronym(candidate)
        if candidate not in used_institutions and acronym not in used_acronyms:
            return candidate
    raise RuntimeError("Vocabulário de instituições esgotado")


def _pick_title(seed_key: str, category: int, used_titles: set[str]) -> tuple[str, str]:
    if category == 0:
        prefixes = _ACADEMIC_TITLE_PREFIXES
    elif category == 1:
        prefixes = _COMPLEMENTARY_TITLE_PREFIXES
    else:
        prefixes = _ACTIVITY_TITLE_PREFIXES
    pairs = [(f"{prefix} {topic}", topic) for prefix in prefixes for topic in _TOPIC_PHRASES]
    total = len(pairs)
    for attempt in range(total):
        title, topic = pairs[_stable_index(f"{seed_key}:{attempt}", total)]
        if title not in used_titles:
            return title, topic
    start = _stable_index(seed_key, total)
    for offset in range(total):
        title, topic = pairs[(start + offset) % total]
        if title not in used_titles:
            return title, topic
    raise RuntimeError("Vocabulário de títulos esgotado")


def _pick_event(seed_key: str, excluded_topic: str, used_events: set[str]) -> str:
    candidates = [
        f"{prefix} {topic}"
        for prefix in _EVENT_PREFIXES
        for topic in _TOPIC_PHRASES
        if topic != excluded_topic
    ]
    total = len(candidates)
    for attempt in range(total):
        candidate = candidates[_stable_index(f"{seed_key}:{attempt}", total)]
        if candidate not in used_events:
            return candidate
    start = _stable_index(seed_key, total)
    for offset in range(total):
        candidate = candidates[(start + offset) % total]
        if candidate not in used_events:
            return candidate
    raise RuntimeError("Vocabulário de eventos esgotado")


def synthetic_acronyms(cases: tuple["Case", ...]) -> dict[str, str]:
    """Tabela explícita por emissor; preserva a identidade exclusiva da família."""
    table: dict[str, str] = {}
    for c in cases:
        inst = c.curriculum.records[0].institution
        if inst:
            table[institution_acronym(inst)] = inst
    return table


def alternative_identity(seed: int, family_id: str, domain: str) -> str:
    """Deriva nome alternativo neutro da mesma distribuição em domínio especificado."""
    normalized_family = family_id.lower()
    seed_key = f"{seed}:{normalized_family}:alt:{domain}"
    if domain == "holder_name":
        return _pick_holder(seed_key, set())
    if domain == "issuer_institution":
        return _pick_institution(seed_key, set(), set())
    raise ValueError(f"Domínio alternativo desconhecido: {domain!r}")


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


def _xml(
    category: int,
    *,
    holder_name: str,
    institution_name: str,
    title: str,
    event_name: str | None = None,
) -> bytes:
    root = Element("CURRICULO-VITAE")
    general = SubElement(root, "DADOS-GERAIS", {"NOME-COMPLETO": holder_name})
    attrs = {
        "SEQUENCIA-FORMACAO": "1",
        "NOME-INSTITUICAO": institution_name,
        "NOME-CURSO": title,
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
        basic = {"TITULO": title, "ANO": "2024"}
        if category == 2:
            basic["TIPO-PARTICIPACAO"] = "PARTICIPANTE"
        SubElement(child, f"DADOS-BASICOS-{suffix}", basic)
        detail = {
            "NOME-INSTITUICAO" if category == 2 else "INSTITUICAO-PROMOTORA": institution_name,
        }
        if category != 4 and event_name is not None:
            detail["NOME-DO-EVENTO"] = event_name
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


def _apply_legitimate_variation(values: dict[str, object], index: int) -> None:
    """Aplica variação equivalente (espaços, caixa ou pontuação) sem alterar conteúdo."""
    style = index % 3
    if style == 0:
        for key in ("holder_name", "activity_title", "event_name", "issuer_institution"):
            text = values[key]
            if isinstance(text, str):
                values[key] = "  ".join(text.split())
    elif style == 1:
        for key in ("holder_name", "activity_title", "event_name", "issuer_institution"):
            text = values[key]
            if isinstance(text, str):
                values[key] = text.upper() if text != text.upper() else text.lower()
    else:
        separators = {
            "holder_name": ", ",
            "activity_title": " - ",
            "event_name": ": ",
            "issuer_institution": ", ",
        }
        for key, sep in separators.items():
            text = values[key]
            if isinstance(text, str):
                prefix, _, suffix = text.rpartition(" ")
                values[key] = f"{prefix}{sep}{suffix}" if prefix else f"{text}."


def generate(*, seed: int, pilot_families: int, final_families: int) -> Corpus:
    """Cada família contém uma categoria e cinco operadores; tamanhos explícitos.

    Família inclui registro-base, emissor e template exclusivos; variantes do
    mesmo registro compartilham emissor e presença de relação sigla/evidência
    AD-014 (regra prévia por índice de família, independente de classe/operador).
    Identidades legíveis, layout e seed de ruído derivam de (seed, partition, index),
    mantendo o piloto invariável quando final_families muda e o padrão de ruído
    estável por família sem alterar a degradação. Categorias alternam em cada
    partição, com equilíbrio exato nos tamanhos aprovados múltiplos de cinco
    (10 famílias piloto = 50 casos e 20 famílias finais = 100 casos). Rótulos são
    intenções, não anotações humanas. Templates textuais em português são rascunho
    de composição assistida por agente (TEMPLATE_PROVENANCE), pendente de validação
    humana antes do congelamento, sem alegação de independência metodológica ou
    conformidade XSD/DTD.
    """
    if pilot_families < 1 or final_families < 1:
        raise ValueError("Ambas as partições precisam de famílias")
    cases = []
    used_holders: set[str] = set()
    used_institutions: set[str] = set()
    used_acronyms: set[str] = set()
    used_titles: set[str] = set()
    used_events: set[str] = set()
    for partition, total in (("pilot", pilot_families), ("final", final_families)):
        for index in range(total):
            fid = hashlib.sha256(f"{seed}:{partition}:{index}".encode()).hexdigest()[:12]
            layout = int(fid, 16)
            category = index % 5
            has_ad014 = index % 2 == 0
            family_seed = f"{seed}:{partition}:{index}"
            holder_name = _pick_holder(f"{family_seed}:holder", used_holders)
            used_holders.add(holder_name)
            institution_name = _pick_institution(
                f"{family_seed}:institution",
                used_institutions,
                used_acronyms,
            )
            used_institutions.add(institution_name)
            used_acronyms.add(institution_acronym(institution_name))
            activity_title, title_topic = _pick_title(
                f"{family_seed}:title", category, used_titles
            )
            used_titles.add(activity_title)
            event_name: str | None = None
            if category in (2, 3):
                event_name = _pick_event(f"{family_seed}:event", title_topic, used_events)
                used_events.add(event_name)
            xml = _xml(
                category,
                holder_name=holder_name,
                institution_name=institution_name,
                title=activity_title,
                event_name=event_name,
            )
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
                doc_institution = institution_name
                if operator == "legitimate":
                    _apply_legitimate_variation(values, index)
                elif operator == "factual_mutation":
                    if category in (0, 1):
                        values["workload_hours"] = 45 if category == 0 else 400
                    elif category == 2:
                        for field in ("activity_year", "start_year", "end_year"):
                            values[field] += 7
                    elif category == 3:
                        alt_holder = _pick_holder(
                            f"{seed}:{fid.lower()}:alt:holder_name",
                            used_holders,
                        )
                        used_holders.add(alt_holder)
                        values["holder_name"] = alt_holder
                    else:
                        alt_institution = _pick_institution(
                            f"{seed}:{fid.lower()}:alt:issuer_institution",
                            used_institutions,
                            used_acronyms,
                        )
                        used_institutions.add(alt_institution)
                        used_acronyms.add(institution_acronym(alt_institution))
                        values["issuer_institution"] = alt_institution
                        doc_institution = alt_institution
                    expected = MatchStatus.DIVERGENTE
                elif operator in ("omission", "no_document"):
                    values["holder_name"] = None
                    expected = MatchStatus.INCONCLUSIVO
                if has_ad014 and operator != "no_document":
                    acronym = institution_acronym(doc_institution)
                    values["issuer_acronym"] = acronym
                    values["issuer_name_acronym_evidence"] = (
                        f"{values['issuer_institution']} - {acronym}"
                    )
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
