"""Pacote sanitizado de anotação humana: sem gabarito, hash verificável, somente piloto."""

import base64
import copy
import hashlib
import json
import re
import subprocess
import sys

import pytest

from comprova_lattes.experiments.__main__ import write as write_corpus
from comprova_lattes.experiments.annotation_package import (
    FORBIDDEN_KEYS,
    GUIDE_VERSION,
    NEUTRAL_ID_PATTERN,
    PACKAGE_VERSION,
    PackageError,
    _assert_no_leak,
    build_package,
    compute_package_sha256,
    main,
    select_pilot_cases,
    validate_package,
)
from comprova_lattes.experiments.synthetic import CATEGORY_ORDER, generate

LEAK_TOKENS = (
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
)


@pytest.fixture(scope="module")
def corpus():
    return generate(seed=42, pilot_families=5, final_families=5)


@pytest.fixture(scope="module")
def built(corpus):
    return build_package(corpus)


def _originals(corpus, built):
    by_id = {c.case_id: c for c in corpus.cases}
    return {neutral: by_id[original] for neutral, original in built.private_map["cases"].items()}


def _keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _keys(child)


def test_package_has_five_pilot_cases_covering_categories_with_varied_operators(corpus, built):
    originals = _originals(corpus, built)
    assert len(built.package["cases"]) == 5
    assert all(c.partition == "pilot" for c in originals.values())
    categories = {c.curriculum.records[0].category for c in originals.values()}
    assert categories == set(CATEGORY_ORDER)
    assert len({c.family_id for c in originals.values()}) == 5
    assert len({c.operator for c in originals.values()}) >= 4


def test_public_package_contains_no_gold_operator_class_or_identity_metadata(corpus, built):
    package = built.package
    assert not set(_keys(package)) & FORBIDDEN_KEYS
    assert package["package_version"] == PACKAGE_VERSION
    assert package["guide_version"] == GUIDE_VERSION
    text = json.dumps(package, ensure_ascii=False).lower()
    assert not [token for token in LEAK_TOKENS if token in text]
    for case in _originals(corpus, built).values():
        assert case.case_id not in text
        assert case.template_id.lower() not in text
        if case.gold is not None and case.gold.issuer_acronym:
            assert case.gold.issuer_acronym.lower() not in text


def test_family_identity_values_only_appear_inside_compared_content(corpus, built):
    originals = _originals(corpus, built)
    for public in built.package["cases"]:
        outside = {k: v for k, v in public.items() if k not in ("xml", "record", "document")}
        family = originals[public["case_id"]].family_id.lower()
        assert family not in json.dumps(outside).lower()
        assert public["case_id"] == outside["case_id"]


def test_case_ids_are_neutral_sequential_and_do_not_follow_category_order(corpus, built):
    ids = [c["case_id"] for c in built.package["cases"]]
    assert ids == [f"case-{i:03d}" for i in range(1, 6)]
    assert all(NEUTRAL_ID_PATTERN.fullmatch(i) for i in ids)
    originals = _originals(corpus, built)
    shuffled = [originals[i].curriculum.records[0].category for i in ids]
    assert shuffled != list(CATEGORY_ORDER)
    assert set(built.private_map["cases"].values()).isdisjoint(ids)
    assert "private_map" not in json.dumps(built.package)


def test_build_is_deterministic_and_hash_matches_canonical_content(corpus, built):
    again = build_package(corpus)
    assert again.package == built.package
    assert built.package["package_sha256"] == compute_package_sha256(built.package)
    assert re.fullmatch(r"[0-9a-f]{64}", built.package["package_sha256"])
    assert built.private_map["package_sha256"] == built.package["package_sha256"]


def test_documents_and_xml_carry_matching_bytes_mime_and_hashes(corpus, built):
    for public in built.package["cases"]:
        original = _originals(corpus, built)[public["case_id"]]
        xml = base64.b64decode(public["xml"]["content_base64"])
        assert xml == original.xml
        assert public["xml"]["sha256"] == hashlib.sha256(original.xml).hexdigest()
        if original.document is None:
            assert public["document"] is None
        else:
            document = public["document"]
            assert base64.b64decode(document["content_base64"]) == original.document
            assert document["sha256"] == hashlib.sha256(original.document).hexdigest()
            assert document["mime_type"] == original.mime_type
        record = original.curriculum.records[0]
        assert public["record"]["title"] == record.title
        assert public["record"]["institution"] == record.institution
    assert any(c["document"] is None for c in built.package["cases"])


def test_validation_accepts_built_package_and_rejects_tampering(built):
    assert len(validate_package(built.package).cases) == 5

    changed = copy.deepcopy(built.package)
    changed["cases"][0]["record"]["title"] = "ALTERADO"
    with pytest.raises(PackageError, match="package_sha256"):
        validate_package(changed)

    bad_doc = copy.deepcopy(built.package)
    target = next(c for c in bad_doc["cases"] if c["document"] is not None)
    target["document"]["content_base64"] = base64.b64encode(b"%PDF-x").decode()
    bad_doc["package_sha256"] = compute_package_sha256(bad_doc)
    with pytest.raises(PackageError, match="hash"):
        validate_package(bad_doc)

    bad_mime = copy.deepcopy(built.package)
    target = next(c for c in bad_mime["cases"] if c["document"] is not None)
    target["document"]["mime_type"] = "text/html"
    bad_mime["package_sha256"] = compute_package_sha256(bad_mime)
    with pytest.raises(PackageError, match="MIME"):
        validate_package(bad_mime)


@pytest.mark.parametrize("key", ["gold", "expected", "operator", "family_id", "issuer_id"])
def test_validation_rejects_forbidden_and_unknown_keys(built, key):
    polluted = copy.deepcopy(built.package)
    polluted["cases"][0][key] = "x"
    polluted["package_sha256"] = compute_package_sha256(polluted)
    with pytest.raises(PackageError):
        validate_package(polluted)
    unknown = copy.deepcopy(built.package)
    unknown["cases"][0]["record"]["extra_field"] = 1
    unknown["package_sha256"] = compute_package_sha256(unknown)
    with pytest.raises(PackageError, match="Esquema"):
        validate_package(unknown)


def test_raw_corpus_is_not_a_valid_package(corpus, tmp_path):
    path = tmp_path / "raw-corpus.json"
    write_corpus(path, corpus)
    with pytest.raises(PackageError):
        validate_package(json.loads(path.read_text(encoding="utf-8")))


def test_neutral_id_must_not_be_original_style(built):
    renamed = copy.deepcopy(built.package)
    renamed["cases"][0]["case_id"] = "a" * 20
    renamed["package_sha256"] = compute_package_sha256(renamed)
    with pytest.raises(PackageError, match="neutro"):
        validate_package(renamed)


def test_assert_no_leak_rejects_family_or_issuer_outside_compared_content(corpus, built):
    selected = select_pilot_cases(corpus)
    leaked = copy.deepcopy(built.package)
    leaked["cases"][0]["case_id"] = f"case-001-{selected[0].family_id}"
    with pytest.raises(PackageError, match="família/emissor"):
        _assert_no_leak(leaked, selected)


def test_corpus_without_pilot_categories_is_rejected(corpus):
    short = generate(seed=7, pilot_families=3, final_families=5)
    with pytest.raises(PackageError, match="cinco categorias"):
        build_package(short)
    assert corpus.select("final")


def test_cli_exports_only_pilot_without_leaking_to_stdout(corpus, built, tmp_path, capsys):
    corpus_path = tmp_path / "corpus.json"
    out = tmp_path / "package.json"
    private = tmp_path / "private-map.json"
    write_corpus(corpus_path, corpus)

    code = main(
        ["--corpus", str(corpus_path), "--output", str(out), "--private-map", str(private)]
    )
    assert code == 0
    stdout = capsys.readouterr().out.lower()
    assert not [token for token in LEAK_TOKENS if token in stdout]
    assert json.loads(stdout)["case_count"] == 5

    package = json.loads(out.read_text(encoding="utf-8"))
    assert package == built.package
    assert len(validate_package(package).cases) == 5
    private_map = json.loads(private.read_text(encoding="utf-8"))
    pilot_ids = {c.case_id for c in corpus.select("pilot")}
    assert set(private_map["cases"].values()) <= pilot_ids
    assert "cases" in private_map and "private_map" not in out.read_text(encoding="utf-8")

    assert main(["--corpus", str(corpus_path), "--output", str(out)]) == 1
    assert "já existe" in capsys.readouterr().err
    assert main(["--corpus", str(corpus_path), "--output", str(out), "--overwrite"]) == 0
    assert main(["--corpus", str(corpus_path), "--output", str(out), "--private-map", str(out)]) == 1


def test_cli_reports_unreadable_corpus_clearly(tmp_path, capsys):
    bogus = tmp_path / "corpus.json"
    bogus.write_text("{}", encoding="utf-8")
    assert main(["--corpus", str(bogus), "--output", str(tmp_path / "out.json")]) == 1
    assert "ERRO" in capsys.readouterr().err
    assert not (tmp_path / "out.json").exists()


def test_module_runs_offline_without_database_queue_or_gemini_modules():
    script = (
        "import sys\n"
        "import comprova_lattes.experiments.annotation_package\n"
        "banned = ('sqlalchemy', 'psycopg', 'redis', 'celery', 'google.genai')\n"
        "loaded = [m for m in banned if m in sys.modules]\n"
        "sys.exit(1 if loaded else 0)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], check=False, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
