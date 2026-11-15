"""Testes focais dos templates de certificados sintéticos em português."""

from collections import Counter
from decimal import Decimal

import pytest

from comprova_lattes.experiments.render import SUPPORTED_CHARS, pdf, png, raster
from comprova_lattes.experiments.synthetic import (
    CATEGORY_ORDER,
    CATEGORY_TEMPLATES,
    DEFAULT_TEMPLATE,
    DOCUMENT_FIELD_LABELS,
    FIELD_LABELS,
    TEMPLATE_PROVENANCE,
    document_text,
    generate,
)
from comprova_lattes.matcher.models import ExtractedDocumentRecord
from comprova_lattes.schemas.lattes import LattesCategory

EXPECTED_LABELS = {
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

FORBIDDEN_SCHEMA_TOKENS = frozenset(
    {
        *EXPECTED_LABELS,
        "document_id",
        "extraction_status",
        "raw_metadata",
        "confianca_extracao",
        "categoria_sugerida",
    }
)

FORBIDDEN_LEAK_TOKENS = frozenset(
    {
        "identity",
        "legitimate",
        "factual_mutation",
        "omission",
        "no_document",
        "VALIDADO",
        "DIVERGENTE",
        "INCONCLUSIVO",
        "pilot",
        "final",
        "OUTRA",
        "ERRO",
        "MUTADO",
    }
)


@pytest.fixture(scope="module")
def corpus_50():
    return generate(seed=31, pilot_families=5, final_families=5)


def test_field_labels_contract_and_no_english_schema_or_status_leaks(corpus_50):
    assert FIELD_LABELS == EXPECTED_LABELS
    assert DOCUMENT_FIELD_LABELS == EXPECTED_LABELS

    for case in corpus_50.cases:
        if case.gold is None:
            assert case.document is None
            continue
        category = case.curriculum.records[0].category
        layout = int(case.family_id, 16)
        for text in (
            document_text(case.gold),
            document_text(case.gold, layout),
            document_text(case.gold, layout, category=category),
        ):
            assert set(text) <= SUPPORTED_CHARS
            lower_text = text.lower()
            for schema_key in FORBIDDEN_SCHEMA_TOKENS:
                assert schema_key.lower() not in lower_text
            for leak_token in FORBIDDEN_LEAK_TOKENS:
                assert leak_token.lower() not in lower_text


def test_five_categories_headers_neutral_phrases_and_call_compatibility(corpus_50):
    assert len(CATEGORY_ORDER) == 5
    assert set(CATEGORY_ORDER) == set(LattesCategory)
    assert set(CATEGORY_TEMPLATES) == set(LattesCategory)
    assert len(set(CATEGORY_TEMPLATES.values())) == 5
    assert ":" not in DEFAULT_TEMPLATE[0] and ":" not in DEFAULT_TEMPLATE[1]

    sample = next(c.gold for c in corpus_50.cases if c.gold is not None)
    default_lines = document_text(sample).splitlines()
    assert default_lines[:2] == list(DEFAULT_TEMPLATE)
    assert document_text(sample, 0) == document_text(sample)

    for idx, cat in enumerate(CATEGORY_ORDER):
        header, phrase = CATEGORY_TEMPLATES[cat]
        assert ":" not in header
        assert ":" not in phrase
        by_enum = document_text(sample, layout=2, category=cat)
        by_str = document_text(sample, layout=2, category=cat.value)
        by_index = document_text(sample, layout=2, category=idx)
        assert by_enum == by_str == by_index
        lines = by_enum.splitlines()
        assert lines[0] == header
        assert lines[1] == phrase
        assert all(":" in line for line in lines[2:])

    for invalid_cat in ("CATEGORIA_INVALIDA", -1, 5, True, False, 1.5):
        with pytest.raises(ValueError, match="Categoria"):
            document_text(sample, layout=0, category=invalid_cat)

    for invalid_layout in (-1, True, False, "0"):
        with pytest.raises(ValueError, match="Layout"):
            document_text(sample, layout=invalid_layout)


def test_literal_values_omissions_decimal_workload_and_ad014_evidence(corpus_50):
    decimal_record = ExtractedDocumentRecord(
        document_id="doc-decimal",
        holder_name="PESSOA FICTICIA DEC",
        activity_title="CURSO SINTETICO DEC",
        issuer_institution="INSTITUTO FICTICIO DEC",
        workload_hours=Decimal("12.5"),
    )
    decimal_lines = document_text(
        decimal_record, layout=0, category=LattesCategory.FORMACAO_COMPLEMENTAR
    ).splitlines()
    assert "Carga horária: 12.5" in decimal_lines
    assert not any(line.startswith("Evento:") for line in decimal_lines)
    assert not any("None" in line for line in decimal_lines)

    for case in corpus_50.cases:
        if case.gold is None:
            continue
        category = case.curriculum.records[0].category
        layout = int(case.family_id, 16)
        lines = document_text(case.gold, layout, category=category).splitlines()
        header, phrase = CATEGORY_TEMPLATES[category]
        assert lines[0] == header
        assert lines[1] == phrase

        field_lines = lines[2:]
        parsed_pairs = [line.split(": ", 1) for line in field_lines]
        assert all(len(pair) == 2 for pair in parsed_pairs)
        observed_map = {label: value for label, value in parsed_pairs}
        assert len(observed_map) == len(field_lines)

        dumped = case.gold.model_dump(include=set(FIELD_LABELS))
        for field_name, label in FIELD_LABELS.items():
            val = dumped[field_name]
            if val is None:
                assert label not in observed_map
            else:
                assert observed_map[label] == str(val)

        if case.gold.issuer_name_acronym_evidence is not None:
            assert case.gold.issuer_acronym is not None
            expected_snippet = f"{case.gold.issuer_institution} - {case.gold.issuer_acronym}"
            assert observed_map["Sigla da instituição"] == case.gold.issuer_acronym
            assert observed_map["Identificação da instituição"] == expected_snippet
        else:
            assert case.gold.issuer_acronym is None
            assert "Sigla da instituição" not in observed_map
            assert "Identificação da instituição" not in observed_map
        if case.operator == "omission":
            assert "Titular" not in observed_map


def test_template_depends_only_on_family_layout_and_category_and_matches_bytes(corpus_50):
    for family_id in {c.family_id for c in corpus_50.cases}:
        members = [c for c in corpus_50.cases if c.family_id == family_id and c.gold is not None]
        category = members[0].curriculum.records[0].category
        layout = int(family_id, 16)
        headers_and_phrases = {
            tuple(document_text(c.gold, layout, category=category).splitlines()[:2])
            for c in members
        }
        assert headers_and_phrases == {CATEGORY_TEMPLATES[category]}

        by_op = {c.operator: c for c in members}
        for test_layout in (0, 1, layout):
            id_labels = [
                line.split(": ", 1)[0]
                for line in document_text(
                    by_op["identity"].gold, test_layout, category=category
                ).splitlines()[2:]
            ]
            mut_labels = [
                line.split(": ", 1)[0]
                for line in document_text(
                    by_op["factual_mutation"].gold, test_layout, category=category
                ).splitlines()[2:]
            ]
            om_labels = [
                line.split(": ", 1)[0]
                for line in document_text(
                    by_op["omission"].gold, test_layout, category=category
                ).splitlines()[2:]
            ]
            leg_labels = [
                line.split(": ", 1)[0]
                for line in document_text(
                    by_op["legitimate"].gold, test_layout, category=category
                ).splitlines()[2:]
            ]
            assert mut_labels == id_labels
            assert om_labels == [lbl for lbl in id_labels if lbl != "Titular"]
            assert [lbl for lbl in leg_labels if lbl in set(id_labels)] == id_labels

        for c in members:
            text = document_text(c.gold, layout, category=category)
            img = raster(text, seed=layout, degradation=c.degradation, layout=layout)
            expected_bytes = (png if c.mime_type == "image/png" else pdf)(*img)
            assert c.document == expected_bytes


def test_workbench_150_distribution_isolation_and_provenance():
    assert TEMPLATE_PROVENANCE["status"] == "draft_pending_human_validation"
    assert TEMPLATE_PROVENANCE["composition_origin"] == "agent_assisted_draft"
    assert TEMPLATE_PROVENANCE["human_approval_required_before_freeze"] is True
    assert TEMPLATE_PROVENANCE["methodological_independence_claimed"] is False
    assert "Gemini" in str(TEMPLATE_PROVENANCE["same_model_family_preparation_risk"])

    corpus = generate(seed=42, pilot_families=10, final_families=20)
    assert len(corpus.cases) == 150
    pilot = corpus.select("pilot")
    final = corpus.select("final")
    assert len(pilot) == 50 and len(final) == 100
    assert pilot == generate(seed=42, pilot_families=10, final_families=3).select("pilot")

    for part_cases, expected_families in ((pilot, 10), (final, 20)):
        cat_counts = Counter(c.curriculum.records[0].category for c in part_cases)
        op_counts = Counter(c.operator for c in part_cases)
        assert set(cat_counts) == set(LattesCategory)
        assert set(cat_counts.values()) == {expected_families}
        assert set(op_counts.values()) == {expected_families}
        ad014_ops = {
            c.operator
            for c in part_cases
            if c.gold is not None and c.gold.issuer_name_acronym_evidence is not None
        }
        assert ad014_ops == {"identity", "legitimate", "factual_mutation", "omission"}
