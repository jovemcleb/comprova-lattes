import warnings
from decimal import Decimal

import pytest

from comprova_lattes.parser import (
    DEFAULT_MAX_XML_BYTES,
    DEFAULT_MAX_XML_DEPTH,
    DIAGNOSTIC_INVALID_WORKLOAD_HOURS,
    LattesEncodingError,
    LattesInvalidRootError,
    LattesMalformedXmlError,
    LattesNumericValueError,
    LattesParseDiagnostic,
    LattesParserError,
    LattesParseResult,
    LattesParserWarning,
    LattesResourceLimitError,
    LattesXmlSecurityError,
    parse_lattes_xml,
    parse_lattes_xml_with_report,
)
from comprova_lattes.schemas import ActivityStatus, LattesCategory, LattesCurriculum


def _wrap_xml(
    body: str,
    *,
    declaration: str = '<?xml version="1.0" encoding="UTF-8"?>',
    root_attrs: str = 'NUMERO-IDENTIFICADOR="0000000000000001" DATA-ATUALIZACAO="12112026"',
    encoding: str = "utf-8",
) -> bytes:
    xml_text = f"{declaration}<CURRICULO-VITAE {root_attrs}>{body}</CURRICULO-VITAE>"
    return xml_text.encode(encoding)


def test_parse_valid_utf8_three_sections_and_curriculum_metadata() -> None:
    xml_bytes = _wrap_xml(
        """
        <DADOS-GERAIS NOME-COMPLETO="Marina Oliveira Costa"
                      NOME-EM-CITACOES-BIBLIOGRAFICAS="COSTA, M. O.; ; OLIVEIRA, Marina ">
            <RESUMO-CV TEXTO-RESUMO-CV-RH="Pesquisadora fictícia em sistemas de informação." />
            <FORMACAO-ACADEMICA-TITULACAO>
                <GRADUACAO SEQUENCIA-FORMACAO="1"
                           NOME-INSTITUICAO="Universidade Federal do Norte"
                           SIGLA-INSTITUICAO="UFN"
                           NOME-CURSO="Sistemas de Informação"
                           ANO-DE-INICIO="2020"
                           ANO-DE-CONCLUSAO="2024"
                           CARGA-HORARIA="3000.5"
                           STATUS-DO-CURSO="CONCLUIDO"
                           CODIGO-CURSO-CAPES="999888" />
                <MESTRADO SEQUENCIA-FORMACAO="2"
                          NOME-INSTITUICAO="Instituto Fictício de Pesquisa"
                          TITULO-DA-DISSERTACAO-TESE="Análise Determinística de Registros"
                          ANO-DE-INICIO="2025"
                          STATUS-DO-CURSO="EM_ANDAMENTO" />
            </FORMACAO-ACADEMICA-TITULACAO>
        </DADOS-GERAIS>
        <DADOS-COMPLEMENTARES>
            <FORMACAO-COMPLEMENTAR>
                <FORMACAO-COMPLEMENTAR-DE-EXTENSAO-UNIVERSITARIA
                    SEQUENCIA-FORMACAO="3"
                    NOME-INSTITUICAO="Faculdade Modelo"
                    NOME-CURSO="Oficina de Python Seguro"
                    ANO-DE-INICIO="2023"
                    ANO-DE-CONCLUSAO="2023"
                    CARGA-HORARIA="40.5"
                    STATUS-DO-CURSO="CONCLUIDO" />
                <FORMACAO-COMPLEMENTAR-CURSO-DE-CURTA-DURACAO
                    SEQUENCIA-FORMACAO="4"
                    NOME-INSTITUICAO="Escola Técnica Fictícia"
                    NOME-CURSO="Introdução a Bancos de Dados"
                    CARGA-HORARIA="12.75"
                    STATUS-DO-CURSO="INCOMPLETO" />
            </FORMACAO-COMPLEMENTAR>
            <PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
                <PARTICIPACAO-EM-CONGRESSO SEQUENCIA-PRODUCAO="10">
                    <DADOS-BASICOS-DA-PARTICIPACAO-EM-CONGRESSO
                        TITULO="Validação Semiautomatizada de Registros"
                        ANO="2024"
                        NATUREZA="Congresso" />
                    <DETALHAMENTO-DA-PARTICIPACAO-EM-CONGRESSO
                        NOME-DO-EVENTO="Congresso Regional de Computação"
                        NOME-INSTITUICAO="Sociedade Fictícia de Computação"
                        CIDADE-DO-EVENTO="Belém"
                        LOCAL-DO-EVENTO="Centro de Convenções"
                        CARGA-HORARIA="16.25" />
                </PARTICIPACAO-EM-CONGRESSO>
            </PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
        </DADOS-COMPLEMENTARES>
        """
    )

    curriculum = parse_lattes_xml(xml_bytes)

    assert isinstance(curriculum, LattesCurriculum)
    assert curriculum.lattes_id == "0000000000000001"
    assert curriculum.updated_at == "12112026"
    assert curriculum.full_name == "Marina Oliveira Costa"
    assert curriculum.citation_names == ["COSTA, M. O.", "OLIVEIRA, Marina"]
    assert curriculum.summary == "Pesquisadora fictícia em sistemas de informação."
    assert len(curriculum.records) == 5

    grad, mestr, ext, curta, evento = curriculum.records

    assert grad.category == LattesCategory.FORMACAO_ACADEMICA
    assert grad.subtype == "GRADUACAO"
    assert grad.sequence == "1"
    assert grad.holder_name == "Marina Oliveira Costa"
    assert grad.institution == "Universidade Federal do Norte"
    assert grad.institution_acronym == "UFN"
    assert grad.title == "Sistemas de Informação"
    assert grad.start_year == 2020
    assert grad.end_year == 2024
    assert grad.workload_hours == Decimal("3000.5")
    assert grad.status == ActivityStatus.CONCLUIDO
    assert grad.validation_code is None
    assert grad.provenance.parent_tag == "DADOS-GERAIS"
    assert grad.provenance.section_tag == "FORMACAO-ACADEMICA-TITULACAO"
    assert grad.provenance.record_tag == "GRADUACAO"
    assert grad.provenance.sequence_attribute == "SEQUENCIA-FORMACAO"
    assert grad.provenance.raw_attributes["CODIGO-CURSO-CAPES"] == "999888"

    assert mestr.title == "Análise Determinística de Registros"
    assert mestr.status == ActivityStatus.EM_ANDAMENTO
    assert mestr.end_year is None

    assert ext.category == LattesCategory.FORMACAO_COMPLEMENTAR
    assert ext.subtype == "EXTENSAO_UNIVERSITARIA"
    assert ext.workload_hours == Decimal("40.5")

    assert curta.category == LattesCategory.FORMACAO_COMPLEMENTAR
    assert curta.subtype == "CURTA_DURACAO"
    assert curta.workload_hours == Decimal("12.75")
    assert curta.status == ActivityStatus.INCOMPLETO

    assert evento.category == LattesCategory.PARTICIPACAO_EVENTO
    assert evento.subtype == "CONGRESSO"
    assert evento.sequence == "10"
    assert evento.title == "Validação Semiautomatizada de Registros"
    assert evento.event_name == "Congresso Regional de Computação"
    assert evento.institution == "Sociedade Fictícia de Computação"
    assert evento.city == "Belém"
    assert evento.location == "Centro de Convenções"
    assert evento.start_year == 2024
    assert evento.end_year == 2024
    assert evento.workload_hours == Decimal("16.25")
    assert evento.status is None
    assert evento.provenance.parent_tag == "DADOS-COMPLEMENTARES"
    assert evento.provenance.section_tag == "PARTICIPACAO-EM-EVENTOS-CONGRESSOS"
    assert evento.provenance.record_tag == "PARTICIPACAO-EM-CONGRESSO"
    assert evento.provenance.sequence_attribute == "SEQUENCIA-PRODUCAO"


def test_parse_respects_iso_8859_1_and_utf8_bom_by_xml_declaration() -> None:
    iso_bytes = _wrap_xml(
        """
        <DADOS-GERAIS NOME-COMPLETO="João Pedro Conceição">
            <FORMACAO-ACADEMICA-TITULACAO>
                <GRADUACAO SEQUENCIA-FORMACAO="1"
                           NOME-INSTITUICAO="Instituição de Educação Agrícola"
                           NOME-CURSO="Agronomia e Produção" />
            </FORMACAO-ACADEMICA-TITULACAO>
        </DADOS-GERAIS>
        """,
        declaration='<?xml version="1.0" encoding="ISO-8859-1" standalone="no"?>',
        encoding="iso-8859-1",
    )

    iso_result = parse_lattes_xml_with_report(iso_bytes)
    assert iso_result.declared_encoding == "ISO-8859-1"
    assert iso_result.curriculum.full_name == "João Pedro Conceição"
    assert iso_result.curriculum.records[0].institution == "Instituição de Educação Agrícola"
    assert iso_result.curriculum.records[0].title == "Agronomia e Produção"

    utf8_bom_bytes = b"\xef\xbb\xbf" + _wrap_xml(
        '<DADOS-GERAIS NOME-COMPLETO="Ágata São Tomé" />',
        declaration='<?xml version="1.0"?>',
        encoding="utf-8",
    )
    bom_result = parse_lattes_xml_with_report(utf8_bom_bytes)
    assert bom_result.declared_encoding == "UTF-8"
    assert bom_result.curriculum.full_name == "Ágata São Tomé"


def test_parse_rejects_encoding_mismatch_and_unsupported_encoding_without_silent_fallback() -> None:
    # ISO-8859-1 bytes under UTF-8 declaration must fail, not silently fall back to latin-1
    mismatched_utf8 = _wrap_xml(
        '<DADOS-GERAIS NOME-COMPLETO="Educação" />',
        declaration='<?xml version="1.0" encoding="UTF-8"?>',
        encoding="iso-8859-1",
    )
    with pytest.raises(LattesEncodingError):
        parse_lattes_xml(mismatched_utf8)

    # ISO-8859-1 bytes without declaration default to UTF-8 per XML 1.0 and must fail
    no_decl_iso = '<CURRICULO-VITAE><DADOS-GERAIS NOME-COMPLETO="Educação" /></CURRICULO-VITAE>'.encode(
        "iso-8859-1"
    )
    with pytest.raises(LattesEncodingError):
        parse_lattes_xml(no_decl_iso)

    # Unsupported encoding declaration
    unsupported_decl = _wrap_xml(
        '<DADOS-GERAIS NOME-COMPLETO="Carlos" />',
        declaration='<?xml version="1.0" encoding="WINDOWS-1252"?>',
        encoding="cp1252",
    )
    with pytest.raises(LattesEncodingError):
        parse_lattes_xml(unsupported_decl)

    # UTF-8 BOM conflicting with ISO-8859-1 declaration
    conflicting_bom = b"\xef\xbb\xbf" + _wrap_xml(
        '<DADOS-GERAIS NOME-COMPLETO="Carlos" />',
        declaration='<?xml version="1.0" encoding="ISO-8859-1"?>',
        encoding="utf-8",
    )
    with pytest.raises(LattesEncodingError):
        parse_lattes_xml(conflicting_bom)


@pytest.mark.parametrize(
    "malicious_xml",
    [
        (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<!DOCTYPE CURRICULO-VITAE [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
            b'<CURRICULO-VITAE><DADOS-GERAIS NOME-COMPLETO="&xxe;" /></CURRICULO-VITAE>'
        ),
        (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<!DOCTYPE CURRICULO-VITAE [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;">]>'
            b'<CURRICULO-VITAE><DADOS-GERAIS NOME-COMPLETO="&lol2;" /></CURRICULO-VITAE>'
        ),
        (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<!DOCTYPE CURRICULO-VITAE SYSTEM "http://127.0.0.1:9/lattes.dtd">'
            b'<CURRICULO-VITAE><DADOS-GERAIS NOME-COMPLETO="Ana" /></CURRICULO-VITAE>'
        ),
        (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<!DOCTYPE CURRICULO-VITAE PUBLIC "-//CNPq//DTD Lattes//PT" "http://127.0.0.1:9/lattes.dtd">'
            b'<CURRICULO-VITAE><DADOS-GERAIS NOME-COMPLETO="Ana" /></CURRICULO-VITAE>'
        ),
    ],
)
def test_parse_rejects_entities_and_external_dtd_without_network(malicious_xml: bytes) -> None:
    with pytest.raises(LattesXmlSecurityError):
        parse_lattes_xml(malicious_xml)


@pytest.mark.parametrize(
    "bad_xml",
    [
        b"",
        b"   \n\t ",
        b"nao eh xml",
        b"<CURRICULO-VITAE><DADOS-GERAIS></CURRICULO-VITAE>",
        b'<?xml version="1.0" encoding="UTF-8"?><CURRICULO-VITAE>',
    ],
)
def test_parse_rejects_malformed_and_empty_xml(bad_xml: bytes) -> None:
    with pytest.raises(LattesMalformedXmlError):
        parse_lattes_xml(bad_xml)


@pytest.mark.parametrize(
    "wrong_root_xml",
    [
        b'<?xml version="1.0" encoding="UTF-8"?><OUTRO-DOCUMENTO />',
        b'<?xml version="1.0" encoding="UTF-8"?><DADOS-GERAIS NOME-COMPLETO="Teste" />',
        b'<?xml version="1.0" encoding="UTF-8"?><CURRICULO-VITAE xmlns="https://exemplo.invalid/ns" />',
    ],
)
def test_parse_rejects_wrong_root_element(wrong_root_xml: bytes) -> None:
    with pytest.raises(LattesInvalidRootError):
        parse_lattes_xml(wrong_root_xml)


def test_parse_missing_fields_remain_none_without_invented_sentinels() -> None:
    xml_bytes = _wrap_xml(
        """
        <DADOS-GERAIS NOME-COMPLETO="   " NOME-EM-CITACOES-BIBLIOGRAFICAS=" ;  ">
            <FORMACAO-ACADEMICA-TITULACAO>
                <GRADUACAO CODIGO-INSTITUICAO="112233" CODIGO-CURSO="4455" />
            </FORMACAO-ACADEMICA-TITULACAO>
        </DADOS-GERAIS>
        <DADOS-COMPLEMENTARES>
            <FORMACAO-COMPLEMENTAR>
                <OUTROS-TIPOS-DE-FORMACAO-COMPLEMENTAR />
            </FORMACAO-COMPLEMENTAR>
            <PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
                <PARTICIPACAO-EM-SIMPOSIO>
                    <DETALHAMENTO-DA-PARTICIPACAO-EM-SIMPOSIO
                        CIDADE-DO-EVENTO="Marabá"
                        LOCAL-DO-EVENTO="Auditório Central" />
                </PARTICIPACAO-EM-SIMPOSIO>
            </PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
        </DADOS-COMPLEMENTARES>
        """,
        root_attrs='HORA-ATUALIZACAO="153000"',
    )

    curriculum = parse_lattes_xml(xml_bytes)

    assert curriculum.lattes_id is None
    assert curriculum.updated_at is None
    assert curriculum.full_name is None
    assert curriculum.citation_names == []
    assert curriculum.summary is None
    assert len(curriculum.records) == 3

    grad, comp, evento = curriculum.records

    assert grad.record_id is not None
    assert grad.record_id == parse_lattes_xml(xml_bytes).records[0].record_id
    assert grad.sequence is None
    assert grad.provenance.sequence_attribute is None
    assert grad.holder_name is None
    assert grad.institution is None
    assert grad.title is None
    assert grad.status is None
    assert grad.validation_code is None

    assert comp.subtype == "OUTROS"
    assert comp.sequence is None
    assert comp.institution is None
    assert comp.title is None
    assert comp.status is None

    # Event must not copy city/location into institution, nor invent title or status
    assert evento.institution is None
    assert evento.city == "Marabá"
    assert evento.location == "Auditório Central"
    assert evento.title is None
    assert evento.event_name is None
    assert evento.status is None


@pytest.mark.parametrize(
    "body_xml",
    [
        '<DADOS-GERAIS><FORMACAO-ACADEMICA-TITULACAO><GRADUACAO ANO-DE-INICIO="2024.5" /></FORMACAO-ACADEMICA-TITULACAO></DADOS-GERAIS>',
        '<DADOS-GERAIS><FORMACAO-ACADEMICA-TITULACAO><GRADUACAO ANO-DE-CONCLUSAO="2024.0" /></FORMACAO-ACADEMICA-TITULACAO></DADOS-GERAIS>',
        '<DADOS-GERAIS><FORMACAO-ACADEMICA-TITULACAO><GRADUACAO ANO-DE-OBTENCAO-DO-TITULO="abc" /></FORMACAO-ACADEMICA-TITULACAO></DADOS-GERAIS>',
        (
            "<DADOS-COMPLEMENTARES><PARTICIPACAO-EM-EVENTOS-CONGRESSOS>"
            '<PARTICIPACAO-EM-CONGRESSO><DADOS-BASICOS-DA-PARTICIPACAO-EM-CONGRESSO ANO="2024.5" /></PARTICIPACAO-EM-CONGRESSO>'
            "</PARTICIPACAO-EM-EVENTOS-CONGRESSOS></DADOS-COMPLEMENTARES>"
        ),
    ],
)
def test_parse_raises_explicit_error_on_invalid_year_attributes_without_truncation(
    body_xml: str,
) -> None:
    xml_bytes = _wrap_xml(body_xml)

    with pytest.raises(LattesNumericValueError):
        parse_lattes_xml(xml_bytes)


@pytest.mark.parametrize(
    "raw_hours",
    [
        "-10",
        "-0.5",
        "40,5",
        "40h",
        "abc",
        "NaN",
        "sNaN",
        "Infinity",
        "-Infinity",
    ],
)
def test_parse_discards_invalid_workload_hours_with_diagnostic_and_preserves_record(
    raw_hours: str,
) -> None:
    xml_bytes = _wrap_xml(
        f"""
        <DADOS-GERAIS NOME-COMPLETO="Marina Oliveira Costa">
            <FORMACAO-ACADEMICA-TITULACAO>
                <GRADUACAO SEQUENCIA-FORMACAO="1"
                           NOME-INSTITUICAO="Universidade Federal do Norte"
                           NOME-CURSO="Sistemas de Informação"
                           ANO-DE-INICIO="2020"
                           CARGA-HORARIA="{raw_hours}" />
                <MESTRADO SEQUENCIA-FORMACAO="2"
                          NOME-INSTITUICAO="Instituto Fictício"
                          NOME-CURSO="Computação Aplicada"
                          CARGA-HORARIA="1200.5" />
            </FORMACAO-ACADEMICA-TITULACAO>
        </DADOS-GERAIS>
        """
    )

    with warnings.catch_warnings(record=True) as captured_report_warnings:
        warnings.simplefilter("always")
        result = parse_lattes_xml_with_report(xml_bytes)

    assert not [w for w in captured_report_warnings if issubclass(w.category, LattesParserWarning)]
    assert len(result.curriculum.records) == 2

    grad, mestr = result.curriculum.records
    assert grad.title == "Sistemas de Informação"
    assert grad.start_year == 2020
    assert grad.workload_hours is None
    assert grad.provenance.raw_attributes["CARGA-HORARIA"] == raw_hours

    assert mestr.workload_hours == Decimal("1200.5")

    assert len(result.diagnostics) == 1
    diag = result.diagnostics[0]
    assert isinstance(diag, LattesParseDiagnostic)
    assert diag.code == DIAGNOSTIC_INVALID_WORKLOAD_HOURS
    assert diag.record_path == "CURRICULO-VITAE/DADOS-GERAIS/FORMACAO-ACADEMICA-TITULACAO/GRADUACAO"
    assert diag.attribute == "CARGA-HORARIA"
    assert diag.original_value == raw_hours
    assert diag.record_index == 0
    assert "CARGA-HORARIA" in diag.reason or "carga horária" in diag.reason.lower()

    with pytest.warns(LattesParserWarning) as warning_records:
        simplified = parse_lattes_xml(xml_bytes)

    assert len(warning_records) == 1
    assert raw_hours in str(warning_records[0].message)
    assert simplified.records[0].workload_hours is None
    assert simplified.records[1].workload_hours == Decimal("1200.5")


def test_parse_invalid_workload_diagnostics_track_subnode_paths_and_record_indices() -> None:
    xml_bytes = _wrap_xml(
        """
        <DADOS-GERAIS>
            <FORMACAO-ACADEMICA-TITULACAO>
                <GRADUACAO NOME-CURSO="Curso Válido" CARGA-HORARIA="3000" />
            </FORMACAO-ACADEMICA-TITULACAO>
        </DADOS-GERAIS>
        <DADOS-COMPLEMENTARES>
            <FORMACAO-COMPLEMENTAR>
                <FORMACAO-COMPLEMENTAR-DE-EXTENSAO-UNIVERSITARIA
                    NOME-CURSO="Oficina"
                    CARGA-HORARIA="-12.5" />
            </FORMACAO-COMPLEMENTAR>
            <PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
                <PARTICIPACAO-EM-CONGRESSO SEQUENCIA-PRODUCAO="1">
                    <DADOS-BASICOS-DA-PARTICIPACAO-EM-CONGRESSO TITULO="Trabalho" ANO="2024" />
                    <DETALHAMENTO-DA-PARTICIPACAO-EM-CONGRESSO
                        NOME-DO-EVENTO="Congresso"
                        CARGA-HORARIA="20h" />
                </PARTICIPACAO-EM-CONGRESSO>
            </PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
        </DADOS-COMPLEMENTARES>
        """
    )

    result = parse_lattes_xml_with_report(xml_bytes)

    assert len(result.curriculum.records) == 3
    assert result.curriculum.records[0].workload_hours == Decimal(3000)
    assert result.curriculum.records[1].workload_hours is None
    assert result.curriculum.records[2].workload_hours is None

    assert len(result.diagnostics) == 2
    comp_diag, event_diag = result.diagnostics
    assert comp_diag.record_index == 1
    assert (
        comp_diag.record_path
        == "CURRICULO-VITAE/DADOS-COMPLEMENTARES/FORMACAO-COMPLEMENTAR/FORMACAO-COMPLEMENTAR-DE-EXTENSAO-UNIVERSITARIA"
    )
    assert comp_diag.original_value == "-12.5"

    assert event_diag.record_index == 2
    assert (
        event_diag.record_path
        == "CURRICULO-VITAE/DADOS-COMPLEMENTARES/PARTICIPACAO-EM-EVENTOS-CONGRESSOS/PARTICIPACAO-EM-CONGRESSO/DETALHAMENTO-DA-PARTICIPACAO-EM-CONGRESSO"
    )
    assert event_diag.original_value == "20h"
    assert (
        result.curriculum.records[2].provenance.raw_attributes[
            "DETALHAMENTO-DA-PARTICIPACAO-EM-CONGRESSO/@CARGA-HORARIA"
        ]
        == "20h"
    )


@pytest.mark.parametrize("raw_hours", ["", "   "])
def test_parse_missing_or_blank_workload_returns_none_without_diagnostics_or_warnings(
    raw_hours: str,
) -> None:
    xml_bytes = _wrap_xml(
        f"""
        <DADOS-GERAIS>
            <FORMACAO-ACADEMICA-TITULACAO>
                <GRADUACAO NOME-CURSO="Curso" CARGA-HORARIA="{raw_hours}" />
                <MESTRADO NOME-CURSO="Mestrado" />
            </FORMACAO-ACADEMICA-TITULACAO>
        </DADOS-GERAIS>
        """
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = parse_lattes_xml_with_report(xml_bytes)
        curriculum = parse_lattes_xml(xml_bytes)

    assert result.diagnostics == ()
    assert [w for w in caught if issubclass(w.category, LattesParserWarning)] == []
    assert all(rec.workload_hours is None for rec in curriculum.records)


@pytest.mark.parametrize(
    ("raw_hours", "expected"),
    [
        ("0", Decimal(0)),
        ("1.5", Decimal("1.5")),
        ("40.75", Decimal("40.75")),
        ("25000.25", Decimal("25000.25")),
    ],
)
def test_parse_preserves_valid_decimal_and_non_negative_workload_without_arbitrary_ceiling(
    raw_hours: str,
    expected: Decimal,
) -> None:
    xml_bytes = _wrap_xml(
        f"""
        <DADOS-GERAIS>
            <FORMACAO-ACADEMICA-TITULACAO>
                <GRADUACAO NOME-CURSO="Curso" CARGA-HORARIA="{raw_hours}" />
            </FORMACAO-ACADEMICA-TITULACAO>
        </DADOS-GERAIS>
        """
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = parse_lattes_xml_with_report(xml_bytes)

    assert result.diagnostics == ()
    assert [w for w in caught if issubclass(w.category, LattesParserWarning)] == []
    assert result.curriculum.records[0].workload_hours == expected
    assert isinstance(result.curriculum.records[0].workload_hours, Decimal)


def test_parse_preserves_subnode_attributes_in_provenance_without_silent_collision() -> None:
    xml_bytes = _wrap_xml(
        """
        <DADOS-COMPLEMENTARES>
            <PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
                <PARTICIPACAO-EM-CONGRESSO SEQUENCIA-PRODUCAO="7" NOME-INSTITUICAO="Instituição Nó Pai" ANO="2022">
                    <DADOS-BASICOS-DA-PARTICIPACAO-EM-CONGRESSO
                        TITULO="Título do Trabalho"
                        ANO="2024"
                        NOME-INSTITUICAO="Instituição Dados Básicos"
                        NATUREZA="Congresso"
                        TIPO-PARTICIPACAO="Ouvinte" />
                    <DETALHAMENTO-DA-PARTICIPACAO-EM-CONGRESSO
                        NOME-DO-EVENTO="Congresso Fictício de Software"
                        NOME-INSTITUICAO="Instituição Detalhamento"
                        CIDADE-DO-EVENTO="Santarém" />
                </PARTICIPACAO-EM-CONGRESSO>
            </PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
        </DADOS-COMPLEMENTARES>
        """
    )

    curriculum = parse_lattes_xml(xml_bytes)
    assert len(curriculum.records) == 1
    record = curriculum.records[0]

    assert record.title == "Título do Trabalho"
    assert record.event_name == "Congresso Fictício de Software"
    assert record.institution == "Instituição Detalhamento"
    assert record.start_year == 2024
    assert record.end_year == 2024

    raw = record.provenance.raw_attributes
    assert raw["NOME-INSTITUICAO"] == "Instituição Nó Pai"
    assert raw["ANO"] == "2022"
    assert raw["DADOS-BASICOS-DA-PARTICIPACAO-EM-CONGRESSO/@NOME-INSTITUICAO"] == "Instituição Dados Básicos"
    assert raw["DADOS-BASICOS-DA-PARTICIPACAO-EM-CONGRESSO/@ANO"] == "2024"
    assert raw["DADOS-BASICOS-DA-PARTICIPACAO-EM-CONGRESSO/@TIPO-PARTICIPACAO"] == "Ouvinte"
    assert raw["DETALHAMENTO-DA-PARTICIPACAO-EM-CONGRESSO/@NOME-INSTITUICAO"] == "Instituição Detalhamento"
    assert raw["DETALHAMENTO-DA-PARTICIPACAO-EM-CONGRESSO/@NOME-DO-EVENTO"] == "Congresso Fictício de Software"


def test_parse_does_not_infer_unknown_status_and_reports_unverified_variants_and_unknown_tags() -> None:
    xml_bytes = _wrap_xml(
        """
        <DADOS-GERAIS NOME-COMPLETO="Lucas Andrade">
            <FORMACAO-ACADEMICA-TITULACAO>
                <ENSINO-MEDIO SEQUENCIA-FORMACAO="1"
                              NOME-INSTITUICAO="Colégio Fictício"
                              STATUS-DO-CURSO="TRANCADO" />
                <TAG-DESCONHECIDA QUALQUER="valor" />
            </FORMACAO-ACADEMICA-TITULACAO>
            <FORMACAO-COMPLEMENTAR>
                <MBA SEQUENCIA-FORMACAO="2" NOME-CURSO="MBA em Dados" />
            </FORMACAO-COMPLEMENTAR>
        </DADOS-GERAIS>
        <DADOS-COMPLEMENTARES>
            <FORMACAO-ACADEMICA-TITULACAO>
                <GRADUACAO NOME-CURSO="Ignorado por caminho inválido" />
            </FORMACAO-ACADEMICA-TITULACAO>
            <PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
                <OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS SEQUENCIA-FORMACAO="3">
                    <DETALHAMENTO-DE-OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS
                        NOME-DO-EVENTO="Semana Acadêmica" />
                </OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS>
            </PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
        </DADOS-COMPLEMENTARES>
        <PRODUCAO-BIBLIOGRAFICA>
            <ARTIGO-PUBLICADO />
        </PRODUCAO-BIBLIOGRAFICA>
        """,
        root_attrs='IDENTIFICADOR-CNPQ="8887776665554443" DATA-ATUALIZACAO="01012026"',
    )

    result = parse_lattes_xml_with_report(xml_bytes)
    assert isinstance(result, LattesParseResult)
    curriculum = result.curriculum

    assert curriculum.lattes_id == "8887776665554443"
    assert curriculum.updated_at == "01012026"
    # Only the 3 recognized records (ENSINO-MEDIO, MBA in DADOS-GERAIS/FORMACAO-COMPLEMENTAR, OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS)
    assert len(curriculum.records) == 3

    ensino_medio, mba, evento = curriculum.records
    assert ensino_medio.subtype == "ENSINO_MEDIO"
    assert ensino_medio.status is None
    assert ensino_medio.provenance.raw_attributes["STATUS-DO-CURSO"] == "TRANCADO"

    assert mba.subtype == "MBA"
    assert mba.provenance.parent_tag == "DADOS-GERAIS"

    assert evento.subtype == "OUTRAS_PARTICIPACOES"
    assert evento.sequence == "3"
    assert evento.provenance.sequence_attribute == "SEQUENCIA-FORMACAO"
    assert evento.event_name == "Semana Acadêmica"
    assert evento.title is None

    assert "CURRICULO-VITAE/DADOS-GERAIS/FORMACAO-ACADEMICA-TITULACAO/TAG-DESCONHECIDA" in result.unrecognized_elements
    assert any("IDENTIFICADOR-CNPQ" in item for item in result.unverified_variants)
    assert any("ENSINO-MEDIO" in item for item in result.unverified_variants)
    assert any("DADOS-GERAIS/FORMACAO-COMPLEMENTAR" in item for item in result.unverified_variants)
    assert any("MBA" in item for item in result.unverified_variants)
    assert any("OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS" in item for item in result.unverified_variants)
    assert any("STATUS-DO-CURSO" in item for item in result.unverified_variants)


def test_parse_accepts_type_error_for_non_bytes_and_exception_hierarchy() -> None:
    assert issubclass(LattesEncodingError, LattesParserError)
    assert issubclass(LattesXmlSecurityError, LattesParserError)
    assert issubclass(LattesResourceLimitError, LattesParserError)
    assert issubclass(LattesMalformedXmlError, LattesParserError)
    assert issubclass(LattesInvalidRootError, LattesParserError)
    assert issubclass(LattesNumericValueError, LattesParserError)
    assert issubclass(LattesParserWarning, UserWarning)

    with pytest.raises(TypeError):
        parse_lattes_xml("<CURRICULO-VITAE />")  # type: ignore[arg-type]


def test_parse_resource_limit_defaults_and_positive_validation() -> None:
    assert DEFAULT_MAX_XML_BYTES == 10 * 1024 * 1024
    assert DEFAULT_MAX_XML_DEPTH == 64

    xml_bytes = _wrap_xml("")
    for bad_limit in (0, -1, True, False):
        with pytest.raises(ValueError):
            parse_lattes_xml(xml_bytes, max_bytes=bad_limit)
        with pytest.raises(ValueError):
            parse_lattes_xml_with_report(xml_bytes, max_depth=bad_limit)


def test_parse_enforces_max_bytes_boundary_before_decoding() -> None:
    xml_bytes = _wrap_xml('<DADOS-GERAIS NOME-COMPLETO="Ana" />')

    exact_result = parse_lattes_xml_with_report(xml_bytes, max_bytes=len(xml_bytes))
    assert exact_result.curriculum.full_name == "Ana"

    with pytest.raises(LattesResourceLimitError):
        parse_lattes_xml(xml_bytes, max_bytes=len(xml_bytes) - 1)

    # Invalid UTF-8 bytes must fail on byte limit BEFORE decoding raises LattesEncodingError.
    invalid_utf8_oversized = b"\xff" * 65
    with pytest.raises(LattesResourceLimitError):
        parse_lattes_xml(invalid_utf8_oversized, max_bytes=64)


def test_parse_enforces_max_depth_boundary_and_aborts_deep_payload_during_parsing() -> None:
    # Depth 5: CURRICULO-VITAE (1) -> DADOS-GERAIS (2) -> FORMACAO-ACADEMICA-TITULACAO (3)
    # -> GRADUACAO (4) -> SUBNO (5)
    depth5_xml = _wrap_xml(
        "<DADOS-GERAIS><FORMACAO-ACADEMICA-TITULACAO><GRADUACAO><SUBNO /></GRADUACAO></FORMACAO-ACADEMICA-TITULACAO></DADOS-GERAIS>"
    )

    ok = parse_lattes_xml(depth5_xml, max_depth=5)
    assert len(ok.records) == 1

    with pytest.raises(LattesResourceLimitError):
        parse_lattes_xml(depth5_xml, max_depth=4)

    # Deep payload exceeding Python's default recursion limit if traversed recursively;
    # bounded TreeBuilder must abort immediately at depth 65 without RecursionError.
    deep_payload = b"<CURRICULO-VITAE>" + (b"<N>" * 2000) + (b"</N>" * 2000) + b"</CURRICULO-VITAE>"
    with pytest.raises(LattesResourceLimitError):
        parse_lattes_xml_with_report(deep_payload)


def test_parse_preserves_defusedxml_protections_with_custom_resource_limits() -> None:
    xxe_payload = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<!DOCTYPE CURRICULO-VITAE [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        b'<CURRICULO-VITAE><DADOS-GERAIS NOME-COMPLETO="&xxe;" /></CURRICULO-VITAE>'
    )
    with pytest.raises(LattesXmlSecurityError):
        parse_lattes_xml_with_report(xxe_payload, max_bytes=4096, max_depth=16)


def test_parse_minimal_root_and_repeated_subnodes_without_collision() -> None:
    empty_curriculum = parse_lattes_xml(b"<CURRICULO-VITAE />")
    assert empty_curriculum == LattesCurriculum()

    xml_bytes = _wrap_xml(
        """
        <DADOS-COMPLEMENTARES>
            <PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
                <PARTICIPACAO-EM-CONGRESSO SEQUENCIA-PRODUCAO="1">
                    <DADOS-BASICOS-DA-PARTICIPACAO-EM-CONGRESSO TITULO="Trabalho Principal" ANO="2024" />
                    <DETALHAMENTO-DA-PARTICIPACAO-EM-CONGRESSO NOME-DO-EVENTO="Evento Único" />
                    <AUTORES NOME-COMPLETO-DO-AUTOR="Marina Costa" />
                    <AUTORES NOME-COMPLETO-DO-AUTOR="Carlos Mendes" />
                </PARTICIPACAO-EM-CONGRESSO>
            </PARTICIPACAO-EM-EVENTOS-CONGRESSOS>
        </DADOS-COMPLEMENTARES>
        """,
        declaration='<?xml version="1.0" encoding="iso-8859-1"?>',
        encoding="iso-8859-1",
    )

    result = parse_lattes_xml_with_report(xml_bytes)
    assert result.declared_encoding == "ISO-8859-1"
    raw = result.curriculum.records[0].provenance.raw_attributes
    assert raw["AUTORES[1]/@NOME-COMPLETO-DO-AUTOR"] == "Marina Costa"
    assert raw["AUTORES[2]/@NOME-COMPLETO-DO-AUTOR"] == "Carlos Mendes"
