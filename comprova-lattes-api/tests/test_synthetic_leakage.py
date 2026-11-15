"""Testes de neutralidade textual, diferenças factuais e ausência de vazamento em valores."""

import re
from collections import Counter

import pytest

from comprova_lattes.experiments.synthetic import (
    alternative_identity,
    document_text,
    generate,
)
from comprova_lattes.matcher.models import MatchStatus
from comprova_lattes.matcher.text import normalize_text
from comprova_lattes.schemas.lattes import LattesCategory

FORBIDDEN_FULL_TEXT_TOKENS = (
    "validado",
    "divergente",
    "inconclusivo",
    "identity",
    "legitimate",
    "factual_mutation",
    "omission",
    "no_document",
    "pilot",
    "final",
    "outra",
    "erro",
    "mutado",
)

HOLDER_PATTERN = re.compile(r"^PESSOA FICTICIA [0-9A-F]{12}$")
INSTITUTION_PATTERN = re.compile(r"^INSTITUTO FICTICIO [0-9A-F]{12}$")


@pytest.fixture(scope="module")
def full_corpus():
    return generate(seed=42, pilot_families=10, final_families=20)


def test_full_document_text_and_values_have_no_class_operator_or_cue_leaks(full_corpus):
    assert len(full_corpus.cases) == 150
    for case in full_corpus.cases:
        if case.gold is None:
            continue
        category = case.curriculum.records[0].category
        layout = int(case.family_id, 16)
        text = document_text(case.gold, layout, category=category)
        lower_text = text.lower()
        for token in FORBIDDEN_FULL_TEXT_TOKENS:
            assert token not in lower_text, (case.case_id, case.operator, token, text)

        for field_value in (
            case.gold.holder_name,
            case.gold.activity_title,
            case.gold.event_name,
            case.gold.issuer_institution,
            case.gold.issuer_acronym,
            case.gold.issuer_name_acronym_evidence,
        ):
            if field_value is not None:
                lower_val = field_value.lower()
                for token in FORBIDDEN_FULL_TEXT_TOKENS:
                    assert token not in lower_val


def test_factual_mutations_preserve_single_field_difference_and_expected_class(full_corpus):
    by_family = {}
    for case in full_corpus.cases:
        by_family.setdefault(case.family_id, {})[case.operator] = case

    assert len(by_family) == 30
    for family_id, ops in by_family.items():
        identity_case = ops["identity"]
        mutated_case = ops["factual_mutation"]
        record = mutated_case.curriculum.records[0]

        assert mutated_case.expected == MatchStatus.DIVERGENTE
        assert mutated_case.gold is not None
        assert identity_case.gold is not None

        id_dump = identity_case.gold.model_dump(exclude={"document_id"})
        mut_dump = mutated_case.gold.model_dump(exclude={"document_id"})
        changed_fields = {k for k in id_dump if id_dump[k] != mut_dump[k]}

        if record.category in (
            LattesCategory.FORMACAO_ACADEMICA,
            LattesCategory.FORMACAO_COMPLEMENTAR,
        ):
            assert changed_fields == {"workload_hours"}
            assert mutated_case.gold.workload_hours != record.workload_hours
        elif record.category == LattesCategory.PARTICIPACAO_EVENTO:
            assert changed_fields == {"start_year", "end_year", "activity_year"}
            assert mutated_case.gold.activity_year != record.end_year
        elif record.category == LattesCategory.APRESENTACAO_TRABALHO:
            assert changed_fields == {"holder_name"}
            assert mutated_case.gold.holder_name != mutated_case.curriculum.full_name
        elif record.category == LattesCategory.ORGANIZACAO_EVENTO:
            assert mutated_case.gold.issuer_institution != record.institution
            if mutated_case.gold.issuer_name_acronym_evidence is not None:
                assert changed_fields == {
                    "issuer_institution",
                    "issuer_acronym",
                    "issuer_name_acronym_evidence",
                }
                assert mutated_case.gold.issuer_acronym is not None
                assert mutated_case.gold.issuer_acronym != identity_case.gold.issuer_acronym
                assert record.institution not in mutated_case.gold.issuer_name_acronym_evidence
                assert (
                    mutated_case.gold.issuer_institution
                    in mutated_case.gold.issuer_name_acronym_evidence
                )
                assert (
                    mutated_case.gold.issuer_acronym
                    in mutated_case.gold.issuer_name_acronym_evidence
                )
            else:
                assert changed_fields == {"issuer_institution"}
                assert mutated_case.gold.issuer_acronym is None
        else:
            pytest.fail(f"Categoria inesperada: {record.category} ({family_id})")


def test_ad014_and_legitimate_characteristics_are_not_exclusive_cues(full_corpus):
    assert len(full_corpus.cases) == 150
    pilot = full_corpus.select("pilot")
    final = full_corpus.select("final")
    assert len(pilot) == 50 and len(final) == 100
    assert pilot == generate(seed=42, pilot_families=10, final_families=3).select("pilot")

    doc_operators = ("identity", "legitimate", "factual_mutation", "omission")
    for part_cases, n_families in ((pilot, 10), (final, 20)):
        cat_counts = Counter(c.curriculum.records[0].category for c in part_cases)
        op_counts = Counter(c.operator for c in part_cases)
        assert set(cat_counts.values()) == {n_families}
        assert set(op_counts.values()) == {n_families}

        ad014_by_op = Counter()
        ad014_by_cat_op = Counter()
        for case in part_cases:
            if case.operator == "no_document":
                assert case.gold is None and case.document is None
                continue
            assert case.gold is not None
            has_acronym = case.gold.issuer_acronym is not None
            has_evidence = case.gold.issuer_name_acronym_evidence is not None
            assert has_acronym == has_evidence
            if has_evidence:
                ad014_by_op[case.operator] += 1
                ad014_by_cat_op[(case.curriculum.records[0].category, case.operator)] += 1
                assert case.gold.issuer_institution in case.gold.issuer_name_acronym_evidence
                assert case.gold.issuer_acronym in case.gold.issuer_name_acronym_evidence

        expected_per_op = n_families // 2
        assert set(ad014_by_op) == set(doc_operators)
        assert all(ad014_by_op[op] == expected_per_op for op in doc_operators)
        expected_per_cat_op = expected_per_op // len(LattesCategory)
        for cat in LattesCategory:
            for op in doc_operators:
                assert ad014_by_cat_op[(cat, op)] == expected_per_cat_op

    by_family = {}
    for case in full_corpus.cases:
        by_family.setdefault(case.family_id, {})[case.operator] = case

    variation_profiles = set()
    for ops in by_family.values():
        ad014_flags = {
            ops[op].gold.issuer_name_acronym_evidence is not None for op in doc_operators
        }
        assert len(ad014_flags) == 1

        leg = ops["legitimate"]
        record = leg.curriculum.records[0]
        assert leg.gold is not None
        assert leg.gold.activity_title != "X" + record.title[1:]
        assert normalize_text(leg.gold.holder_name) == normalize_text(leg.curriculum.full_name)
        assert normalize_text(leg.gold.activity_title) == normalize_text(record.title)
        assert normalize_text(leg.gold.issuer_institution) == normalize_text(record.institution)
        if record.event_name is not None:
            assert normalize_text(leg.gold.event_name) == normalize_text(record.event_name)

        differs_literally = any(
            [
                leg.gold.holder_name != leg.curriculum.full_name,
                leg.gold.activity_title != record.title,
                leg.gold.issuer_institution != record.institution,
                leg.gold.event_name != record.event_name,
            ]
        )
        assert differs_literally
        has_double_space = "  " in leg.gold.activity_title
        has_case_diff = leg.gold.activity_title != leg.gold.activity_title.upper()
        has_punct_diff = any(ch in leg.gold.activity_title for ch in (",", "-", ":"))
        variation_profiles.add((has_double_space, has_case_diff, has_punct_diff))

    assert len(variation_profiles) >= 3


def test_mutated_identities_share_neutral_shape_and_determinism(full_corpus):
    by_family = {}
    for case in full_corpus.cases:
        by_family.setdefault(case.family_id, {})[case.operator] = case

    pilot_only = generate(seed=42, pilot_families=10, final_families=3).select("pilot")
    assert full_corpus.select("pilot") == pilot_only
    other_seed_corpus = generate(seed=99, pilot_families=10, final_families=20)

    seen_holder_suffixes = set()
    seen_institution_suffixes = set()

    for family_id, ops in by_family.items():
        id_case = ops["identity"]
        mut_case = ops["factual_mutation"]
        category = mut_case.curriculum.records[0].category
        layout = int(family_id, 16)

        id_lines = document_text(id_case.gold, layout, category=category).splitlines()
        mut_lines = document_text(mut_case.gold, layout, category=category).splitlines()
        assert id_lines[:2] == mut_lines[:2]
        assert [line.split(": ", 1)[0] for line in id_lines[2:]] == [
            line.split(": ", 1)[0] for line in mut_lines[2:]
        ]

        if category == LattesCategory.APRESENTACAO_TRABALHO:
            normal_name = id_case.gold.holder_name
            mutated_name = mut_case.gold.holder_name
            assert HOLDER_PATTERN.match(normal_name)
            assert HOLDER_PATTERN.match(mutated_name)
            assert len(mutated_name) == len(normal_name)
            assert mutated_name.split()[:-1] == normal_name.split()[:-1]
            suffix = mutated_name.rsplit(" ", 1)[1]
            assert suffix != family_id.upper()
            assert suffix == alternative_identity(full_corpus.seed, family_id, "holder_name")
            assert suffix != alternative_identity(full_corpus.seed, family_id, "issuer_institution")
            assert suffix != alternative_identity(other_seed_corpus.seed, family_id, "holder_name")
            seen_holder_suffixes.add(suffix)

        elif category == LattesCategory.ORGANIZACAO_EVENTO:
            normal_inst = id_case.gold.issuer_institution
            mutated_inst = mut_case.gold.issuer_institution
            assert INSTITUTION_PATTERN.match(normal_inst)
            assert INSTITUTION_PATTERN.match(mutated_inst)
            assert len(mutated_inst) == len(normal_inst)
            assert mutated_inst.split()[:-1] == normal_inst.split()[:-1]
            suffix = mutated_inst.rsplit(" ", 1)[1]
            assert suffix != family_id.upper()
            assert suffix == alternative_identity(
                full_corpus.seed, family_id, "issuer_institution"
            )
            assert suffix != alternative_identity(full_corpus.seed, family_id, "holder_name")
            assert suffix != alternative_identity(
                other_seed_corpus.seed, family_id, "issuer_institution"
            )
            seen_institution_suffixes.add(suffix)

    assert len(seen_holder_suffixes) == 6
    assert len(seen_institution_suffixes) == 6
