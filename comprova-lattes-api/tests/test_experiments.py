"""Contratos experimentais com documentos fictícios e extratores locais."""

import struct
import zlib
from xml.etree.ElementTree import fromstring

import pytest

from comprova_lattes.experiments.__main__ import Replay, main, read, write
from comprova_lattes.experiments.baseline import OCRRegex
from comprova_lattes.experiments.freeze import calibrate, freeze, verify
from comprova_lattes.experiments.render import pdf, png, raster
from comprova_lattes.experiments.runner import (
    evaluate,
    experiment1,
    experiment2,
    experiment3,
    extraction_inference,
    extraction_metrics,
    inference,
)
from comprova_lattes.experiments.statistics import (
    classification,
    cluster_bootstrap,
    cohen_kappa,
    holm,
    mcnemar_exact,
)
from comprova_lattes.experiments.synthetic import (
    FIELD_LABELS,
    SYNTHETIC_ACRONYMS,
    Corpus,
    alternative_identity,
    document_text,
    generate,
    synthetic_acronyms,
)
from comprova_lattes.matcher.models import ExtractedDocumentRecord, MatcherConfig, MatcherThresholds
from comprova_lattes.matcher.text import normalize_text


@pytest.fixture(scope="module")
def corpus():
    return generate(seed=93, pilot_families=5, final_families=5)


@pytest.fixture
def config(corpus):
    # Valores exclusivos do teste; não são limiares científicos calibrados.
    return MatcherConfig(
        acronym_table=synthetic_acronyms(corpus.select("pilot")),
        acronym_table_version="synthetic-test-only",
        thresholds=MatcherThresholds(
            association=0.3,
            ambiguity_margin=0.01,
            holder_low=0.4,
            holder_high=0.95,
            title_low=0.4,
            title_high=0.95,
            institution_low=0.4,
            institution_high=0.95,
        )
    )


def test_deterministic_partition_and_categories(corpus):
    assert corpus == generate(seed=93, pilot_families=5, final_families=5)
    pilot, final = corpus.select("pilot"), corpus.select("final")
    assert pilot == generate(seed=93, pilot_families=5, final_families=20).select("pilot")
    assert len(corpus.cases) == 50
    assert len({c.curriculum.records[0].category for c in pilot}) == 5
    assert len(generate(seed=7, pilot_families=1, final_families=2).cases) == 15
    for attr in ("family_id", "template_id", "issuer_id"):
        assert not {getattr(c, attr) for c in pilot} & {getattr(c, attr) for c in final}
    assert len({c.case_id for c in corpus.cases}) == 50
    assert all(len(c.curriculum.records) == 1 for c in corpus.cases)
    leaked = final[0].model_copy(update={"family_id": pilot[0].family_id})
    with pytest.raises(ValueError, match="Vazamento"):
        Corpus(seed=93, cases=(*pilot, leaked))
    with pytest.raises(ValueError):
        generate(seed=1, pilot_families=0, final_families=1)


def test_png_crc_pixels_and_pdf_cross_reference():
    clean = raster("CERTIFICADO\nHOLDER_NAME: PESSOA 123", seed=4, degradation=0, layout=0)
    degraded = raster("CERTIFICADO\nHOLDER_NAME: PESSOA 123", seed=4, degradation=2, layout=0)
    assert degraded == raster(
        "CERTIFICADO\nHOLDER_NAME: PESSOA 123", seed=4, degradation=2, layout=0
    )
    assert clean[2] != degraded[2]
    image = png(*degraded)
    assert image[:8] == b"\x89PNG\r\n\x1a\n"
    offset, compressed = 8, b""
    while offset < len(image):
        size = struct.unpack("!I", image[offset : offset + 4])[0]
        kind, data = image[offset + 4 : offset + 8], image[offset + 8 : offset + 8 + size]
        assert (
            zlib.crc32(kind + data)
            == struct.unpack("!I", image[offset + 8 + size : offset + 12 + size])[0]
        )
        if kind == b"IDAT":
            compressed += data
        offset += 12 + size
    assert len(zlib.decompress(compressed)) == (degraded[0] + 1) * degraded[1]
    document = pdf(*degraded)
    assert document.startswith(b"%PDF-1.4") and document.endswith(b"%%EOF\n")
    start = int(document.split(b"startxref\n")[1].splitlines()[0])
    assert document[start : start + 4] == b"xref"
    entries = document[start:].splitlines()[3:8]
    for i, entry in enumerate(entries, 1):
        assert document[int(entry[:10]) :].startswith(f"{i} 0 obj".encode())
    assert degraded[2] == zlib.decompress(
        document.split(b"stream\n", 1)[1].split(b"\nendstream")[0]
    )


def test_baseline_injected_and_failures(corpus):
    c = next(c for c in corpus.cases if c.gold is not None)
    observed = []

    def ocr(data, mime):
        observed.append((data, mime))
        return document_text(
            c.gold, int(c.family_id, 16), category=c.curriculum.records[0].category
        )

    assert OCRRegex(ocr).extract(c.case_id, c.document, c.mime_type) == c.gold
    assert observed == [(c.document, c.mime_type)]
    assert OCRRegex(lambda *_: "").extract("x", b"x", "image/png").extraction_status == "UNREADABLE"
    assert (
        OCRRegex(lambda *_: "Carga horária: bad\nworkload_hours: bad")
        .extract("x", b"x", "image/png")
        .extraction_status
        == "INVALID_JSON"
    )


def test_three_runs_not_three_samples_and_failure_metrics(corpus):
    cases = corpus.select("final")
    gold = {c.case_id: c.gold for c in cases if c.gold}
    output = experiment1(cases, Replay([gold] * 3), Replay([gold]))
    assert output["n"] == len(gold)
    assert output["unstable_documents"] == 0
    assert output["stability_by_field"]["holder_name"] == 1
    statistics = extraction_inference(output, cases, seed=1, replicates=10, confidence=0.95)
    assert statistics["intervals"]["all_three"]["n"] == len(gold)
    assert all(r["n"] == len(gold) and r["all_fields_accuracy"] == 1 for r in output["literal"])
    changed = dict(gold)
    key = next(iter(gold))
    changed[key] = ExtractedDocumentRecord(document_id=key, extraction_status="API_ERROR")
    varied = experiment1(cases, Replay([gold, changed, gold]), Replay([gold]))
    assert varied["unstable_documents"] == 1
    metrics = extraction_metrics(cases, changed)
    assert metrics["failures"] == {"API_ERROR": 1}
    assert metrics["conditional_n"] == len(gold) - 1
    assert metrics["fields"]["holder_name"]["omitted"] == 1
    assert not metrics["correct"][key]


def test_runners_and_propagation(corpus, config):
    cases = corpus.select("final")
    reports = experiment2(cases, config)
    assert set(reports) == {"A", "B", "LEVENSHTEIN_NORM", "JARO_WINKLER", "TOKEN_HYBRID"}
    for report in reports.values():
        assert sum(map(sum, report["matrix"])) == len(cases)
        assert len(report["matrix"]) == 3
        assert report["review_stage"] == "automatic_before_human_review"
    gold = {c.case_id: c.gold for c in cases if c.gold}
    integrated = experiment3(cases, [gold] * 3, config)
    assert integrated["n"] == len(cases) and integrated["calls"] == 0
    assert integrated["runs"][0]["matrix"] == reports["LEVENSHTEIN_NORM"]["matrix"]
    mutated = dict(gold)
    c = next(c for c in cases if c.operator == "identity")
    mutated[c.case_id] = c.gold.model_copy(update={"activity_year": 2031, "end_year": 2031})
    result = experiment3(cases, [mutated] * 3, config)
    assert result["runs"][0]["error_causes"].get("extraction", 0) >= 1
    failed = {
        k: ExtractedDocumentRecord(document_id=k, extraction_status="UNREADABLE") for k in gold
    }
    result = evaluate(cases, failed, config)
    assert len(result["DOCUMENTO_NAO_ASSOCIADO"]) == len(gold)
    assert sum(map(sum, result["matrix"])) == len(cases)
    assert result["association"]["fn"] == len(gold)
    assert result["error_causes"].get("association", 0)
    stats = inference(reports, cases, seed=8, replicates=10, confidence=0.95)
    assert stats["intervals"]["A"]["families"] == 5
    assert list(stats["mcnemar"]) == [
        "LEVENSHTEIN_NORM:A",
        "LEVENSHTEIN_NORM:B",
        "LEVENSHTEIN_NORM:JARO_WINKLER",
        "LEVENSHTEIN_NORM:TOKEN_HYBRID",
    ]
    assert "A:B" not in stats["mcnemar"]
    assert all(entry["n"] == 5 for entry in stats["mcnemar"].values())


def _assert_unit_contracts_on_proposed(cases, proposed, glyphs):
    ad014_present_ops = set()
    ad014_absent_ops = set()
    for case, row in zip(cases, proposed["rows"], strict=True):
        record = case.curriculum.records[0]
        assert record.title and record.institution
        assert record.start_year and record.end_year == 2024
        if record.category == "ORGANIZACAO_EVENTO":
            assert record.event_name is None
        elif record.category in ("PARTICIPACAO_EVENTO", "APRESENTACAO_TRABALHO"):
            assert record.event_name

        assert row["association_correct"]

        if case.gold:
            text = document_text(
                case.gold, int(case.family_id, 16), category=record.category
            )
            assert all(ch.isprintable() or ch == "\n" for ch in text)
            if glyphs is not None:
                assert set(text.upper()) <= set(glyphs) | {" ", "\n"}
            if record.category == "APRESENTACAO_TRABALHO":
                assert case.gold.participation_role_raw == "APRESENTADOR"

            inst = next(
                f
                for f in row["automatic"]["field_evidences"]
                if f["field_name"] == "instituicao"
            )
            is_mutated_org = (
                case.operator == "factual_mutation" and record.category == "ORGANIZACAO_EVENTO"
            )
            if case.gold.issuer_name_acronym_evidence is not None:
                assert case.gold.issuer_acronym is not None
                ad014_present_ops.add(case.operator)
                if is_mutated_org:
                    assert inst["rule_applied"] != "DOCUMENT_ACRONYM_EQUIVALENCE"
                    assert inst["document_evidence"] is None
                else:
                    assert inst["rule_applied"] == "DOCUMENT_ACRONYM_EQUIVALENCE"
                    assert inst["document_evidence"] == case.gold.issuer_name_acronym_evidence
                    assert inst["outcome"] == "MATCH"
            else:
                assert case.gold.issuer_acronym is None
                ad014_absent_ops.add(case.operator)
                assert inst["rule_applied"] != "DOCUMENT_ACRONYM_EQUIVALENCE"
                assert inst["document_evidence"] is None
                if not is_mutated_org:
                    assert inst["outcome"] == "MATCH"

        if case.operator in ("identity", "legitimate"):
            assert row["status"] == "VALIDADO", (record.category, case.operator, row)
            assert row["reason"] == "VALIDADO_CORRESPONDENCIA_COMPLETA"
            assert row["correct"]
        elif case.operator == "factual_mutation":
            assert row["expected"] == "DIVERGENTE"
        elif case.operator == "omission":
            assert row["status"] == "INCONCLUSIVO"
            assert row["reason"] == "EVIDENCIA_INSUFICIENTE"
            assert row["correct"]
        elif case.operator == "no_document":
            assert row["status"] == "INCONCLUSIVO"
            assert row["reason"] == "SEM_COMPROVANTE"
            assert row["correct"]
        else:
            pytest.fail(f"Operador inesperado: {case.operator}")

    expected_doc_ops = {"identity", "legitimate", "factual_mutation", "omission"}
    assert ad014_present_ops == expected_doc_ops
    assert ad014_absent_ops == expected_doc_ops


@pytest.mark.parametrize("partition", ["pilot", "final"])
def test_synthetic_categories_and_operator_verdicts(corpus, config, partition):
    """Contrato unitário/estrutural separado da avaliação de desempenho calibrada."""
    import comprova_lattes.experiments.render as render_module

    glyphs = getattr(render_module, "_GLYPHS", None)
    cases = corpus.select(partition)
    assert len(cases) == 25
    proposed = experiment2(cases, config)["LEVENSHTEIN_NORM"]
    _assert_unit_contracts_on_proposed(cases, proposed, glyphs)
    if partition == "final":
        empty_table = config.model_copy(update={"acronym_table": {}})
        empty_proposed = experiment2(cases, empty_table)["LEVENSHTEIN_NORM"]
        _assert_unit_contracts_on_proposed(cases, empty_proposed, glyphs)


def test_synthetic_xml_structure_and_raster_alphabet(corpus):
    import comprova_lattes.experiments.render as render_module

    glyphs = getattr(render_module, "_GLYPHS", None)
    for case in corpus.cases:
        record = case.curriculum.records[0]
        assert record.title and record.institution and record.end_year == 2024
        if record.category in (
            "PARTICIPACAO_EVENTO", "APRESENTACAO_TRABALHO", "ORGANIZACAO_EVENTO"
        ):
            root = fromstring(case.xml)
            assert any(node.tag.startswith("DADOS-BASICOS-") for node in root.iter())
            assert any(node.tag.startswith("DETALHAMENTO-") for node in root.iter())
        if record.category == "ORGANIZACAO_EVENTO":
            assert record.event_name is None
        if case.gold:
            text = document_text(
                case.gold, int(case.family_id, 16), category=record.category
            )
            assert all(ch.isprintable() or ch == "\n" for ch in text)
            if glyphs is not None:
                assert set(text.upper()) <= set(glyphs) | {" ", "\n"}


def test_legitimate_variation_and_factual_mutations(corpus, config):
    from comprova_lattes.matcher.rules import compare_institution

    assert SYNTHETIC_ACRONYMS == {"IF": "INSTITUTO FICTICIO"}
    assert config.acronym_table == synthetic_acronyms(corpus.select("pilot"))
    assert not (set(config.acronym_table) & set(synthetic_acronyms(corpus.select("final"))))
    empty_config = config.model_copy(update={"acronym_table": {}})
    scalar_mutations = {
        "FORMACAO_ACADEMICA": ("workload_hours", 45),
        "FORMACAO_COMPLEMENTAR": ("workload_hours", 400),
        "PARTICIPACAO_EVENTO": ("activity_year", 2031),
    }
    identity_by_family = {
        c.family_id: c for c in corpus.cases if c.operator == "identity"
    }
    for case in corpus.cases:
        record = case.curriculum.records[0]
        if case.gold is not None:
            is_mutated_inst = (
                case.operator == "factual_mutation" and record.category == "ORGANIZACAO_EVENTO"
            )
            if case.gold.issuer_name_acronym_evidence is not None:
                expected_suffix = (
                    alternative_identity(corpus.seed, case.family_id, "issuer_institution")
                    if is_mutated_inst
                    else case.issuer_id.upper()
                )
                expected_acronym = f"IF{expected_suffix}"
                assert case.gold.issuer_acronym == expected_acronym
                assert (
                    case.gold.issuer_name_acronym_evidence
                    == f"{case.gold.issuer_institution} - {expected_acronym}"
                )
                xml_acronym_rel = compare_institution(
                    record.model_copy(update={"institution": f"IF{case.issuer_id.upper()}"}),
                    case.gold,
                    empty_config,
                )
                doc_acronym_rel = compare_institution(
                    record.model_copy(update={"institution": expected_acronym}),
                    case.gold,
                    empty_config,
                )
                if is_mutated_inst:
                    assert xml_acronym_rel.outcome != "MATCH"
                    assert (
                        compare_institution(record, case.gold, empty_config).rule_applied
                        != "DOCUMENT_ACRONYM_EQUIVALENCE"
                    )
                    assert doc_acronym_rel.rule_applied == "DOCUMENT_ACRONYM_EQUIVALENCE"
                else:
                    assert doc_acronym_rel.outcome == "MATCH"
                    assert doc_acronym_rel.rule_applied == "DOCUMENT_ACRONYM_EQUIVALENCE"
                    assert doc_acronym_rel.document_evidence == case.gold.issuer_name_acronym_evidence
            else:
                assert case.gold.issuer_acronym is None

        if case.operator == "legitimate":
            expected_acronym = f"IF{case.issuer_id.upper()}"
            assert normalize_text(case.gold.issuer_institution) == normalize_text(
                record.institution
            )
            assert synthetic_acronyms((case,))[expected_acronym] == record.institution
            acronym_only_doc = case.gold.model_copy(
                update={
                    "issuer_institution": expected_acronym,
                    "issuer_acronym": None,
                    "issuer_name_acronym_evidence": None,
                }
            )
            if case.partition == "pilot":
                assert (
                    compare_institution(record, acronym_only_doc, config).rule_applied
                    == "ACRONYM_EQUIVALENCE"
                )
            else:
                assert compare_institution(record, acronym_only_doc, config).outcome != "MATCH"
                with_table = config.model_copy(
                    update={"acronym_table": synthetic_acronyms((case,))}
                )
                assert (
                    compare_institution(record, acronym_only_doc, with_table).rule_applied
                    == "ACRONYM_EQUIVALENCE"
                )
            assert case.gold.activity_title != "X" + record.title[1:]
            assert normalize_text(case.gold.activity_title) == normalize_text(record.title)
            assert normalize_text(case.gold.holder_name) == normalize_text(
                case.curriculum.full_name
            )
            assert any(
                [
                    case.gold.holder_name != case.curriculum.full_name,
                    case.gold.activity_title != record.title,
                    case.gold.issuer_institution != record.institution,
                    case.gold.event_name != record.event_name,
                ]
            )
        elif case.operator == "factual_mutation":
            baseline_gold = identity_by_family[case.family_id].gold
            if record.category in scalar_mutations:
                field, value = scalar_mutations[record.category]
                assert getattr(case.gold, field) == value
                if field == "workload_hours":
                    assert record.workload_hours == 40
                elif field == "activity_year":
                    assert case.gold.start_year == case.gold.end_year == 2031
            elif record.category == "APRESENTACAO_TRABALHO":
                expected_holder = (
                    f"PESSOA FICTICIA {alternative_identity(corpus.seed, case.family_id, 'holder_name')}"
                )
                assert case.gold.holder_name == expected_holder
                assert case.gold.holder_name != case.curriculum.full_name
                assert case.gold.holder_name.startswith("PESSOA FICTICIA ")
                assert len(case.gold.holder_name) == len(case.curriculum.full_name)
                assert case.gold.model_copy(
                    update={"document_id": baseline_gold.document_id, "holder_name": baseline_gold.holder_name}
                ) == baseline_gold
            elif record.category == "ORGANIZACAO_EVENTO":
                expected_inst = (
                    "INSTITUTO FICTICIO "
                    f"{alternative_identity(corpus.seed, case.family_id, 'issuer_institution')}"
                )
                assert case.gold.issuer_institution == expected_inst
                assert case.gold.issuer_institution != record.institution
                assert case.gold.issuer_institution.startswith("INSTITUTO FICTICIO ")
                assert len(case.gold.issuer_institution) == len(record.institution)
                restore = {
                    "document_id": baseline_gold.document_id,
                    "issuer_institution": baseline_gold.issuer_institution,
                }
                if baseline_gold.issuer_name_acronym_evidence is not None:
                    restore["issuer_acronym"] = baseline_gold.issuer_acronym
                    restore["issuer_name_acronym_evidence"] = (
                        baseline_gold.issuer_name_acronym_evidence
                    )
                assert case.gold.model_copy(update=restore) == baseline_gold


def test_statistics_known_values():
    kappa = cohen_kappa(["A", "A", "B", "B"], ["A", "B", "B", "B"])
    assert kappa["kappa"] == pytest.approx(0.5)
    assert cohen_kappa(["A"], ["A"])["kappa"] is None
    test = mcnemar_exact({"a": True, "b": True, "c": True}, {"a": False, "b": False, "c": True})
    assert test["b"] == 2 and test["c"] == 0 and test["p_value"] == 0.5
    assert holm({"a": 0.01, "b": 0.04, "c": 0.03}) == pytest.approx(
        {"a": 0.03, "c": 0.06, "b": 0.06}
    )
    seen = []

    def metric(indices):
        assert indices.count(0) == indices.count(1)
        seen.append(indices)
        return sum(indices) / len(indices)

    a = cluster_bootstrap(["a", "a", "b"], metric, seed=3, replicates=100, confidence=0.95)
    b = cluster_bootstrap(["a", "a", "b"], metric, seed=3, replicates=100, confidence=0.95)
    assert a == b and a["families"] == 2 and a["low"] <= a["estimate"] <= a["high"]
    assert classification(["VALIDADO"], ["VALIDADO"])["macro_f1"] == 1 / 3
    with pytest.raises(ValueError):
        mcnemar_exact({"a": True}, {"b": True})


def test_calibration_freeze_and_tampering(corpus, config):
    calibration = calibrate(corpus.select("pilot"), [config, config])
    assert calibration["selected"] == 0
    artifacts = {
        k: k.encode()
        for k in (
            "schema",
            "prompt",
            "regex",
            "acronyms",
            "normalization",
            "generator",
            "code",
            "environment",
        )
    }
    manifest = freeze(corpus, calibration, artifacts)
    verify(manifest, corpus, artifacts)
    with pytest.raises(ValueError):
        verify(manifest, corpus, dict(artifacts, prompt=b"changed"))
    with pytest.raises(ValueError):
        calibrate(corpus.select("final"), [config])
    with pytest.raises(ValueError):
        freeze(corpus, calibration, {})
    altered = corpus.model_copy(
        update={
            "cases": (
                corpus.cases[0].model_copy(update={"degradation": 2 - corpus.cases[0].degradation}),
                *corpus.cases[1:],
            )
        }
    )
    with pytest.raises(ValueError):
        verify(manifest, altered, artifacts)


@pytest.mark.parametrize("status", ["API_ERROR", "INVALID_JSON", "UNREADABLE"])
def test_every_failure_keeps_denominator(corpus, status):
    case = next(c for c in corpus.cases if c.gold)
    result = extraction_metrics(
        [case],
        {case.case_id: ExtractedDocumentRecord(document_id=case.case_id, extraction_status=status)},
    )
    assert result["n"] == 1 and result["failure_rate"] == 1
    assert result["conditional_n"] == 0 and result["conditional_accuracy"] is None
    assert result["failures"] == {status: 1}


@pytest.mark.parametrize(
    "operation",
    [
        lambda: cohen_kappa([], []),
        lambda: classification(["VALIDADO"], []),
        lambda: cluster_bootstrap([], lambda _: 0, seed=1, replicates=2, confidence=0.95),
        lambda: holm({"a": -1}),
        lambda: raster("ABC", seed=1, degradation=3, layout=0),
    ],
)
def test_invalid_statistical_inputs(operation):
    with pytest.raises(ValueError):
        operation()


def test_cli_roundtrip_all_experiments(tmp_path, corpus, config):
    def path(name):
        return tmp_path / name

    write(path("corpus.json"), corpus)
    assert Corpus.model_validate(read(path("corpus.json"))) == corpus
    write(path("candidates.json"), [config])
    main(
        [
            "calibrate",
            "--corpus",
            str(path("corpus.json")),
            "--candidates",
            str(path("candidates.json")),
            "--output",
            str(path("calibration.json")),
        ]
    )
    artifacts = {}
    for name in (
        "schema",
        "prompt",
        "regex",
        "acronyms",
        "normalization",
        "generator",
        "code",
        "environment",
    ):
        path(name).write_bytes(name.encode())
        artifacts[name] = str(path(name))
    write(path("artifacts.json"), artifacts)
    main(
        [
            "freeze",
            "--corpus",
            str(path("corpus.json")),
            "--calibration",
            str(path("calibration.json")),
            "--artifacts",
            str(path("artifacts.json")),
            "--output",
            str(path("manifest.json")),
        ]
    )
    gold = {c.case_id: c.gold for c in corpus.select("final") if c.gold}
    write(path("runs.json"), [gold] * 3)
    write(path("ocr.json"), gold)
    common = [
        "--corpus",
        str(path("corpus.json")),
        "--manifest",
        str(path("manifest.json")),
        "--artifacts",
        str(path("artifacts.json")),
        "--partition",
        "final",
        "--output",
        str(path("report.json")),
    ]
    for command in ("exp1", "exp2", "exp3"):
        extra = (
            ["--seed", "8", "--replicates", "10", "--confidence", ".95"]
            if command == "exp2"
            else (["--extractions", str(path("runs.json"))])
        )
        if command == "exp1":
            extra += ["--baseline", str(path("ocr.json"))]
        main([command, *common, *extra])
        assert read(path("report.json"))["partition"] == "final"


def test_approved_workbench_size_and_family_structure():
    from collections import Counter

    corpus = generate(seed=42, pilot_families=10, final_families=20)
    assert corpus == generate(seed=42, pilot_families=10, final_families=20)
    assert corpus.select("pilot") == generate(seed=42, pilot_families=10, final_families=5).select(
        "pilot"
    )
    for partition, n_families in (("pilot", 10), ("final", 20)):
        cases = corpus.select(partition)
        families = {c.family_id for c in cases}
        assert len(cases) == n_families * 5
        assert len(families) == n_families
        assert set(Counter(c.curriculum.records[0].category for c in cases).values()) == {
            n_families
        }
        assert set(Counter(c.operator for c in cases).values()) == {n_families}
        assert sum(c.document is not None for c in cases) == n_families * 4
        assert sum(c.gold is not None for c in cases) == n_families * 4
        for family in families:
            members = [c for c in cases if c.family_id == family]
            assert len(members) == 5
            assert len({c.xml for c in members}) == 1
            assert len({c.template_id for c in members}) == 1
            assert {c.operator for c in members} == {
                "identity", "legitimate", "factual_mutation", "omission", "no_document"
            }
    layouts = [
        [
            line
            for line in document_text(
                c.gold, int(c.family_id, 16), category=c.curriculum.records[0].category
            ).splitlines()
            if ":" in line
        ]
        for c in corpus.cases
        if c.operator == "identity"
    ]
    orders = {tuple(line.split(":", 1)[0] for line in lines) for lines in layouts}
    assert len(orders) > 2


def test_template_relative_key_order_and_skip_no_document_render(monkeypatch, corpus):
    import comprova_lattes.experiments.synthetic as synthetic_module

    def field_keys(record, layout, category=None):
        return [
            line.split(":", 1)[0]
            for line in document_text(record, layout, category=category).splitlines()
            if ":" in line
        ]

    for family_id in {c.family_id for c in corpus.cases}:
        by_op = {c.operator: c for c in corpus.cases if c.family_id == family_id}
        category = by_op["identity"].curriculum.records[0].category
        for layout in (0, 1, int(family_id, 16)):
            identity_keys = field_keys(by_op["identity"].gold, layout, category)
            omission_keys = field_keys(by_op["omission"].gold, layout, category)
            legitimate_keys = field_keys(by_op["legitimate"].gold, layout, category)
            assert omission_keys == [
                k for k in identity_keys if k != FIELD_LABELS["holder_name"]
            ]
            assert [k for k in legitimate_keys if k in set(identity_keys)] == identity_keys

    raster_calls = 0
    original_raster = synthetic_module.raster

    def counted_raster(*args, **kwargs):
        nonlocal raster_calls
        raster_calls += 1
        return original_raster(*args, **kwargs)

    monkeypatch.setattr(synthetic_module, "raster", counted_raster)
    sample = generate(seed=19, pilot_families=2, final_families=3)
    assert len(sample.cases) == 25
    assert raster_calls == 20
    assert all(
        c.gold is None and c.document is None
        for c in sample.cases
        if c.operator == "no_document"
    )


@pytest.mark.parametrize("partition", ["pilot", "final"])
def test_synthetic_unit_contracts_with_distributed_ad014(corpus, config, partition):
    cases = corpus.select(partition)
    proposed = experiment2(cases, config)["LEVENSHTEIN_NORM"]
    ad014_ops_seen = set()
    no_ad014_ops_seen = set()
    for case, row in zip(cases, proposed["rows"], strict=True):
        record = case.curriculum.records[0]
        assert row["association_correct"]
        if case.operator in ("identity", "legitimate"):
            assert row["status"] == "VALIDADO"
        elif case.operator in ("omission", "no_document"):
            assert row["status"] == "INCONCLUSIVO"

        if case.gold is not None:
            inst = next(
                f
                for f in row["automatic"]["field_evidences"]
                if f["field_name"] == "instituicao"
            )
            if case.gold.issuer_name_acronym_evidence is not None:
                ad014_ops_seen.add(case.operator)
                if case.operator == "factual_mutation" and record.category == "ORGANIZACAO_EVENTO":
                    assert inst["rule_applied"] != "DOCUMENT_ACRONYM_EQUIVALENCE"
                    assert inst["document_evidence"] is None
                else:
                    assert inst["rule_applied"] == "DOCUMENT_ACRONYM_EQUIVALENCE"
                    assert inst["document_evidence"] == case.gold.issuer_name_acronym_evidence
            else:
                no_ad014_ops_seen.add(case.operator)
                assert inst["rule_applied"] != "DOCUMENT_ACRONYM_EQUIVALENCE"
                assert inst["document_evidence"] is None

    expected_doc_ops = {"identity", "legitimate", "factual_mutation", "omission"}
    assert ad014_ops_seen == expected_doc_ops
    assert no_ad014_ops_seen == expected_doc_ops
