from comprova_lattes.parser import parse_lattes_xml_with_report
from comprova_lattes.parser.mappings import (
    ACADEMIC_TAG_SUBTYPES,
    EVENT_TAG_SUBTYPES,
    PARTICIPATION_ROLE_MAP,
    TECHNICAL_PRODUCTION_TAG_CATEGORIES,
    UNVERIFIED_VARIANT_TAGS,
)
from comprova_lattes.schemas import LattesCategory


def test_xsd_mappings_include_fundamental_olimpiada_and_technical_categories() -> None:
    assert ACADEMIC_TAG_SUBTYPES["ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU"] == "ENSINO_FUNDAMENTAL"
    assert EVENT_TAG_SUBTYPES["PARTICIPACAO-EM-OLIMPIADA"] == "OLIMPIADA"
    assert (
        TECHNICAL_PRODUCTION_TAG_CATEGORIES["APRESENTACAO-DE-TRABALHO"]
        == LattesCategory.APRESENTACAO_TRABALHO
    )
    assert (
        TECHNICAL_PRODUCTION_TAG_CATEGORIES["ORGANIZACAO-DE-EVENTO"]
        == LattesCategory.ORGANIZACAO_EVENTO
    )
    assert PARTICIPATION_ROLE_MAP["ouvinte"] == "OUVINTE"
    assert PARTICIPATION_ROLE_MAP["palestrante"] == "PALESTRANTE"
    assert PARTICIPATION_ROLE_MAP["conferencista"] == "PALESTRANTE"


def test_confirmed_xsd_tags_and_attributes_do_not_emit_stale_pendente_dtd_or_claim_ui_conformity() -> None:
    xml_bytes = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CURRICULO-VITAE SISTEMA-ORIGEM-XML="SINTETICO-TESTE" '
        'NUMERO-IDENTIFICADOR="9200111122223333" DATA-ATUALIZACAO="13112026">'
        '<DADOS-GERAIS NOME-COMPLETO="Clara Sintética" '
        'NOME-EM-CITACOES-BIBLIOGRAFICAS="SINTETICA, C." '
        'NACIONALIDADE="B" PERMISSAO-DE-DIVULGACAO="SIM">'
        "<FORMACAO-ACADEMICA-TITULACAO>"
        '<POS-DOUTORADO SEQUENCIA-FORMACAO="1" NOME-INSTITUICAO="Univ X" NOME-CURSO-INGLES="Postdoc" />'
        '<ENSINO-FUNDAMENTAL-PRIMEIRO-GRAU SEQUENCIA-FORMACAO="2" NOME-INSTITUICAO="Escola Y" />'
        "</FORMACAO-ACADEMICA-TITULACAO>"
        "</DADOS-GERAIS>"
        "<DADOS-COMPLEMENTARES>"
        "<FORMACAO-COMPLEMENTAR>"
        '<MBA SEQUENCIA-FORMACAO="1" NOME-CURSO="MBA Z" />'
        '<OUTROS SEQUENCIA-FORMACAO="2" NOME-CURSO-INGLES="Other Course" />'
        "</FORMACAO-COMPLEMENTAR>"
        "<PARTICIPACAO-EM-EVENTOS-CONGRESSOS>"
        '<PARTICIPACAO-EM-FEIRA SEQUENCIA-PRODUCAO="1">'
        '<DADOS-BASICOS-DA-PARTICIPACAO-EM-FEIRA TITULO="Feira" ANO="2024" />'
        '<DETALHAMENTO-DA-PARTICIPACAO-EM-FEIRA NOME-DO-EVENTO-INGLES="Tech Fair" />'
        "</PARTICIPACAO-EM-FEIRA>"
        '<PARTICIPACAO-EM-EXPOSICAO SEQUENCIA-PRODUCAO="2">'
        '<DADOS-BASICOS-DA-PARTICIPACAO-EM-EXPOSICAO TITULO="Expo" ANO="2024" />'
        "</PARTICIPACAO-EM-EXPOSICAO>"
        '<PARTICIPACAO-EM-OLIMPIADA SEQUENCIA-PRODUCAO="3">'
        '<DADOS-BASICOS-DA-PARTICIPACAO-EM-OLIMPIADA TITULO="Olimpíada" ANO="2024" />'
        "</PARTICIPACAO-EM-OLIMPIADA>"
        '<OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS SEQUENCIA-PRODUCAO="4">'
        '<DETALHAMENTO-DE-OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS NOME-DO-EVENTO="Outro" />'
        "</OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS>"
        "</PARTICIPACAO-EM-EVENTOS-CONGRESSOS>"
        "</DADOS-COMPLEMENTARES>"
        "</CURRICULO-VITAE>"
    ).encode()

    result = parse_lattes_xml_with_report(xml_bytes)

    assert result.unrecognized_elements == ()
    assert len(result.curriculum.records) == 8

    for message in result.unverified_variants:
        assert "pendente DTD" not in message
        assert "conforme UI" not in message.lower()

    for tag in (
        "POS-DOUTORADO",
        "LIVRE-DOCENCIA",
        "MESTRADO-PROFISSIONALIZANTE",
        "ENSINO-MEDIO-SEGUNDO-GRAU",
        "RESIDENCIA-MEDICA",
        "MBA",
        "OUTROS",
        "PARTICIPACAO-EM-SEMINARIO",
        "PARTICIPACAO-EM-OFICINA",
        "PARTICIPACAO-EM-ENCONTRO",
        "PARTICIPACAO-EM-EXPOSICAO",
        "OUTRAS-PARTICIPACOES-EM-EVENTOS-CONGRESSOS",
    ):
        assert tag in UNVERIFIED_VARIANT_TAGS
        assert "pendente DTD" not in UNVERIFIED_VARIANT_TAGS[tag]
        assert "XSD" in UNVERIFIED_VARIANT_TAGS[tag]


def test_technical_section_ignores_out_of_scope_xsd_siblings_and_reports_unknown_tags() -> None:
    xml_bytes = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<CURRICULO-VITAE SISTEMA-ORIGEM-XML="SINTETICO-TESTE" '
        'NUMERO-IDENTIFICADOR="9200111122223333" DATA-ATUALIZACAO="13112026">'
        '<DADOS-GERAIS NOME-COMPLETO="Clara Sintética" '
        'NOME-EM-CITACOES-BIBLIOGRAFICAS="SINTETICA, C." '
        'NACIONALIDADE="B" PERMISSAO-DE-DIVULGACAO="SIM" />'
        "<PRODUCAO-TECNICA>"
        "<DEMAIS-TIPOS-DE-PRODUCAO-TECNICA>"
        '<APRESENTACAO-DE-TRABALHO SEQUENCIA-PRODUCAO="1">'
        '<DADOS-BASICOS-DA-APRESENTACAO-DE-TRABALHO NATUREZA="COMUNICACAO" TITULO="Comunicação" ANO="2025" />'
        "</APRESENTACAO-DE-TRABALHO>"
        '<OUTRA-PRODUCAO-TECNICA SEQUENCIA-PRODUCAO="2" />'
        '<TAG-TECNICA-DESCONHECIDA QUALQUER="1" />'
        "</DEMAIS-TIPOS-DE-PRODUCAO-TECNICA>"
        "</PRODUCAO-TECNICA>"
        "</CURRICULO-VITAE>"
    ).encode()

    result = parse_lattes_xml_with_report(xml_bytes)

    assert len(result.curriculum.records) == 1
    assert result.curriculum.records[0].category == LattesCategory.APRESENTACAO_TRABALHO
    assert result.unrecognized_elements == (
        "CURRICULO-VITAE/PRODUCAO-TECNICA/DEMAIS-TIPOS-DE-PRODUCAO-TECNICA/TAG-TECNICA-DESCONHECIDA",
    )
