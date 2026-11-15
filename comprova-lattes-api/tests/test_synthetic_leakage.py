"""Testes de neutralidade textual, diferenças factuais e ausência de vazamento em valores."""

import re

import pytest

from comprova_lattes.experiments.synthetic import (
    alternative_identity,
    document_text,
    generate,
)
from comprova_lattes.matcher.models import MatchStatus
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
            assert changed_fields == {"issuer_institution"}
            assert mutated_case.gold.issuer_institution != record.institution
        else:
            pytest.fail(f"Categoria inesperada: {record.category} ({family_id})")


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
