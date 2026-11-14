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
    SYNTHETIC_ACRONYMS,
    Corpus,
    document_text,
    generate,
    synthetic_acronyms,
)
from comprova_lattes.matcher.models import ExtractedDocumentRecord, MatcherConfig, MatcherThresholds


@pytest.fixture(scope="module")
def corpus():
    return generate(seed=93, pilot_families=1, final_families=1)


@pytest.fixture
def config(corpus):
    # Valores exclusivos do teste; não são limiares científicos calibrados.
    return MatcherConfig(
        acronym_table=synthetic_acronyms(corpus.cases),
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
    assert corpus == generate(seed=93, pilot_families=1, final_families=1)
    pilot, final = corpus.select("pilot"), corpus.select("final")
    assert len(corpus.cases) == 50
    assert len({c.curriculum.records[0].category for c in pilot}) == 5
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
        return document_text(c.gold)

    assert OCRRegex(ocr).extract(c.case_id, c.document, c.mime_type) == c.gold
    assert observed == [(c.document, c.mime_type)]
    assert OCRRegex(lambda *_: "").extract("x", b"x", "image/png").extraction_status == "UNREADABLE"
    assert (
        OCRRegex(lambda *_: "workload_hours: bad").extract("x", b"x", "image/png").extraction_status
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
    assert stats["intervals"]["A"]["families"] == 1
    assert stats["mcnemar"]["A:B"]["n"] == 1


@pytest.mark.parametrize("partition", ["pilot", "final"])
def test_synthetic_categories_and_operator_verdicts(corpus, config, partition):
    from comprova_lattes.experiments.render import _GLYPHS

    cases = corpus.select(partition)
    assert len(cases) == 25
    reports = experiment2(cases, config)
    proposed = reports["LEVENSHTEIN_NORM"]
    assert proposed["macro_f1"] > reports["A"]["macro_f1"]
    assert proposed["macro_f1"] > reports["B"]["macro_f1"]
    for case, row in zip(cases, proposed["rows"], strict=True):
        record = case.curriculum.records[0]
        assert record.title and record.institution
        assert record.start_year and record.end_year == 2024
        if record.category == "ORGANIZACAO_EVENTO":
            assert record.event_name is None
        elif record.category in ("PARTICIPACAO_EVENTO", "APRESENTACAO_TRABALHO"):
            assert record.event_name
        if case.gold:
            assert set(document_text(case.gold).upper()) <= set(_GLYPHS) | {" ", "\n"}
        if case.operator in ("identity", "legitimate"):
            assert row["status"] == "VALIDADO", (record.category, case.operator, row)
            if record.category == "APRESENTACAO_TRABALHO":
                assert case.gold.participation_role_raw == "APRESENTADOR"
        elif case.operator == "factual_mutation":
            assert row["status"] == "DIVERGENTE"
            assert row["association_correct"]
        else:
            assert row["status"] == "INCONCLUSIVO"
    assert proposed["macro_f1"] == 1


def test_synthetic_xml_structure_and_raster_alphabet(corpus):
    from comprova_lattes.experiments.render import _GLYPHS

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
            assert set(document_text(case.gold).upper()) <= set(_GLYPHS) | {" ", "\n"}


def test_legitimate_variation_and_factual_mutations(corpus, config):
    assert SYNTHETIC_ACRONYMS == {"IF": "INSTITUTO FICTICIO"}
    fields = {
        "FORMACAO_ACADEMICA": ("workload_hours", 45),
        "FORMACAO_COMPLEMENTAR": ("workload_hours", 400),
        "PARTICIPACAO_EVENTO": ("activity_year", 2031),
        "APRESENTACAO_TRABALHO": ("holder_name", "OUTRA PESSOA SINTETICA"),
        "ORGANIZACAO_EVENTO": ("issuer_institution", "INSTITUICAO DIVERGENTE SINTETICA"),
    }
    for case in corpus.cases:
        record = case.curriculum.records[0]
        if case.operator == "legitimate":
            assert config.acronym_table[case.gold.issuer_institution] == record.institution
            assert len(record.title) >= 25
            assert sum(a != b for a, b in zip(record.title, case.gold.activity_title)) == 1
        elif case.operator == "factual_mutation":
            field, value = fields[record.category]
            assert getattr(case.gold, field) == value
            if field == "workload_hours":
                assert record.workload_hours == 40
            elif field == "activity_year":
                assert case.gold.start_year == case.gold.end_year == 2031


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
