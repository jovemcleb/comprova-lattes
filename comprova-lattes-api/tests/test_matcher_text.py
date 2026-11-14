import pytest

from comprova_lattes.matcher.text import (
    acronym_identity,
    jaro_winkler_similarity,
    levenshtein_similarity,
    normalize_role,
    normalize_text,
    token_similarity,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, None),
        ("", None),
        ("  --- ... ", None),
        (" CIÊNCIA / Dados ", "ciencia dados"),
        ("A_B—C", "a b c"),
        ("Straße", "strasse"),
    ],
)
def test_normalization(raw, expected):
    assert normalize_text(raw) == expected


@pytest.mark.parametrize(
    "metric", [levenshtein_similarity, jaro_winkler_similarity, token_similarity]
)
@pytest.mark.parametrize("a,b", [("", ""), ("a", ""), ("", "b")])
def test_empty_guard(metric, a, b):
    assert metric(a, b) == 0.0


@pytest.mark.parametrize(
    "metric", [levenshtein_similarity, jaro_winkler_similarity, token_similarity]
)
@pytest.mark.parametrize("a,b", [("abc", "abc"), ("abc", "xyz"), ("Maria Silva", "Maria Siva")])
def test_metric_bounds_and_symmetry(metric, a, b):
    score = metric(a, b)
    assert 0 <= score <= 1
    assert score == pytest.approx(metric(b, a))


def test_metric_reference_values():
    assert levenshtein_similarity("kitten", "sitting") == pytest.approx(1 - 3 / 7)
    assert jaro_winkler_similarity("MARTHA", "MARHTA") == pytest.approx(0.96111111)
    assert token_similarity("ciencia de dados", "dados de ciencia") == 1
    assert token_similarity("a b", "b c") == pytest.approx(1 / 3)


def test_explicit_acronym_table():
    table = {"UFRA": "Universidade Federal Rural da Amazônia"}
    assert acronym_identity("UFRA", table) == acronym_identity(table["UFRA"], table)
    assert acronym_identity("UFPA", table) != acronym_identity("UFRA", table)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Conferencista", "PALESTRANTE"),
        ("comissão organizadora", "ORGANIZADOR"),
        ("Apresentação de trabalho", "APRESENTADOR"),
        ("OUVINTE", "OUVINTE"),
        ("Congresso", None),
        ("Debatedor", None),
        (None, None),
    ],
)
def test_explicit_roles_only(raw, expected):
    assert normalize_role(raw) == expected
