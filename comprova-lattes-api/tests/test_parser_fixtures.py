import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from comprova_lattes.parser import parse_lattes_xml_with_report
from comprova_lattes.schemas import ActivityStatus, LattesCategory, LattesRecord

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "m1"
MANIFEST_PATH = FIXTURES_DIR / "manifest.json"
MANIFEST: dict[str, Any] = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
FIXTURE_ENTRIES: list[dict[str, Any]] = MANIFEST["fixtures"]


def _load_fixture_entry(entry: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    xml_path = FIXTURES_DIR / entry["file"]
    assert xml_path.is_file(), f"Missing fixture file declared in manifest: {xml_path}"
    return xml_path.read_bytes(), entry


def _assert_record_matches_manifest(
    record: LattesRecord,
    expected: dict[str, Any],
) -> None:
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
    if expected_hours is not None:
        assert isinstance(record.workload_hours, Decimal)

    expected_status = (
        ActivityStatus(expected["status"])
        if expected["status"] is not None
        else None
    )
    assert record.status == expected_status
    assert record.validation_code == expected["validation_code"]


def test_manifest_lists_exact_xml_fixture_set() -> None:
    assert MANIFEST["scope"] == "M1-Parser-Fixtures"
    declared_files = [entry["file"] for entry in FIXTURE_ENTRIES]
    disk_files = sorted(path.name for path in FIXTURES_DIR.glob("*.xml"))
    assert len(declared_files) == len(set(declared_files))
    assert sorted(declared_files) == disk_files


@pytest.mark.parametrize("entry", FIXTURE_ENTRIES, ids=[e["file"] for e in FIXTURE_ENTRIES])
def test_fixture_matches_manifest_header_counts_and_records(
    entry: dict[str, Any],
) -> None:
    xml_bytes, spec = _load_fixture_entry(entry)
    result = parse_lattes_xml_with_report(xml_bytes)
    curriculum = result.curriculum

    assert result.declared_encoding == spec["encoding"]
    assert result.diagnostics == ()

    expected_header = spec["expected_header"]
    assert curriculum.lattes_id == expected_header["lattes_id"]
    assert curriculum.updated_at == expected_header["updated_at"]
    assert curriculum.full_name == expected_header["full_name"]
    assert curriculum.citation_names == expected_header["citation_names"]
    assert curriculum.summary == expected_header["summary"]

    expected_counts = spec["expected_counts"]
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
        "total": len(curriculum.records),
    }
    assert actual_counts == expected_counts

    expected_records = spec["expected_records"]
    assert len(curriculum.records) == len(expected_records)
    for expected_record in expected_records:
        idx = expected_record["index"]
        _assert_record_matches_manifest(curriculum.records[idx], expected_record)


@pytest.mark.parametrize("entry", FIXTURE_ENTRIES, ids=[e["file"] for e in FIXTURE_ENTRIES])
def test_fixture_iso_8859_1_transcoded_with_explicit_declaration_matches_utf8(
    entry: dict[str, Any],
) -> None:
    xml_bytes, _ = _load_fixture_entry(entry)
    utf8_text = xml_bytes.decode("utf-8", errors="strict")
    utf8_decl = '<?xml version="1.0" encoding="UTF-8"?>'
    iso_decl = '<?xml version="1.0" encoding="ISO-8859-1"?>'
    assert utf8_text.startswith(utf8_decl)

    iso_text = utf8_text.replace(utf8_decl, iso_decl, 1)
    iso_bytes = iso_text.encode("iso-8859-1", errors="strict")

    utf8_result = parse_lattes_xml_with_report(xml_bytes)
    iso_result = parse_lattes_xml_with_report(iso_bytes)

    assert iso_result.declared_encoding == "ISO-8859-1"
    assert iso_result.diagnostics == utf8_result.diagnostics
    assert iso_result.curriculum == utf8_result.curriculum
