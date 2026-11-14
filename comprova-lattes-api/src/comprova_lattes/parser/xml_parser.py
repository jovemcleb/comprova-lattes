"""Parser seguro e determinístico de XML do Currículo Lattes (P0-A)."""

from __future__ import annotations

import hashlib
import json
import re
import warnings
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import defusedxml.ElementTree as DET
from defusedxml.common import (
    DefusedXmlException,
    DTDForbidden,
    EntitiesForbidden,
    ExternalReferenceForbidden,
)
from pydantic import ValidationError

from comprova_lattes.parser.exceptions import (
    LattesEncodingError,
    LattesInvalidRootError,
    LattesMalformedXmlError,
    LattesNumericValueError,
    LattesParserWarning,
    LattesResourceLimitError,
    LattesSchemaValidationError,
    LattesXmlSecurityError,
)
from comprova_lattes.parser.mappings import (
    ACADEMIC_TAG_SUBTYPES,
    COMPLEMENTARY_TAG_SUBTYPES,
    EVENT_TAG_SUBTYPES,
    OUT_OF_SCOPE_TECHNICAL_PRODUCTION_TAGS,
    STATUS_TOKEN_MAP,
    TECHNICAL_PRODUCTION_TAG_CATEGORIES,
    TECHNICAL_PRODUCTION_TAG_SUBTYPES,
    UNVERIFIED_VARIANT_TAGS,
    resolve_participation_role,
)
from comprova_lattes.schemas import (
    ActivityStatus,
    LattesCategory,
    LattesCurriculum,
    LattesRecord,
    XmlProvenance,
)

_UTF8_BOM = b"\xef\xbb\xbf"
_UNSUPPORTED_BOMS = (
    b"\xff\xfe\x00\x00",
    b"\x00\x00\xfe\xff",
    b"\xff\xfe",
    b"\xfe\xff",
)
_XML_DECL_RE = re.compile(rb"^\s*<\?xml\b([^?]*?)\?>")
_ENCODING_ATTR_RE = re.compile(
    r"""\bencoding\s*=\s*(?:"([^"]*)"|'([^']*)')""",
    re.IGNORECASE,
)
_STRICT_INT_RE = re.compile(r"^[+-]?\d+$")
_ROOT_TAG = "CURRICULO-VITAE"

# Technical operational defaults to bound resource usage; not scientific domain limits.
DEFAULT_MAX_XML_BYTES: int = 10 * 1024 * 1024  # 10 MiB
DEFAULT_MAX_XML_DEPTH: int = 64
DIAGNOSTIC_INVALID_WORKLOAD_HOURS: str = "INVALID_WORKLOAD_HOURS"


@dataclass(frozen=True, slots=True)
class LattesParseDiagnostic:
    """Diagnóstico estruturado para anomalia recuperável durante o parsing XML."""

    code: str
    record_path: str
    attribute: str
    original_value: str
    reason: str
    record_index: int | None = None


@dataclass(frozen=True, slots=True)
class LattesParseResult:
    """Resultado completo do parsing com metadados, diagnósticos e variantes."""

    curriculum: LattesCurriculum
    declared_encoding: str
    unverified_variants: tuple[str, ...] = ()
    unrecognized_elements: tuple[str, ...] = ()
    diagnostics: tuple[LattesParseDiagnostic, ...] = ()


def parse_lattes_xml(
    data: bytes,
    *,
    max_bytes: int = DEFAULT_MAX_XML_BYTES,
    max_depth: int = DEFAULT_MAX_XML_DEPTH,
) -> LattesCurriculum:
    """Converte bytes do XML Lattes em `LattesCurriculum` de forma segura.

    Emite `LattesParserWarning` para cada diagnóstico recuperável registrado
    durante o parsing (por exemplo, descarte de `CARGA-HORARIA` inválida),
    evitando descarte silencioso. Para inspeção estruturada sem `warnings.warn`,
    utilize `parse_lattes_xml_with_report`.
    """
    result = parse_lattes_xml_with_report(
        data,
        max_bytes=max_bytes,
        max_depth=max_depth,
    )
    for diagnostic in result.diagnostics:
        warnings.warn(
            (
                f"[{diagnostic.code}] {diagnostic.record_path}/@{diagnostic.attribute}="
                f"{diagnostic.original_value!r}: {diagnostic.reason}"
            ),
            category=LattesParserWarning,
            stacklevel=2,
        )
    return result.curriculum


def parse_lattes_xml_with_report(
    data: bytes,
    *,
    max_bytes: int = DEFAULT_MAX_XML_BYTES,
    max_depth: int = DEFAULT_MAX_XML_DEPTH,
) -> LattesParseResult:
    """Executa o parsing seguro e retorna também diagnósticos, variantes e tags desconhecidas."""
    if not isinstance(data, bytes):
        raise TypeError("Expected 'bytes' input for Lattes XML payload.")

    validated_max_bytes = _validate_positive_int_limit(max_bytes, "max_bytes")
    validated_max_depth = _validate_positive_int_limit(max_depth, "max_depth")

    if len(data) > validated_max_bytes:
        raise LattesResourceLimitError(
            f"XML payload size ({len(data)} bytes) exceeds max_bytes limit ({validated_max_bytes} bytes)."
        )

    if not data or not data.strip():
        raise LattesMalformedXmlError("XML payload is empty.")

    declared_encoding = _validate_and_decode_bytes(data)
    root = _parse_secure_xml(data, max_depth=validated_max_depth)

    if root.tag != _ROOT_TAG:
        raise LattesInvalidRootError(
            f"Expected root element '{_ROOT_TAG}', got {root.tag!r}."
        )

    unverified_variants: list[str] = []
    unrecognized_elements: list[str] = []
    diagnostics: list[LattesParseDiagnostic] = []

    dados_gerais = root.find("DADOS-GERAIS")
    dados_comp = root.find("DADOS-COMPLEMENTARES")
    producao_tecnica = root.find("PRODUCAO-TECNICA")

    header = _extract_header(root, dados_gerais, unverified_variants)
    holder_name = header["full_name"]

    records: list[LattesRecord] = []
    records.extend(
        _extract_academic_records(
            dados_gerais,
            holder_name=holder_name,
            record_offset=len(records),
            unverified_variants=unverified_variants,
            unrecognized_elements=unrecognized_elements,
            diagnostics=diagnostics,
        )
    )
    records.extend(
        _extract_complementary_records(
            dados_gerais=dados_gerais,
            dados_comp=dados_comp,
            holder_name=holder_name,
            record_offset=len(records),
            unverified_variants=unverified_variants,
            unrecognized_elements=unrecognized_elements,
            diagnostics=diagnostics,
        )
    )
    records.extend(
        _extract_event_records(
            dados_gerais=dados_gerais,
            dados_comp=dados_comp,
            holder_name=holder_name,
            record_offset=len(records),
            unverified_variants=unverified_variants,
            unrecognized_elements=unrecognized_elements,
            diagnostics=diagnostics,
        )
    )
    records.extend(
        _extract_technical_production_records(
            producao_tecnica=producao_tecnica,
            holder_name=holder_name,
            unverified_variants=unverified_variants,
            unrecognized_elements=unrecognized_elements,
        )
    )

    _assign_record_ids(records, lattes_id=header["lattes_id"])

    try:
        curriculum = LattesCurriculum(
            lattes_id=header["lattes_id"],
            updated_at=header["updated_at"],
            full_name=holder_name,
            citation_names=header["citation_names"],
            summary=header["summary"],
            records=records,
        )
    except ValidationError as exc:
        raise LattesSchemaValidationError(
            f"Failed to validate parsed LattesCurriculum schema: {exc}"
        ) from exc

    return LattesParseResult(
        curriculum=curriculum,
        declared_encoding=declared_encoding,
        unverified_variants=tuple(dict.fromkeys(unverified_variants)),
        unrecognized_elements=tuple(dict.fromkeys(unrecognized_elements)),
        diagnostics=tuple(diagnostics),
    )


def _validate_positive_int_limit(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value!r}.")
    return value


def _validate_and_decode_bytes(data: bytes) -> str:
    for bom in _UNSUPPORTED_BOMS:
        if data.startswith(bom):
            raise LattesEncodingError(
                "Unsupported XML byte-order mark; only UTF-8 and ISO-8859-1 are supported."
            )

    has_utf8_bom = data.startswith(_UTF8_BOM)
    payload = data[len(_UTF8_BOM) :] if has_utf8_bom else data

    match = _XML_DECL_RE.match(payload[:512])
    if match:
        try:
            decl_text = match.group(1).decode("ascii", errors="strict")
        except UnicodeDecodeError as exc:
            raise LattesEncodingError(
                "XML declaration contains non-ASCII bytes."
            ) from exc
        encoding_match = _ENCODING_ATTR_RE.search(decl_text)
        raw_encoding = (
            (encoding_match.group(1) if encoding_match.group(1) is not None else encoding_match.group(2))
            if encoding_match
            else None
        )
    else:
        raw_encoding = None

    if raw_encoding is None:
        target_encoding = "utf-8"
        canonical_label = "UTF-8"
    else:
        normalized = raw_encoding.strip().upper()
        if normalized == "UTF-8":
            target_encoding = "utf-8"
            canonical_label = "UTF-8"
        elif normalized == "ISO-8859-1":
            if has_utf8_bom:
                raise LattesEncodingError(
                    "UTF-8 BOM conflicts with declared ISO-8859-1 encoding."
                )
            target_encoding = "iso-8859-1"
            canonical_label = "ISO-8859-1"
        else:
            raise LattesEncodingError(
                f"Unsupported XML encoding declaration {raw_encoding!r}; "
                "only UTF-8 and ISO-8859-1 are supported."
            )

    try:
        payload.decode(target_encoding, errors="strict")
    except UnicodeDecodeError as exc:
        raise LattesEncodingError(
            f"XML bytes do not match declared encoding {canonical_label}."
        ) from exc

    return canonical_label


class _BoundedTreeBuilder(ET.TreeBuilder):
    """TreeBuilder que interrompe o parsing assim que a profundidade excede `max_depth`."""

    def __init__(self, max_depth: int) -> None:
        super().__init__()
        self._max_depth = max_depth
        self._depth = 0

    def start(self, tag: str, attrs: dict[str, str]) -> ET.Element:
        self._depth += 1
        if self._depth > self._max_depth:
            raise LattesResourceLimitError(
                f"XML nesting depth ({self._depth}) exceeds max_depth limit ({self._max_depth})."
            )
        return super().start(tag, attrs)

    def end(self, tag: str) -> ET.Element:
        self._depth -= 1
        return super().end(tag)


def _parse_secure_xml(data: bytes, *, max_depth: int) -> ET.Element:
    parser = DET.DefusedXMLParser(
        target=_BoundedTreeBuilder(max_depth),
        forbid_dtd=True,
        forbid_entities=True,
        forbid_external=True,
    )
    try:
        parser.feed(data)
        return parser.close()
    except (
        DTDForbidden,
        EntitiesForbidden,
        ExternalReferenceForbidden,
        DefusedXmlException,
    ) as exc:
        raise LattesXmlSecurityError(f"Unsafe XML construct rejected: {exc}") from exc
    except ET.ParseError as exc:
        raise LattesMalformedXmlError(f"Malformed XML document: {exc}") from exc


def _extract_header(
    root: ET.Element,
    dados_gerais: ET.Element | None,
    unverified_variants: list[str],
) -> dict[str, object]:
    lattes_id = _clean_str(root.attrib.get("NUMERO-IDENTIFICADOR"))
    if lattes_id is None:
        fallback_id = _clean_str(root.attrib.get("IDENTIFICADOR-CNPQ"))
        if fallback_id is not None:
            lattes_id = fallback_id
            unverified_variants.append(
                "CURRICULO-VITAE/@IDENTIFICADOR-CNPQ "
                "(fallback legado Python ausente do XSD e da DTD; conformidade UI não verificada)"
            )

    # Keep DATA-ATUALIZACAO raw; never substitute HORA-ATUALIZACAO.
    updated_at = _clean_str(root.attrib.get("DATA-ATUALIZACAO"))

    full_name: str | None = None
    citation_names: list[str] = []
    summary: str | None = None

    if dados_gerais is not None:
        full_name = _clean_str(dados_gerais.attrib.get("NOME-COMPLETO"))
        raw_citations = _clean_str(dados_gerais.attrib.get("NOME-EM-CITACOES-BIBLIOGRAFICAS"))
        if raw_citations is not None:
            citation_names = [part.strip() for part in raw_citations.split(";") if part.strip()]

        resumo_elem = dados_gerais.find("RESUMO-CV")
        if resumo_elem is not None:
            summary = _clean_str(resumo_elem.attrib.get("TEXTO-RESUMO-CV-RH"))
        if summary is None:
            summary = _clean_str(dados_gerais.attrib.get("TEXTO-RESUMO-CV-RH"))

    return {
        "lattes_id": lattes_id,
        "updated_at": updated_at,
        "full_name": full_name,
        "citation_names": citation_names,
        "summary": summary,
    }


def _extract_academic_records(
    dados_gerais: ET.Element | None,
    *,
    holder_name: str | None,
    record_offset: int,
    unverified_variants: list[str],
    unrecognized_elements: list[str],
    diagnostics: list[LattesParseDiagnostic],
) -> list[LattesRecord]:
    if dados_gerais is None:
        return []
    section_elem = dados_gerais.find("FORMACAO-ACADEMICA-TITULACAO")
    if section_elem is None:
        return []

    records: list[LattesRecord] = []
    for child in section_elem:
        subtype = ACADEMIC_TAG_SUBTYPES.get(child.tag)
        if subtype is None:
            unrecognized_elements.append(
                f"CURRICULO-VITAE/DADOS-GERAIS/FORMACAO-ACADEMICA-TITULACAO/{child.tag}"
            )
            continue

        _record_unverified_tag(child.tag, unverified_variants)
        context = f"DADOS-GERAIS/FORMACAO-ACADEMICA-TITULACAO/{child.tag}"
        record_path = f"{_ROOT_TAG}/{context}"
        sequence = _clean_str(child.attrib.get("SEQUENCIA-FORMACAO"))
        title, title_attr = _first_clean_attr_with_name(
            [child],
            (
                "NOME-CURSO",
                "NOME-CURSO-INGLES",
                "TITULO-DA-DISSERTACAO-TESE",
                "TITULO-DO-TRABALHO-DE-CONCLUSAO-DE-CURSO",
                "TITULO-DA-MONOGRAFIA",
                "TITULO-DO-TRABALHO",
                "TITULO-DA-RESIDENCIA-MEDICA",
            ),
        )
        if title_attr == "NOME-CURSO-INGLES":
            unverified_variants.append(
                f"{child.tag}/@NOME-CURSO-INGLES "
                "(confirmado no XSD do Extrator e na DTD comunitária; conformidade UI não verificada)"
            )

        start_year = _extract_strict_int_from_candidates(
            [child],
            ("ANO-DE-INICIO",),
            field_name="start_year",
            context=context,
        )
        end_year = _extract_strict_int_from_candidates(
            [child],
            ("ANO-DE-CONCLUSAO", "ANO-DE-OBTENCAO-DO-TITULO"),
            field_name="end_year",
            context=context,
        )
        workload_hours = _extract_workload_hours(
            [(child, record_path)],
            record_index=record_offset + len(records),
            diagnostics=diagnostics,
        )
        status = _parse_explicit_status(
            _first_clean_attr([child], ("STATUS-DO-CURSO", "STATUS-DO-ESTAGIO")),
            context=context,
            unverified_variants=unverified_variants,
        )

        records.append(
            _build_record(
                category=LattesCategory.FORMACAO_ACADEMICA,
                subtype=subtype,
                sequence=sequence,
                provenance=XmlProvenance(
                    parent_tag="DADOS-GERAIS",
                    section_tag="FORMACAO-ACADEMICA-TITULACAO",
                    record_tag=child.tag,
                    sequence_attribute="SEQUENCIA-FORMACAO" if sequence is not None else None,
                    raw_attributes=_collect_provenance_attributes(child),
                ),
                holder_name=holder_name,
                institution=_clean_str(child.attrib.get("NOME-INSTITUICAO")),
                institution_acronym=_clean_str(child.attrib.get("SIGLA-INSTITUICAO")),
                title=title,
                start_year=start_year,
                end_year=end_year,
                workload_hours=workload_hours,
                status=status,
            )
        )

    return records


def _extract_complementary_records(
    *,
    dados_gerais: ET.Element | None,
    dados_comp: ET.Element | None,
    holder_name: str | None,
    record_offset: int,
    unverified_variants: list[str],
    unrecognized_elements: list[str],
    diagnostics: list[LattesParseDiagnostic],
) -> list[LattesRecord]:
    containers: list[tuple[str, ET.Element]] = []
    if dados_comp is not None:
        containers.extend(
            ("DADOS-COMPLEMENTARES", section)
            for section in dados_comp.findall("FORMACAO-COMPLEMENTAR")
        )
    if dados_gerais is not None:
        gerais_sections = dados_gerais.findall("FORMACAO-COMPLEMENTAR")
        if gerais_sections:
            unverified_variants.append(
                "DADOS-GERAIS/FORMACAO-COMPLEMENTAR "
                "(contêiner legado TS ausente do XSD e da DTD; conformidade UI não verificada)"
            )
            containers.extend(("DADOS-GERAIS", section) for section in gerais_sections)

    records: list[LattesRecord] = []
    for parent_tag, section_elem in containers:
        for child in section_elem:
            subtype = COMPLEMENTARY_TAG_SUBTYPES.get(child.tag)
            if subtype is None:
                unrecognized_elements.append(
                    f"CURRICULO-VITAE/{parent_tag}/FORMACAO-COMPLEMENTAR/{child.tag}"
                )
                continue

            _record_unverified_tag(child.tag, unverified_variants)
            context = f"{parent_tag}/FORMACAO-COMPLEMENTAR/{child.tag}"
            record_path = f"{_ROOT_TAG}/{context}"
            sequence = _clean_str(child.attrib.get("SEQUENCIA-FORMACAO"))
            title, title_attr = _first_clean_attr_with_name(
                [child],
                ("NOME-CURSO", "NOME-CURSO-INGLES", "TITULO-DA-MONOGRAFIA"),
            )
            if title_attr == "NOME-CURSO-INGLES":
                unverified_variants.append(
                    f"{child.tag}/@NOME-CURSO-INGLES "
                    "(confirmado no XSD do Extrator e na DTD comunitária; conformidade UI não verificada)"
                )

            start_year = _extract_strict_int_from_candidates(
                [child],
                ("ANO-DE-INICIO",),
                field_name="start_year",
                context=context,
            )
            end_year = _extract_strict_int_from_candidates(
                [child],
                ("ANO-DE-CONCLUSAO", "ANO-DE-OBTENCAO-DO-TITULO"),
                field_name="end_year",
                context=context,
            )
            workload_hours = _extract_workload_hours(
                [(child, record_path)],
                record_index=record_offset + len(records),
                diagnostics=diagnostics,
            )
            status = _parse_explicit_status(
                _clean_str(child.attrib.get("STATUS-DO-CURSO")),
                context=context,
                unverified_variants=unverified_variants,
            )

            records.append(
                _build_record(
                    category=LattesCategory.FORMACAO_COMPLEMENTAR,
                    subtype=subtype,
                    sequence=sequence,
                    provenance=XmlProvenance(
                        parent_tag=parent_tag,
                        section_tag="FORMACAO-COMPLEMENTAR",
                        record_tag=child.tag,
                        sequence_attribute="SEQUENCIA-FORMACAO" if sequence is not None else None,
                        raw_attributes=_collect_provenance_attributes(child),
                    ),
                    holder_name=holder_name,
                    institution=_clean_str(child.attrib.get("NOME-INSTITUICAO")),
                    institution_acronym=_clean_str(child.attrib.get("SIGLA-INSTITUICAO")),
                    title=title,
                    start_year=start_year,
                    end_year=end_year,
                    workload_hours=workload_hours,
                    status=status,
                )
            )

    return records


def _extract_event_records(
    *,
    dados_gerais: ET.Element | None,
    dados_comp: ET.Element | None,
    holder_name: str | None,
    record_offset: int,
    unverified_variants: list[str],
    unrecognized_elements: list[str],
    diagnostics: list[LattesParseDiagnostic],
) -> list[LattesRecord]:
    containers: list[tuple[str, ET.Element]] = []
    comp_section = dados_comp.find("PARTICIPACAO-EM-EVENTOS-CONGRESSOS") if dados_comp is not None else None
    if comp_section is not None:
        containers.append(("DADOS-COMPLEMENTARES", comp_section))
    elif dados_gerais is not None:
        gerais_section = dados_gerais.find("PARTICIPACAO-EM-EVENTOS-CONGRESSOS")
        if gerais_section is not None:
            unverified_variants.append(
                "DADOS-GERAIS/PARTICIPACAO-EM-EVENTOS-CONGRESSOS "
                "(fallback legado TS ausente do XSD e da DTD; conformidade UI não verificada)"
            )
            containers.append(("DADOS-GERAIS", gerais_section))

    records: list[LattesRecord] = []
    for parent_tag, section_elem in containers:
        for child in section_elem:
            subtype = EVENT_TAG_SUBTYPES.get(child.tag)
            if subtype is None:
                unrecognized_elements.append(
                    f"CURRICULO-VITAE/{parent_tag}/PARTICIPACAO-EM-EVENTOS-CONGRESSOS/{child.tag}"
                )
                continue

            _record_unverified_tag(child.tag, unverified_variants)
            context = f"{parent_tag}/PARTICIPACAO-EM-EVENTOS-CONGRESSOS/{child.tag}"
            base_record_path = f"{_ROOT_TAG}/{context}"
            sequence, seq_attr = _first_clean_attr_with_name(
                [child],
                ("SEQUENCIA-PRODUCAO", "SEQUENCIA-FORMACAO"),
            )
            if seq_attr == "SEQUENCIA-FORMACAO":
                unverified_variants.append(
                    f"{child.tag}/@SEQUENCIA-FORMACAO "
                    "(fallback legado TS em eventos ausente do XSD e da DTD; "
                    "conformidade UI não verificada)"
                )

            basic_node, detail_node = _select_basic_and_detail_nodes(
                child,
                context=context,
                unverified_variants=unverified_variants,
            )

            event_name, event_name_attr = _first_clean_attr_with_name(
                [detail_node, child],
                ("NOME-DO-EVENTO", "NOME-DO-EVENTO-INGLES"),
            )
            if event_name_attr == "NOME-DO-EVENTO-INGLES":
                unverified_variants.append(
                    f"{child.tag}/@NOME-DO-EVENTO-INGLES "
                    "(confirmado no XSD do Extrator e na DTD comunitária; "
                    "conformidade UI não verificada)"
                )

            title = _first_clean_attr([basic_node, child], ("TITULO",))
            institution = _first_clean_attr(
                [detail_node, basic_node, child],
                ("NOME-INSTITUICAO",),
            )
            city = _first_clean_attr([detail_node, child], ("CIDADE-DO-EVENTO",))
            location = _first_clean_attr([detail_node, child], ("LOCAL-DO-EVENTO",))
            nature_raw = _first_clean_attr([basic_node, child], ("NATUREZA",))
            participation_type_raw = _first_clean_attr(
                [basic_node, child],
                ("TIPO-PARTICIPACAO",),
            )
            participation_form_raw = _first_clean_attr(
                [basic_node, child],
                ("FORMA-PARTICIPACAO",),
            )
            participation_role, role_audit_note = resolve_participation_role(
                participation_type_raw,
                participation_form_raw,
            )
            if role_audit_note is not None:
                unverified_variants.append(f"{context}: {role_audit_note}")

            event_year = _extract_strict_int_from_candidates(
                [basic_node, child],
                ("ANO",),
                field_name="start_year/end_year",
                context=context,
            )
            workload_hours = _extract_workload_hours(
                [
                    (
                        detail_node,
                        f"{base_record_path}/{detail_node.tag}" if detail_node is not None else "",
                    ),
                    (
                        basic_node,
                        f"{base_record_path}/{basic_node.tag}" if basic_node is not None else "",
                    ),
                    (child, base_record_path),
                ],
                record_index=record_offset + len(records),
                diagnostics=diagnostics,
            )

            records.append(
                _build_record(
                    category=LattesCategory.PARTICIPACAO_EVENTO,
                    subtype=subtype,
                    sequence=sequence,
                    provenance=XmlProvenance(
                        parent_tag=parent_tag,
                        section_tag="PARTICIPACAO-EM-EVENTOS-CONGRESSOS",
                        record_tag=child.tag,
                        sequence_attribute=seq_attr if sequence is not None else None,
                        raw_attributes=_collect_provenance_attributes(child),
                    ),
                    holder_name=holder_name,
                    institution=institution,
                    title=title,
                    event_name=event_name,
                    city=city,
                    location=location,
                    start_year=event_year,
                    end_year=event_year,
                    workload_hours=workload_hours,
                    status=None,
                    nature_raw=nature_raw,
                    participation_type_raw=participation_type_raw,
                    participation_form_raw=participation_form_raw,
                    participation_role=participation_role,
                )
            )

    return records


def _extract_technical_production_records(
    *,
    producao_tecnica: ET.Element | None,
    holder_name: str | None,
    unverified_variants: list[str],
    unrecognized_elements: list[str],
) -> list[LattesRecord]:
    if producao_tecnica is None:
        return []

    records: list[LattesRecord] = []
    for section_elem in producao_tecnica.findall("DEMAIS-TIPOS-DE-PRODUCAO-TECNICA"):
        for child in section_elem:
            if child.tag in OUT_OF_SCOPE_TECHNICAL_PRODUCTION_TAGS:
                continue

            category = TECHNICAL_PRODUCTION_TAG_CATEGORIES.get(child.tag)
            if category is None:
                unrecognized_elements.append(
                    f"CURRICULO-VITAE/PRODUCAO-TECNICA/DEMAIS-TIPOS-DE-PRODUCAO-TECNICA/{child.tag}"
                )
                continue

            subtype = TECHNICAL_PRODUCTION_TAG_SUBTYPES[child.tag]
            context = f"PRODUCAO-TECNICA/DEMAIS-TIPOS-DE-PRODUCAO-TECNICA/{child.tag}"
            sequence = _clean_str(child.attrib.get("SEQUENCIA-PRODUCAO"))
            basic_node, detail_node = _select_basic_and_detail_nodes(
                child,
                context=context,
                unverified_variants=unverified_variants,
            )

            title, title_attr = _first_clean_attr_with_name(
                [basic_node],
                ("TITULO", "TITULO-INGLES"),
            )
            if title_attr == "TITULO-INGLES":
                unverified_variants.append(
                    f"{child.tag}/@TITULO-INGLES "
                    "(confirmado no XSD do Extrator e na DTD comunitária; "
                    "conformidade UI não verificada)"
                )

            nature_raw = _first_clean_attr([basic_node], ("NATUREZA",))
            year = _extract_strict_int_from_candidates(
                [basic_node],
                ("ANO",),
                field_name="start_year/end_year",
                context=context,
            )
            institution = _first_clean_attr([detail_node], ("INSTITUICAO-PROMOTORA",))

            if category == LattesCategory.APRESENTACAO_TRABALHO:
                event_name, event_name_attr = _first_clean_attr_with_name(
                    [detail_node],
                    ("NOME-DO-EVENTO", "NOME-DO-EVENTO-INGLES"),
                )
                if event_name_attr == "NOME-DO-EVENTO-INGLES":
                    unverified_variants.append(
                        f"{child.tag}/@NOME-DO-EVENTO-INGLES "
                        "(confirmado no XSD do Extrator e na DTD comunitária; "
                        "conformidade UI não verificada)"
                    )
                city = _first_clean_attr([detail_node], ("CIDADE-DA-APRESENTACAO",))
                location = _first_clean_attr([detail_node], ("LOCAL-DA-APRESENTACAO",))
                # Nunca inferir PALESTRANTE por NATUREZA="CONFERENCIA" (AD-010/AD-012).
                participation_role = None
            else:
                event_name = None
                city = _first_clean_attr([detail_node], ("CIDADE",))
                location = _first_clean_attr([detail_node], ("LOCAL",))
                # Papel estrutural derivado da tag ORGANIZACAO-DE-EVENTO; nature_raw preservado.
                participation_role = "ORGANIZADOR"

            records.append(
                _build_record(
                    category=category,
                    subtype=subtype,
                    sequence=sequence,
                    provenance=XmlProvenance(
                        parent_tag="PRODUCAO-TECNICA",
                        section_tag="DEMAIS-TIPOS-DE-PRODUCAO-TECNICA",
                        record_tag=child.tag,
                        sequence_attribute="SEQUENCIA-PRODUCAO" if sequence is not None else None,
                        raw_attributes=_collect_provenance_attributes(child),
                    ),
                    holder_name=holder_name,
                    institution=institution,
                    title=title,
                    event_name=event_name,
                    city=city,
                    location=location,
                    start_year=year,
                    end_year=year,
                    workload_hours=None,
                    status=None,
                    nature_raw=nature_raw,
                    participation_type_raw=None,
                    participation_form_raw=None,
                    participation_role=participation_role,
                )
            )

    return records


def _select_basic_and_detail_nodes(
    record_elem: ET.Element,
    *,
    context: str,
    unverified_variants: list[str],
) -> tuple[ET.Element | None, ET.Element | None]:
    basic_nodes = [sub for sub in record_elem if sub.tag.startswith("DADOS-BASICOS-")]
    detail_nodes = [sub for sub in record_elem if sub.tag.startswith("DETALHAMENTO-")]
    if len(basic_nodes) > 1 or len(detail_nodes) > 1:
        unverified_variants.append(
            f"{context}: múltiplos subnós DADOS-BASICOS/DETALHAMENTO preservados apenas na proveniência"
        )
    return (
        basic_nodes[0] if basic_nodes else None,
        detail_nodes[0] if detail_nodes else None,
    )


def _assign_record_ids(records: list[LattesRecord], *, lattes_id: object) -> None:
    """Identifica conteúdo canônico e distingue duplicatas pela ordem de extração.

    Ordem de atributos e codificação XML não afetam a identidade. Alterações
    nos dados extraídos geram outra identidade, sem representar edição estável.
    """
    occurrences: Counter[str] = Counter()
    for record in records:
        payload = json.dumps(
            [lattes_id, record.model_dump(mode="json", exclude={"record_id"})],
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(payload.encode("ascii")).hexdigest()
        occurrences[digest] += 1
        record.record_id = f"{digest}:{occurrences[digest]}"


def _build_record(**kwargs: object) -> LattesRecord:
    try:
        return LattesRecord(**kwargs)  # type: ignore[arg-type]
    except ValidationError as exc:
        raise LattesSchemaValidationError(
            f"Failed to validate parsed LattesRecord schema: {exc}"
        ) from exc


def _collect_provenance_attributes(record_elem: ET.Element) -> dict[str, str]:
    raw_attrs: dict[str, str] = {str(k): str(v) for k, v in record_elem.attrib.items()}
    stack: list[tuple[ET.Element, str]] = [(record_elem, "")]
    while stack:
        elem, prefix = stack.pop()
        if prefix:
            for attr_name, attr_value in elem.attrib.items():
                raw_attrs[f"{prefix}/@{attr_name}"] = str(attr_value)

        children = list(elem)
        if not children:
            continue

        tag_totals = Counter(child.tag for child in children)
        tag_seen: Counter[str] = Counter()
        child_frames: list[tuple[ET.Element, str]] = []
        for child in children:
            tag_seen[child.tag] += 1
            segment = (
                child.tag
                if tag_totals[child.tag] == 1
                else f"{child.tag}[{tag_seen[child.tag]}]"
            )
            child_path = f"{prefix}/{segment}" if prefix else segment
            child_frames.append((child, child_path))

        stack.extend(reversed(child_frames))

    return raw_attrs


def _record_unverified_tag(tag_name: str, unverified_variants: list[str]) -> None:
    note = UNVERIFIED_VARIANT_TAGS.get(tag_name)
    if note is not None:
        unverified_variants.append(f"{tag_name}: {note}")


def _parse_explicit_status(
    raw_status: str | None,
    *,
    context: str,
    unverified_variants: list[str],
) -> ActivityStatus | None:
    if raw_status is None:
        return None
    mapped = STATUS_TOKEN_MAP.get(raw_status.strip().upper())
    if mapped is None:
        unverified_variants.append(
            f"{context}/@STATUS-DO-CURSO={raw_status!r} (valor não mapeado; mantido None sem inferência)"
        )
    return mapped


def _extract_strict_int_from_candidates(
    elements: Iterable[ET.Element | None],
    attr_names: tuple[str, ...],
    *,
    field_name: str,
    context: str,
) -> int | None:
    selected: int | None = None
    for elem in elements:
        if elem is None:
            continue
        for attr_name in attr_names:
            raw = _clean_str(elem.attrib.get(attr_name))
            if raw is None:
                continue
            if not _STRICT_INT_RE.fullmatch(raw):
                raise LattesNumericValueError(
                    f"Invalid integer for {field_name} at {context}/@{attr_name}: {raw!r}."
                )
            parsed = int(raw)
            if selected is None:
                selected = parsed
    return selected


def _extract_workload_hours(
    candidates: Iterable[tuple[ET.Element | None, str]],
    *,
    record_index: int,
    diagnostics: list[LattesParseDiagnostic],
) -> Decimal | None:
    attr_name = "CARGA-HORARIA"
    for elem, elem_path in candidates:
        if elem is None:
            continue
        raw_attr = elem.attrib.get(attr_name)
        cleaned = _clean_str(raw_attr)
        if cleaned is None:
            continue

        original_value = str(raw_attr)
        reason_label: str | None = None
        parsed: Decimal | None = None
        try:
            parsed = Decimal(cleaned)
        except InvalidOperation:
            reason_label = "não numérico"

        if reason_label is None and parsed is not None:
            if not parsed.is_finite():
                reason_label = "não finito"
            elif parsed < Decimal(0):
                reason_label = "negativo"

        if reason_label is not None:
            diagnostics.append(
                LattesParseDiagnostic(
                    code=DIAGNOSTIC_INVALID_WORKLOAD_HOURS,
                    record_path=elem_path,
                    attribute=attr_name,
                    original_value=original_value,
                    reason=(
                        f"Valor de carga horária {reason_label} ({original_value!r}) "
                        "descartado para None; registro e atributos brutos preservados."
                    ),
                    record_index=record_index,
                )
            )
            return None

        return parsed

    return None


def _first_clean_attr(
    elements: Iterable[ET.Element | None],
    attr_names: tuple[str, ...],
) -> str | None:
    value, _ = _first_clean_attr_with_name(elements, attr_names)
    return value


def _first_clean_attr_with_name(
    elements: Iterable[ET.Element | None],
    attr_names: tuple[str, ...],
) -> tuple[str | None, str | None]:
    for elem in elements:
        if elem is None:
            continue
        for attr_name in attr_names:
            cleaned = _clean_str(elem.attrib.get(attr_name))
            if cleaned is not None:
                return cleaned, attr_name
    return None, None


def _clean_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
