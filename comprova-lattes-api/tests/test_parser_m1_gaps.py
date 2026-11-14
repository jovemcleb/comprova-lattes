"""Regress?es sint?ticas para as lacunas M1 da auditoria E1."""

import pytest

from comprova_lattes.parser import LattesNumericValueError, parse_lattes_xml
from comprova_lattes.schemas import ActivityStatus


def parse(body: str):
    return parse_lattes_xml(f"<CURRICULO-VITAE>{body}</CURRICULO-VITAE>".encode())


@pytest.mark.parametrize("parent", ["DADOS-COMPLEMENTARES", "DADOS-GERAIS"])
def test_repeated_complementary_containers(parent):
    section = '<FORMACAO-COMPLEMENTAR><MBA CARGA-HORARIA="1.5" /></FORMACAO-COMPLEMENTAR>'
    records = parse(f"<{parent}>{section}{section}</{parent}>").records
    assert len(records) == 2
    assert all(r.provenance.parent_tag == parent for r in records)
    assert records[0].record_id != records[1].record_id


@pytest.mark.parametrize("tag,attribute", [
    ("ESPECIALIZACAO", "TITULO-DA-MONOGRAFIA"),
    ("APERFEICOAMENTO", "TITULO-DA-MONOGRAFIA"),
    ("POS-DOUTORADO", "TITULO-DO-TRABALHO"),
    ("LIVRE-DOCENCIA", "TITULO-DO-TRABALHO"),
    ("RESIDENCIA-MEDICA", "TITULO-DA-RESIDENCIA-MEDICA"),
    ("MBA", "TITULO-DA-MONOGRAFIA"),
])
@pytest.mark.parametrize("course", ["", 'NOME-CURSO="Curso"'])
def test_alternative_titles_and_course_precedence(tag, attribute, course):
    section = "FORMACAO-COMPLEMENTAR" if tag == "MBA" else "FORMACAO-ACADEMICA-TITULACAO"
    record = parse(
        f'<DADOS-GERAIS><{section}><{tag} {course} {attribute}="Titulo" />'
        f'</{section}></DADOS-GERAIS>'
    ).records[0]
    assert record.title == ("Curso" if course else "Titulo")
    assert record.provenance.raw_attributes[attribute] == "Titulo"


@pytest.mark.parametrize("child,expected", [
    ("", "Direto"),
    ('<RESUMO-CV TEXTO-RESUMO-CV-RH="Filho" />', "Filho"),
    ('<RESUMO-CV TEXTO-RESUMO-CV-RH="  " />', "Direto"),
])
def test_direct_summary_fallback(child, expected):
    assert parse(
        f'<DADOS-GERAIS TEXTO-RESUMO-CV-RH="Direto">{child}</DADOS-GERAIS>'
    ).summary == expected


@pytest.mark.parametrize("attributes,expected", [
    ('STATUS-DO-ESTAGIO="CONCLUIDO"', ActivityStatus.CONCLUIDO),
    ('STATUS-DO-CURSO="EM_ANDAMENTO" STATUS-DO-ESTAGIO="CONCLUIDO"',
     ActivityStatus.EM_ANDAMENTO),
    ('STATUS-DO-CURSO=" " STATUS-DO-ESTAGIO="CONCLUIDO"', ActivityStatus.CONCLUIDO),
])
def test_postdoctoral_stage_status(attributes, expected):
    record = parse(
        '<DADOS-GERAIS><FORMACAO-ACADEMICA-TITULACAO>'
        f'<POS-DOUTORADO {attributes} />'
        '</FORMACAO-ACADEMICA-TITULACAO></DADOS-GERAIS>'
    ).records[0]
    assert record.status == expected


@pytest.mark.parametrize("completion,expected", [("", 2024), ('ANO-DE-CONCLUSAO="2023"', 2023)])
def test_mba_title_year_fallback(completion, expected):
    record = parse(
        '<DADOS-COMPLEMENTARES><FORMACAO-COMPLEMENTAR>'
        f'<MBA {completion} ANO-DE-OBTENCAO-DO-TITULO="2024" />'
        '</FORMACAO-COMPLEMENTAR></DADOS-COMPLEMENTARES>'
    ).records[0]
    assert record.end_year == expected


def test_mba_title_year_remains_strict():
    with pytest.raises(LattesNumericValueError):
        parse('<DADOS-COMPLEMENTARES><FORMACAO-COMPLEMENTAR>'
              '<MBA ANO-DE-OBTENCAO-DO-TITULO="2024.5" />'
              '</FORMACAO-COMPLEMENTAR></DADOS-COMPLEMENTARES>')


@pytest.mark.parametrize("nature", ["CURADORIA", "MONTAGEM", "MUSEOLOGIA", "ORGANIZACAO"])
def test_organization_preserves_nature_separately_from_structural_role(nature):
    record = parse(
        '<PRODUCAO-TECNICA><DEMAIS-TIPOS-DE-PRODUCAO-TECNICA><ORGANIZACAO-DE-EVENTO>'
        f'<DADOS-BASICOS-DA-ORGANIZACAO-DE-EVENTO NATUREZA="{nature}" />'
        '</ORGANIZACAO-DE-EVENTO></DEMAIS-TIPOS-DE-PRODUCAO-TECNICA></PRODUCAO-TECNICA>'
    ).records[0]
    assert record.nature_raw == nature
    assert record.participation_role == "ORGANIZADOR"
    assert record.provenance.raw_attributes[
        "DADOS-BASICOS-DA-ORGANIZACAO-DE-EVENTO/@NATUREZA"
    ] == nature


def test_ids_are_deterministic_unique_and_independent_of_attribute_order():
    body = ('<DADOS-GERAIS><FORMACAO-ACADEMICA-TITULACAO>'
            '<GRADUACAO NOME-CURSO="A" SEQUENCIA-FORMACAO="1" />'
            '<GRADUACAO NOME-CURSO="A" SEQUENCIA-FORMACAO="1" />'
            '<GRADUACAO NOME-CURSO="B" />'
            '</FORMACAO-ACADEMICA-TITULACAO></DADOS-GERAIS>')
    first = parse(body)
    assert first == parse(body)
    assert all(r.record_id for r in first.records)
    assert len({r.record_id for r in first.records}) == 3
    reordered = body.replace('NOME-CURSO="A" SEQUENCIA-FORMACAO="1"',
                             'SEQUENCIA-FORMACAO="1" NOME-CURSO="A"')
    assert first == parse(reordered)
    assert first.records[0].record_id != parse(body.replace('NOME-CURSO="A"',
                                                          'NOME-CURSO="C"')).records[0].record_id
