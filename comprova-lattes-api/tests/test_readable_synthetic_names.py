"""Contratos de legibilidade, unicidade e isolamento sem sufixos hex em valores humanos."""

import re

import pytest

from comprova_lattes.experiments.annotation_package import build_package, validate_package
from comprova_lattes.experiments.synthetic import (
    SYNTHETIC_ACRONYMS,
    TEMPLATE_PROVENANCE,
    document_text,
    generate,
    institution_acronym,
    synthetic_acronyms,
)
from comprova_lattes.matcher.text import normalize_text
from comprova_lattes.schemas.lattes import LattesCategory

LONG_HEX_RE = re.compile(r"\b[0-9a-fA-F]{6,}\b")
ACRONYM_RE = re.compile(r"^[A-Z]{2,5}$")
TECHNICAL_CASE_ID_RE = re.compile(r"^[0-9a-f]{20}$")
TECHNICAL_FAMILY_ID_RE = re.compile(r"^[0-9a-f]{12}$")

LEGACY_ARTIFICIAL_MARKERS = (
    "pessoa ficticia",
    "instituto ficticio",
    "curso sintetico",
    "trabalho sintetico",
    "evento ficticio",
    "outra",
    "divergente",
    "mutado",
)


@pytest.fixture(scope="module")
def approved_corpus():
    return generate(seed=42, pilot_families=10, final_families=20)


def test_human_values_have_no_hex_suffixes_and_keep_short_readable_lengths(approved_corpus):
    assert len(approved_corpus.cases) == 150
    for case in approved_corpus.cases:
        assert TECHNICAL_CASE_ID_RE.fullmatch(case.case_id)
        assert TECHNICAL_FAMILY_ID_RE.fullmatch(case.family_id)
        assert case.issuer_id == case.family_id
        assert case.template_id == f"t-{case.family_id}"

        record = case.curriculum.records[0]
        human_values = [
            case.curriculum.full_name,
            record.holder_name,
            record.institution,
            record.title,
            record.event_name,
        ]
        if case.gold is not None:
            human_values.extend(
                [
                    case.gold.holder_name,
                    case.gold.activity_title,
                    case.gold.event_name,
                    case.gold.issuer_institution,
                    case.gold.issuer_acronym,
                    case.gold.issuer_name_acronym_evidence,
                ]
            )
            text = document_text(
                case.gold, int(case.family_id, 16), category=record.category
            )
            assert not LONG_HEX_RE.search(text)
            assert case.family_id.lower() not in text.lower()
            assert case.case_id.lower() not in text.lower()

        for value in human_values:
            if value is None:
                continue
            assert not LONG_HEX_RE.search(value), value
            assert case.family_id.lower() not in value.lower()
            lowered = value.lower()
            for marker in LEGACY_ARTIFICIAL_MARKERS:
                assert marker not in lowered, (marker, value)

        assert 2 <= len(case.curriculum.full_name.split()) <= 4
        assert 2 <= len(record.institution.split()) <= 4
        assert 2 <= len(record.title.split()) <= 6
        if record.event_name is not None:
            assert 2 <= len(record.event_name.split()) <= 6

        if case.gold is not None:
            if case.gold.holder_name is not None:
                assert 2 <= len(case.gold.holder_name.split()) <= 4
            assert 2 <= len(case.gold.issuer_institution.split()) <= 4
            assert 2 <= len(case.gold.activity_title.split()) <= 6
            if case.gold.event_name is not None:
                assert 2 <= len(case.gold.event_name.split()) <= 6
            if case.gold.issuer_acronym is not None:
                assert ACRONYM_RE.fullmatch(case.gold.issuer_acronym)
                assert case.gold.issuer_acronym == institution_acronym(
                    case.gold.issuer_institution
                )
                assert (
                    case.gold.issuer_name_acronym_evidence
                    == f"{case.gold.issuer_institution} - {case.gold.issuer_acronym}"
                )


def test_pilot_final_disjoint_issuers_acronyms_and_invariance(approved_corpus):
    pilot = approved_corpus.select("pilot")
    final = approved_corpus.select("final")
    assert len(pilot) == 50 and len(final) == 100
    assert pilot == generate(seed=42, pilot_families=10, final_families=3).select("pilot")

    pilot_acronyms = synthetic_acronyms(pilot)
    final_acronyms = synthetic_acronyms(final)
    assert len(pilot_acronyms) == 10
    assert len(final_acronyms) == 20
    assert set(pilot_acronyms).isdisjoint(final_acronyms)
    assert set(pilot_acronyms.values()).isdisjoint(final_acronyms.values())
    assert set(SYNTHETIC_ACRONYMS) == {"I", "C", "F", "E"}

    pilot_institutions = {
        normalize_text(c.curriculum.records[0].institution) for c in pilot
    } | {
        normalize_text(c.gold.issuer_institution)
        for c in pilot
        if c.gold is not None
    }
    final_institutions = {
        normalize_text(c.curriculum.records[0].institution) for c in final
    } | {
        normalize_text(c.gold.issuer_institution)
        for c in final
        if c.gold is not None
    }
    assert pilot_institutions.isdisjoint(final_institutions)

    pilot_doc_acronyms = {
        c.gold.issuer_acronym for c in pilot if c.gold is not None and c.gold.issuer_acronym
    }
    final_doc_acronyms = {
        c.gold.issuer_acronym for c in final if c.gold is not None and c.gold.issuer_acronym
    }
    assert pilot_doc_acronyms.isdisjoint(final_doc_acronyms)

    titles = {normalize_text(c.curriculum.records[0].title) for c in approved_corpus.cases}
    events = {
        normalize_text(c.curriculum.records[0].event_name)
        for c in approved_corpus.cases
        if c.curriculum.records[0].event_name is not None
    }
    assert len(titles) == 30
    assert len(events) == 12


def test_mutated_names_differ_from_xml_without_leaking_cues(approved_corpus):
    for case in approved_corpus.cases:
        if case.operator != "factual_mutation":
            continue
        record = case.curriculum.records[0]
        assert case.gold is not None
        if record.category == LattesCategory.APRESENTACAO_TRABALHO:
            assert case.gold.holder_name is not None
            assert normalize_text(case.gold.holder_name) != normalize_text(
                case.curriculum.full_name
            )
            assert case.gold.holder_name.split()[0] != case.curriculum.full_name.split()[0] or (
                case.gold.holder_name.split()[1] != case.curriculum.full_name.split()[1]
            )
        elif record.category == LattesCategory.ORGANIZACAO_EVENTO:
            assert normalize_text(case.gold.issuer_institution) != normalize_text(
                record.institution
            )
            if case.gold.issuer_acronym is not None:
                assert case.gold.issuer_acronym != institution_acronym(record.institution)


def test_template_version_bumped_and_annotation_package_builds(approved_corpus):
    assert TEMPLATE_PROVENANCE["template_version"] == "ptbr-contract-draft-v2"
    assert TEMPLATE_PROVENANCE["status"] == "draft_pending_human_validation"
    assert TEMPLATE_PROVENANCE["human_approval_required_before_freeze"] is True
    assert TEMPLATE_PROVENANCE["methodological_independence_claimed"] is False

    built = build_package(approved_corpus)
    validated = validate_package(built.package)
    assert len(validated.cases) == 5
    for public_case in validated.cases:
        assert public_case.record.holder_name is not None
        assert not LONG_HEX_RE.search(public_case.record.holder_name)
        if public_case.record.institution is not None:
            assert not LONG_HEX_RE.search(public_case.record.institution)
        if public_case.record.title is not None:
            assert not LONG_HEX_RE.search(public_case.record.title)
        if public_case.record.event_name is not None:
            assert not LONG_HEX_RE.search(public_case.record.event_name)
