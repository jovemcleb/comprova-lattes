"""Bancada fictícia sem LLM, com famílias indivisíveis e IDs neutros."""

import hashlib
import random
from typing import Literal
from xml.etree.ElementTree import Element, SubElement, tostring

from pydantic import BaseModel, ConfigDict, model_validator

from comprova_lattes.matcher.models import ExtractedDocumentRecord, MatchStatus
from comprova_lattes.parser import parse_lattes_xml
from comprova_lattes.schemas.lattes import LattesCurriculum

from .render import pdf, png, raster

SYNTHETIC_ACRONYMS = {"IF": "INSTITUTO FICTICIO"}


def synthetic_acronyms(cases: tuple["Case", ...]) -> dict[str, str]:
    """Tabela explícita por emissor; preserva a identidade exclusiva da família."""
    return {
        f"{acronym}{c.issuer_id.upper()}": f"{name} {c.issuer_id.upper()}"
        for c in cases
        for acronym, name in SYNTHETIC_ACRONYMS.items()
    }


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


def document_text(record: ExtractedDocumentRecord, layout: int = 0) -> str:
    fields = record.model_dump(
        exclude={
            "document_id",
            "extraction_status",
            "raw_metadata",
            "confianca_extracao",
            "categoria_sugerida",
        }
    )
    lines = [f"{k}: {v}" for k, v in fields.items() if v is not None]
    if layout % 2:
        lines.reverse()
    return "CERTIFICADO FICTICIO\n" + "\n".join(lines)


def generate(*, seed: int, pilot_families: int, final_families: int) -> Corpus:
    """Cada família cruza 5 categorias x 5 operadores; tamanhos são explícitos.

    Família inclui registro-base, emissor e template exclusivos; variantes de
    categorias compartilham emissor. Rótulos são intenções, não anotações humanas.
    XML é fixture consumível por M1, sem alegação de conformidade XSD/DTD.
    """
    if pilot_families < 1 or final_families < 1:
        raise ValueError("Ambas as partições precisam de famílias")
    rng, cases = random.Random(seed), []
    partitions = ["pilot"] * pilot_families + ["final"] * final_families
    rng.shuffle(partitions)
    for family, partition in enumerate(partitions):
        fid = hashlib.sha256(f"{seed}:{family}".encode()).hexdigest()[:12]
        for category in range(5):
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
                    values["holder_name"] = values["holder_name"].replace(" ", "  ")
                    values["issuer_institution"] = f"IF{fid.upper()}"
                    values["activity_title"] = "X" + values["activity_title"][1:]
                elif operator == "factual_mutation":
                    if category in (0, 1):
                        values["workload_hours"] = 45 if category == 0 else 400
                    elif category == 2:
                        for field in ("activity_year", "start_year", "end_year"):
                            values[field] += 7
                    elif category == 3:
                        values["holder_name"] = "OUTRA PESSOA SINTETICA"
                    else:
                        values["issuer_institution"] = "INSTITUICAO DIVERGENTE SINTETICA"
                    expected = MatchStatus.DIVERGENTE
                elif operator in ("omission", "no_document"):
                    values["holder_name"] = None
                    expected = MatchStatus.INCONCLUSIVO
                gold = ExtractedDocumentRecord(document_id=cid, **values)
                level, layout = (category + variant + family) % 3, family % 2
                mime = "image/png" if (category + variant) % 2 else "application/pdf"
                image = raster(
                    document_text(gold, layout),
                    seed=seed + family,
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
                        gold=None if operator == "no_document" else gold,
                        document=None if operator == "no_document" else data,
                        mime_type=mime,
                    )
                )
    return Corpus(seed=seed, cases=tuple(cases))
