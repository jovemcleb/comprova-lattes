from decimal import Decimal

import pytest
from pydantic import ValidationError

from comprova_lattes.schemas import (
    ActivityStatus,
    LattesCategory,
    LattesCurriculum,
    LattesRecord,
    XmlProvenance,
)


def _make_provenance(
    section_tag: str = "FORMACAO-ACADEMICA-TITULACAO",
    record_tag: str = "GRADUACAO",
    parent_tag: str | None = "DADOS-GERAIS",
    sequence_attribute: str | None = "SEQUENCIA-FORMACAO",
    raw_attributes: dict[str, str] | None = None,
) -> XmlProvenance:
    return XmlProvenance(
        parent_tag=parent_tag,
        section_tag=section_tag,
        record_tag=record_tag,
        sequence_attribute=sequence_attribute,
        raw_attributes=raw_attributes or {},
    )


def test_lattes_category_enum_has_only_three_target_categories() -> None:
    expected = {
        "FORMACAO_ACADEMICA",
        "FORMACAO_COMPLEMENTAR",
        "PARTICIPACAO_EVENTO",
        "APRESENTACAO_TRABALHO",
        "ORGANIZACAO_EVENTO",
    }
    assert {member.value for member in LattesCategory} == expected

    with pytest.raises(ValidationError):
        LattesRecord(
            category="DESCONHECIDO",  # type: ignore[arg-type]
            provenance=_make_provenance(),
        )


def test_lattes_curriculum_defaults_to_none_without_invented_sentinels() -> None:
    curriculum = LattesCurriculum()

    assert curriculum.lattes_id is None
    assert curriculum.updated_at is None
    assert curriculum.full_name is None
    assert curriculum.citation_names == []
    assert curriculum.summary is None
    assert curriculum.records == []


def test_lattes_record_optional_fields_default_to_none_without_sentinels() -> None:
    record = LattesRecord(
        category=LattesCategory.FORMACAO_COMPLEMENTAR,
        provenance=_make_provenance(
            parent_tag="DADOS-COMPLEMENTARES",
            section_tag="FORMACAO-COMPLEMENTAR",
            record_tag="OUTROS-TIPOS-DE-FORMACAO-COMPLEMENTAR",
            sequence_attribute=None,
        ),
        institution="   ",
        title="",
        city=" ",
        location="",
    )

    assert record.record_id is None
    assert record.subtype is None
    assert record.sequence is None
    assert record.holder_name is None
    assert record.institution is None
    assert record.institution_acronym is None
    assert record.title is None
    assert record.event_name is None
    assert record.city is None
    assert record.location is None
    assert record.start_year is None
    assert record.end_year is None
    assert record.workload_hours is None
    assert record.status is None
    assert record.validation_code is None


def test_lattes_record_valid_academic_complementar_and_event_records() -> None:
    academic = LattesRecord(
        record_id="FA-GRADUACAO-1",
        category=LattesCategory.FORMACAO_ACADEMICA,
        subtype="GRADUACAO",
        sequence="1",
        provenance=_make_provenance(
            raw_attributes={
                "SEQUENCIA-FORMACAO": "1",
                "NOME-INSTITUICAO": "Universidade Federal do Norte",
                "NOME-CURSO": "Sistemas de Informação",
            }
        ),
        holder_name="Marina Oliveira Costa",
        institution="Universidade Federal do Norte",
        institution_acronym="UFN",
        title="Sistemas de Informação",
        start_year=2021,
        end_year=2025,
        status=ActivityStatus.CONCLUIDO,
        validation_code="123456",
    )

    event_without_institution = LattesRecord(
        category=LattesCategory.PARTICIPACAO_EVENTO,
        subtype="PARTICIPACAO_EM_CONGRESSO",
        sequence="7",
        provenance=_make_provenance(
            parent_tag="DADOS-COMPLEMENTARES",
            section_tag="PARTICIPACAO-EM-EVENTOS-CONGRESSOS",
            record_tag="PARTICIPACAO-EM-CONGRESSO",
            sequence_attribute="SEQUENCIA-PRODUCAO",
        ),
        holder_name="Marina Oliveira Costa",
        institution=None,
        title="Aplicação de Análise Determinística em Registros Acadêmicos",
        event_name="Congresso Regional de Computação",
        city="Belém",
        location="Centro de Convenções",
        start_year=2024,
        end_year=2024,
        workload_hours=Decimal(16),
        status=ActivityStatus.PARTICIPOU,
    )

    curriculum = LattesCurriculum(
        lattes_id="0000000000000001",
        updated_at="12112026",
        full_name="Marina Oliveira Costa",
        citation_names=["COSTA, M. O.", "OLIVEIRA, Marina"],
        summary="Pesquisadora fictícia em sistemas de informação.",
        records=[academic, event_without_institution],
    )

    assert len(curriculum.records) == 2
    assert curriculum.records[1].institution is None
    assert curriculum.records[1].city == "Belém"
    assert curriculum.records[1].location == "Centro de Convenções"


@pytest.mark.parametrize(
    ("section_tag", "record_tag"),
    [
        ("", "GRADUACAO"),
        ("   ", "GRADUACAO"),
        ("FORMACAO-ACADEMICA-TITULACAO", ""),
        ("FORMACAO-ACADEMICA-TITULACAO", "   "),
    ],
)
def test_xml_provenance_rejects_empty_section_or_record_tag(
    section_tag: str,
    record_tag: str,
) -> None:
    with pytest.raises(ValidationError):
        XmlProvenance(section_tag=section_tag, record_tag=record_tag)


def test_lattes_record_requires_category_and_provenance() -> None:
    with pytest.raises(ValidationError):
        LattesRecord(category=LattesCategory.FORMACAO_ACADEMICA)  # type: ignore[call-arg]

    with pytest.raises(ValidationError):
        LattesRecord(provenance=_make_provenance())  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("raw_hours", "expected"),
    [
        (Decimal("40.5"), Decimal("40.5")),
        (40.5, Decimal("40.5")),
        ("40.5", Decimal("40.5")),
        (40, Decimal(40)),
        ("12.75", Decimal("12.75")),
    ],
)
def test_workload_hours_preserves_fractional_values_without_truncation(
    raw_hours: Decimal | float | str,
    expected: Decimal,
) -> None:
    record = LattesRecord(
        category=LattesCategory.FORMACAO_COMPLEMENTAR,
        provenance=_make_provenance(
            parent_tag="DADOS-COMPLEMENTARES",
            section_tag="FORMACAO-COMPLEMENTAR",
            record_tag="FORMACAO-COMPLEMENTAR-DE-EXTENSAO-UNIVERSITARIA",
        ),
        workload_hours=raw_hours,  # type: ignore[arg-type]
    )

    assert record.workload_hours == expected
    assert isinstance(record.workload_hours, Decimal)


def test_numeric_fields_do_not_enforce_arbitrary_domain_limits() -> None:
    record = LattesRecord(
        category=LattesCategory.FORMACAO_ACADEMICA,
        provenance=_make_provenance(),
        start_year="1889",  # type: ignore[arg-type]
        end_year=2150,
        workload_hours=Decimal("25000.25"),
    )

    assert record.start_year == 1889
    assert record.end_year == 2150
    assert record.workload_hours == Decimal("25000.25")


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("start_year", 2024.5),
        ("start_year", 2024.0),
        ("start_year", "2024.5"),
        ("start_year", Decimal("2024.5")),
        ("start_year", "abc"),
        ("start_year", ""),
        ("start_year", True),
        ("end_year", 2025.9),
        ("end_year", "2025.0"),
        ("end_year", False),
        ("workload_hours", True),
        ("workload_hours", False),
        ("workload_hours", "40h"),
        ("workload_hours", "40,5"),
        ("workload_hours", ""),
        ("workload_hours", float("nan")),
        ("workload_hours", float("inf")),
        ("workload_hours", Decimal("NaN")),
        ("workload_hours", Decimal("Infinity")),
    ],
)
def test_numeric_fields_reject_invalid_values_and_silent_truncation(
    field_name: str,
    invalid_value: object,
) -> None:
    payload: dict[str, object] = {
        "category": LattesCategory.FORMACAO_ACADEMICA,
        "provenance": _make_provenance(),
        field_name: invalid_value,
    }

    with pytest.raises(ValidationError):
        LattesRecord.model_validate(payload)


def test_schemas_reject_extra_fields_and_invalid_status() -> None:
    with pytest.raises(ValidationError):
        LattesCurriculum.model_validate({"nomeCompleto": "Marina"})

    with pytest.raises(ValidationError):
        LattesRecord.model_validate(
            {
                "category": "FORMACAO_ACADEMICA",
                "provenance": _make_provenance(),
                "cargaHoraria": 40,
            }
        )

    with pytest.raises(ValidationError):
        LattesRecord.model_validate(
            {
                "category": "FORMACAO_ACADEMICA",
                "provenance": _make_provenance(),
                "status": "INVALIDO",
            }
        )


def test_curriculum_json_roundtrip_preserves_none_and_decimal() -> None:
    original = LattesCurriculum(
        lattes_id=None,
        full_name="Carlos Eduardo Mendes",
        records=[
            LattesRecord(
                category=LattesCategory.FORMACAO_COMPLEMENTAR,
                provenance=_make_provenance(
                    parent_tag="DADOS-COMPLEMENTARES",
                    section_tag="FORMACAO-COMPLEMENTAR",
                    record_tag="FORMACAO-COMPLEMENTAR-CURSO-DE-CURTA-DURACAO",
                ),
                workload_hours=Decimal("12.75"),
                institution=None,
            )
        ],
    )

    dumped = original.model_dump(mode="json")
    restored = LattesCurriculum.model_validate(dumped)

    assert restored == original
    assert restored.lattes_id is None
    assert restored.records[0].workload_hours == Decimal("12.75")
    assert restored.records[0].institution is None
