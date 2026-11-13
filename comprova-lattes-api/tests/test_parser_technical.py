import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as DET
import pytest

from comprova_lattes.parser import (
    LattesNumericValueError,
    LattesResourceLimitError,
    LattesXmlSecurityError,
    parse_lattes_xml_with_report,
)
from comprova_lattes.schemas import ActivityStatus, LattesCategory, LattesRecord

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "m1-technical"
MANIFEST_PATH = FIXTURES_DIR / "manifest.json"
MANIFEST: dict[str, Any] = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
FIXTURE_ENTRIES: list[dict[str, Any]] = MANIFEST["fixtures"]

_XSD_WORKLOAD_ALLOWED_TAGS = frozenset(
    {
        "ESPECIALIZACAO",
        "APERFEICOAMENTO",
        "FORMACAO-COMPLEMENTAR-DE-EXTENSAO-UNIVERSITARIA",
        "MBA",
        "FORMACAO-COMPLEMENTAR-CURSO-DE-CURTA-DURACAO",
        "OUTROS",
    }
)


def _wrap_xml(body: str, *, encoding: str = "utf-8", xml_decl_encoding: str = "UTF-8") -> bytes:
    xml_text = (
        f'<?xml version="1.0" encoding="{xml_decl_encoding}"?>'
        '<CURRICULO-VITAE SISTEMA-ORIGEM-XML="SINTETICO-TESTE" '
        'NUMERO-IDENTIFICADOR="9100999988887777" DATA-ATUALIZACAO="13112026">'
        f'<DADOS-GERAIS NOME-COMPLETO="Teste Técnico Sintético" '
        'NOME-EM-CITACOES-BIBLIOGRAFICAS="SINTETICO, T. T." '
        'NACIONALIDADE="B" PERMISSAO-DE-DIVULGACAO="SIM" />'
        f"{body}</CURRICULO-VITAE>"
    )
    return xml_text.encode(encoding)


def _load_fixture_entry(entry: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    xml_path = FIXTURES_DIR / entry["file"]
    assert xml_path.is_file(), f"Missing technical fixture file: {xml_path}"
    return xml_path.read_bytes(), entry


def _assert_record_matches_manifest(record: LattesRecord, expected: dict[str, Any]) -> None:
    assert record.category == LattesCategory(expected["category"])
    assert record.subtype == expected["subtype"]
    assert record.sequence == expected["sequence"]
    assert record.institution == expected["institution"]
    assert record.institution_acronym == expected["institution_acronym"]
    assert record.title == expected["title"]
    assert record.event_name == expected["event_name"]
    assert record.city == expected["city"]
    assert record.location == expected["location"]
    assert record.start_year == expected["start_year"]
    assert record.end_year == expected["end_year"]

    expected_hours = (
        Decimal(expected["workload_hours"])
        if expected["workload_hours"] is not None
        else None
    )
    assert record.workload_hours == expected_hours
    expected_status = (
        ActivityStatus(expected["status"])
        if expected["status"] is not None
        else None
    )
    assert record.status == expected_status
    assert record.validation_code == expected["validation_code"]
    assert record.nature_raw == expected["nature_raw"]
    assert record.participation_type_raw == expected["participation_type_raw"]
    assert record.participation_form_raw == expected["participation_form_raw"]
    assert record.participation_role == expected["participation_role"]

    expected_prov = expected["provenance"]
    assert record.provenance.parent_tag == expected_prov["parent_tag"]
    assert record.provenance.section_tag == expected_prov["section_tag"]
    assert record.provenance.record_tag == expected_prov["record_tag"]
    assert record.provenance.sequence_attribute == expected_prov["sequence_attribute"]


def test_technical_manifest_lists_exact_xml_fixture_set() -> None:
    assert MANIFEST["scope"] == "M1-Parser-Technical-Production-Fixtures"
    declared_files = [entry["file"] for entry in FIXTURE_ENTRIES]
    disk_files = sorted(path.name for path in FIXTURES_DIR.glob("*.xml"))
    assert len(declared_files) == len(set(declared_files))
    assert sorted(declared_files) == disk_files


@pytest.mark.parametrize("entry", FIXTURE_ENTRIES, ids=[e["file"] for e in FIXTURE_ENTRIES])
def test_technical_fixture_respects_xsd_and_security_invariants(entry: dict[str, Any]) -> None:
    xml_bytes, _ = _load_fixture_entry(entry)
    assert b"<!DOCTYPE" not in xml_bytes
    assert b"<!ENTITY" not in xml_bytes

    root = DET.fromstring(xml_bytes)
    assert root.tag == "CURRICULO-VITAE"
    assert root.attrib.get("SISTEMA-ORIGEM-XML")
    for elem in root.iter():
        assert "SIGLA-INSTITUICAO" not in elem.attrib
        if "CARGA-HORARIA" in elem.attrib:
            assert elem.tag in _XSD_WORKLOAD_ALLOWED_TAGS


@pytest.mark.parametrize("entry", FIXTURE_ENTRIES, ids=[e["file"] for e in FIXTURE_ENTRIES])
def test_technical_fixture_matches_manifest_header_counts_and_records(
    entry: dict[str, Any],
) -> None:
    xml_bytes, spec = _load_fixture_entry(entry)
    result = parse_lattes_xml_with_report(xml_bytes)
    curriculum = result.curriculum

    assert result.declared_encoding == spec["encoding"]
    assert result.diagnostics == ()
    assert result.unrecognized_elements == ()

    expected_header = spec["expected_header"]
    assert curriculum.lattes_id == expected_header["lattes_id"]
    assert curriculum.updated_at == expected_header["updated_at"]
    assert curriculum.full_name == expected_header["full_name"]
    assert curriculum.citation_names == expected_header["citation_names"]
    assert curriculum.summary == expected_header["summary"]

    actual_counts = {
        "academic": sum(
            1 for r in curriculum.records if r.category == LattesCategory.FORMACAO_ACADEMICA
        ),
        "complementary": sum(
            1 for r in curriculum.records if r.category == LattesCategory.FORMACAO_COMPLEMENTAR
        ),
        "event": sum(
            1 for r in curriculum.records if r.category == LattesCategory.PARTICIPACAO_EVENTO
        ),
        "apresentacao_trabalho": sum(
            1 for r in curriculum.records if r.category == LattesCategory.APRESENTACAO_TRABALHO
        ),
        "organizacao_evento": sum(
            1 for r in curriculum.records if r.category == LattesCategory.ORGANIZACAO_EVENTO
        ),
        "total": len(curriculum.records),
    }
    assert actual_counts == spec["expected_counts"]

    expected_records = spec["expected_records"]
    assert len(curriculum.records) == len(expected_records)
    for expected_record in expected_records:
        idx = expected_record["index"]
        _assert_record_matches_manifest(curriculum.records[idx], expected_record)


@pytest.mark.parametrize("entry", FIXTURE_ENTRIES, ids=[e["file"] for e in FIXTURE_ENTRIES])
def test_technical_fixture_iso_8859_1_transcoded_matches_utf8(entry: dict[str, Any]) -> None:
    xml_bytes, _ = _load_fixture_entry(entry)
    utf8_text = xml_bytes.decode("utf-8", errors="strict")
    utf8_decl = '<?xml version="1.0" encoding="UTF-8"?>'
    iso_decl = '<?xml version="1.0" encoding="ISO-8859-1"?>'
    assert utf8_text.startswith(utf8_decl)

    iso_bytes = utf8_text.replace(utf8_decl, iso_decl, 1).encode("iso-8859-1", errors="strict")
    utf8_result = parse_lattes_xml_with_report(xml_bytes)
    iso_result = parse_lattes_xml_with_report(iso_bytes)

    assert iso_result.declared_encoding == "ISO-8859-1"
    assert iso_result.diagnostics == utf8_result.diagnostics
    assert iso_result.unrecognized_elements == utf8_result.unrecognized_elements
    assert iso_result.curriculum == utf8_result.curriculum


def test_apresentacao_trabalho_conferencia_never_infers_palestrante_and_preserves_provenance() -> None:
    xml_bytes = _wrap_xml(
        """
        <PRODUCAO-TECNICA>
            <DEMAIS-TIPOS-DE-PRODUCAO-TECNICA>
                <APRESENTACAO-DE-TRABALHO SEQUENCIA-PRODUCAO="1">
                    <DADOS-BASICOS-DA-APRESENTACAO-DE-TRABALHO
                        NATUREZA="CONFERENCIA"
                        TITULO="Palestra Magistral Fictícia"
                        ANO="2025"
                        PAIS="Brasil"
                        IDIOMA="Português" />
                    <DETALHAMENTO-DA-APRESENTACAO-DE-TRABALHO
                        NOME-DO-EVENTO="Conferência Regional de Sistemas"
                        INSTITUICAO-PROMOTORA="Instituto Fictício"
                        LOCAL-DA-APRESENTACAO="Auditório 1"
                        CIDADE-DA-APRESENTACAO="Belém" />
                </APRESENTACAO-DE-TRABALHO>
            </DEMAIS-TIPOS-DE-PRODUCAO-TECNICA>
        </PRODUCAO-TECNICA>
        """
    )

    result = parse_lattes_xml_with_report(xml_bytes)
    assert len(result.curriculum.records) == 1
    rec = result.curriculum.records[0]

    assert rec.category == LattesCategory.APRESENTACAO_TRABALHO
    assert rec.subtype == "APRESENTACAO_DE_TRABALHO"
    assert rec.title == "Palestra Magistral Fictícia"
    assert rec.event_name == "Conferência Regional de Sistemas"
    assert rec.nature_raw == "CONFERENCIA"
    assert rec.participation_type_raw is None
    assert rec.participation_form_raw is None
    assert rec.participation_role is None
    assert rec.workload_hours is None
    assert rec.validation_code is None
    assert rec.provenance.raw_attributes["DADOS-BASICOS-DA-APRESENTACAO-DE-TRABALHO/@PAIS"] == "Brasil"
    assert rec.provenance.raw_attributes["DADOS-BASICOS-DA-APRESENTACAO-DE-TRABALHO/@IDIOMA"] == "Português"


def test_organizacao_evento_derives_organizador_from_tag_and_preserves_separations() -> None:
    xml_bytes = _wrap_xml(
        """
        <PRODUCAO-TECNICA>
            <DEMAIS-TIPOS-DE-PRODUCAO-TECNICA>
                <ORGANIZACAO-DE-EVENTO SEQUENCIA-PRODUCAO="2">
                    <DADOS-BASICOS-DA-ORGANIZACAO-DE-EVENTO
                        TIPO="SIMPOSIO"
                        NATUREZA="ORGANIZACAO"
                        TITULO="Simpósio Fictício de Auditoria"
                        ANO="2024"
                        PAIS="Portugal"
                        IDIOMA="Português" />
                    <DETALHAMENTO-DA-ORGANIZACAO-DE-EVENTO
                        INSTITUICAO-PROMOTORA="Universidade Atlântica Fictícia"
                        DURACAO-EM-SEMANAS="2"
                        LOCAL="Centro Cultural"
                        CIDADE="Porto" />
                </ORGANIZACAO-DE-EVENTO>
            </DEMAIS-TIPOS-DE-PRODUCAO-TECNICA>
        </PRODUCAO-TECNICA>
        """
    )

    result = parse_lattes_xml_with_report(xml_bytes)
    assert len(result.curriculum.records) == 1
    rec = result.curriculum.records[0]

    assert rec.category == LattesCategory.ORGANIZACAO_EVENTO
    assert rec.subtype == "ORGANIZACAO_DE_EVENTO"
    assert rec.title == "Simpósio Fictício de Auditoria"
    assert rec.event_name is None
    assert rec.institution == "Universidade Atlântica Fictícia"
    assert rec.location == "Centro Cultural"
    assert rec.city == "Porto"
    assert rec.nature_raw == "ORGANIZACAO"
    assert rec.participation_role == "ORGANIZADOR"
    assert rec.workload_hours is None
    assert rec.validation_code is None
    assert rec.provenance.raw_attributes["DADOS-BASICOS-DA-ORGANIZACAO-DE-EVENTO/@PAIS"] == "Portugal"
    assert rec.provenance.raw_attributes["DADOS-BASICOS-DA-ORGANIZACAO-DE-EVENTO/@IDIOMA"] == "Português"
    assert rec.provenance.raw_attributes["DETALHAMENTO-DA-ORGANIZACAO-DE-EVENTO/@DURACAO-EM-SEMANAS"] == "2"


@pytest.mark.parametrize(
    ("tipo_part", "forma_part", "expected_role", "expect_unverified"),
    [
        ("Ouvinte", "Presencial", "OUVINTE", False),
        ("Palestrante", None, "PALESTRANTE", False),
        ("Conferencista", "Convidado", "PALESTRANTE", False),
        ("Apresentador", None, "APRESENTADOR", False),
        ("Apresentação de Trabalho", None, "APRESENTADOR", False),
        ("Organizador", None, "ORGANIZADOR", False),
        ("Comissão Organizadora", None, "ORGANIZADOR", False),
        ("Participante", None, "PARTICIPANTE", False),
        ("Congressista", None, "PARTICIPANTE", False),
        ("Debatedor de Mesa", "Presencial", None, True),
        ("Ouvinte", "Palestrante", None, True),
        ("   ", "", None, False),
    ],
)
def test_event_participation_role_mapping_and_unknown_or_conflicting_preservation(
    tipo_part: str | None,
    forma_part: str | None,
    expected_role: str | None,
    expect_unverified: bool,
) -> None:
    attrs = ['NATUREZA="Congresso"', 'TITULO="Trabalho"', 'ANO="2025"']
    if tipo_part is not None:
        attrs.append(f'TIPO-PARTICIPACAO="{tipo_part}"')
    if forma_part is not None:
        attrs.append(f'FORMA-PARTICIPACAO="{forma_part}"')

    xml_bytes = _wrap_xml(
        f"""
        <DADOS-COMPLEMENTARES>
            <PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
                <PARTICIPACAO-EM-CONGRESSO SEQUENCIA-PRODUCAO="1">
                    <DADOS-BASICOS-DA-PARTICIPACAO-EM-CONGRESSO {" ".join(attrs)} />
                    <DETALHAMENTO-DA-PARTICIPACAO-EM-CONGRESSO NOME-DO-EVENTO="Congresso Modelo" />
                </PARTICIPACAO-EM-CONGRESSO>
            </PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
        </DADOS-COMPLEMENTARES>
        """
    )

    result = parse_lattes_xml_with_report(xml_bytes)
    rec = result.curriculum.records[0]

    assert rec.nature_raw == "Congresso"
    assert rec.participation_role == expected_role
    expected_tipo = tipo_part.strip() or None if tipo_part is not None else None
    expected_forma = forma_part.strip() or None if forma_part is not None else None
    assert rec.participation_type_raw == expected_tipo
    assert rec.participation_form_raw == expected_forma
    if expect_unverified:
        assert any("PARTICIPACAO" in item for item in result.unverified_variants)


def test_technical_production_enforces_security_limits_and_strict_year() -> None:
    xxe_bytes = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<!DOCTYPE CURRICULO-VITAE [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        b'<CURRICULO-VITAE><PRODUCAO-TECNICA><DEMAIS-TIPOS-DE-PRODUCAO-TECNICA>'
        b'<APRESENTACAO-DE-TRABALHO><DADOS-BASICOS-DA-APRESENTACAO-DE-TRABALHO TITULO="&xxe;" />'
        b'</APRESENTACAO-DE-TRABALHO></DEMAIS-TIPOS-DE-PRODUCAO-TECNICA></PRODUCAO-TECNICA>'
        b'</CURRICULO-VITAE>'
    )
    with pytest.raises(LattesXmlSecurityError):
        parse_lattes_xml_with_report(xxe_bytes)

    bad_year_bytes = _wrap_xml(
        """
        <PRODUCAO-TECNICA>
            <DEMAIS-TIPOS-DE-PRODUCAO-TECNICA>
                <APRESENTACAO-DE-TRABALHO>
                    <DADOS-BASICOS-DA-APRESENTACAO-DE-TRABALHO ANO="2025.5" />
                </APRESENTACAO-DE-TRABALHO>
            </DEMAIS-TIPOS-DE-PRODUCAO-TECNICA>
        </PRODUCAO-TECNICA>
        """
    )
    with pytest.raises(LattesNumericValueError):
        parse_lattes_xml_with_report(bad_year_bytes)

    with pytest.raises(LattesResourceLimitError):
        parse_lattes_xml_with_report(bad_year_bytes, max_depth=3)
