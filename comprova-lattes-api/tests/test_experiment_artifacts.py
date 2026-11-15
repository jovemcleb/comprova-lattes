"""Testes offline do preparador de artefatos pré-freeze (experiments/artifacts.py)."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from comprova_lattes.experiments import baseline, render
from comprova_lattes.experiments.__main__ import read as cli_read
from comprova_lattes.experiments.artifacts import (
    DEFAULT_EXPERIMENTAL_MODEL,
    EXPLICIT_CODE_SCOPE,
    REQUIRED_ARTIFACTS,
    collect_artifacts,
    main,
)
from comprova_lattes.experiments.freeze import calibrate, freeze, verify
from comprova_lattes.experiments.synthetic import generate, synthetic_acronyms
from comprova_lattes.matcher.models import ExtractedDocumentRecord, MatcherConfig, MatcherThresholds


def _write_sample_acronyms(path: Path, table: dict[str, str] | None = None) -> Path:
    payload = {
        "version": "pilot-explicit-v1",
        "acronym_table": table
        or {
            "UFRA": "Universidade Federal Rural da Amazonia",
            "IF01": "Instituto Ficticio 01",
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _copy_package_tree(dest_root: Path) -> Path:
    src_pkg = Path(__file__).resolve().parents[1] / "src" / "comprova_lattes"
    target_pkg = dest_root / "src" / "comprova_lattes"
    for rel_path in EXPLICIT_CODE_SCOPE:
        src_file = src_pkg / rel_path
        dst_file = target_pkg / rel_path
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
    pyproject_src = src_pkg.parents[1] / "pyproject.toml"
    if pyproject_src.is_file():
        shutil.copy2(pyproject_src, dest_root / "pyproject.toml")
    return target_pkg


def test_collect_artifacts_required_keys_and_cli_compatibility(tmp_path):
    acronyms_file = _write_sample_acronyms(tmp_path / "acronyms.json")
    out_dir = tmp_path / "prepared"

    result = collect_artifacts(output_dir=out_dir, acronyms_path=acronyms_file)
    report = result["report"]

    assert report["frozen"] is False
    assert report["freeze_status"] == "prepared_not_frozen"
    assert set(result["artifacts_map"]) == set(REQUIRED_ARTIFACTS)

    loaded_map = cli_read(result["artifacts_file"])
    assert set(loaded_map) == set(REQUIRED_ARTIFACTS)
    artifacts_bytes = {k: Path(v).read_bytes() for k, v in loaded_map.items()}
    assert all(len(v) > 0 for v in artifacts_bytes.values())

    schema_data = json.loads(artifacts_bytes["schema"])
    assert "properties" in schema_data["json_schema"]
    assert "workload_hours" in schema_data["json_schema"]["properties"]
    assert schema_data["extracted_record_json_schema"] == ExtractedDocumentRecord.model_json_schema()

    prompt_data = json.loads(artifacts_bytes["prompt"])
    assert prompt_data["prompt_version"] == "entities-v2"
    assert "issuer_name_acronym_evidence" in prompt_data["prompt"]
    assert prompt_data["experimental_model"] == DEFAULT_EXPERIMENTAL_MODEL
    assert prompt_data["supports_temperature"] is False
    assert prompt_data["temperature"] is None
    assert prompt_data["temperature_policy"] == "provider_default"

    regex_data = json.loads(artifacts_bytes["regex"])
    assert regex_data["patterns"] == baseline.PATTERNS
    assert regex_data["field_labels_pt"] == baseline.FIELD_LABELS_PT

    acronyms_data = json.loads(artifacts_bytes["acronyms"])
    assert acronyms_data["version"] == "pilot-explicit-v1"
    assert acronyms_data["acronym_table"]["UFRA"] == "Universidade Federal Rural da Amazonia"

    generator_data = json.loads(artifacts_bytes["generator"])
    assert generator_data["template_provenance"]["status"] == "draft_pending_human_validation"
    assert generator_data["template_provenance"]["human_approval_required_before_freeze"] is True
    assert generator_data["rasterizer_version"] == render.RASTERIZER_VERSION

    code_data = json.loads(artifacts_bytes["code"])
    recorded_paths = {entry["path"] for entry in code_data["files"]}
    assert recorded_paths == {f"src/comprova_lattes/{p}" for p in EXPLICIT_CODE_SCOPE}
    assert code_data["git_diff_included"] is False

    # Compatibilidade direta com freeze/verify da CLI existente (sem executá-lo automaticamente).
    corpus = generate(seed=11, pilot_families=1, final_families=1)
    cfg = MatcherConfig(
        acronym_table=synthetic_acronyms(corpus.select("pilot")),
        acronym_table_version="test-only",
        thresholds=MatcherThresholds(
            association=0.3,
            ambiguity_margin=0.01,
            holder_low=0.4,
            holder_high=0.95,
            title_low=0.4,
            title_high=0.95,
            institution_low=0.4,
            institution_high=0.95,
        ),
    )
    calibration = calibrate(corpus.select("pilot"), [cfg])
    manifest = freeze(corpus, calibration, artifacts_bytes)
    verify(manifest, corpus, artifacts_bytes)


def test_determinism_and_volatile_metadata_separation(tmp_path):
    acronyms_file = _write_sample_acronyms(tmp_path / "acronyms.json")
    fixed_ocr = lambda: {
        "engine": "tesseract",
        "available": False,
        "executable": None,
        "tesseract_version": None,
        "language": "por",
        "language_available": False,
        "available_languages": [],
        "tessdata_dir": None,
        "dpi": 300,
        "pdf_render_scale": 300 / 72.0,
        "timeout_seconds": 30.0,
        "max_pdf_pages": 10,
        "max_image_pixels": 25_000_000,
        "supported_mime_types": ["application/pdf", "image/jpeg", "image/png"],
        "pdf_conversion_library": "pypdfium2",
        "pypdfium2_version": None,
        "pdfium_version": None,
        "pillow_version": None,
        "pdf_text_extraction": "disabled_raster_only",
        "error": "tesseract ausente",
        "limitations": ["stub"],
    }

    run_a = collect_artifacts(
        output_dir=tmp_path / "run_a",
        acronyms_path=acronyms_file,
        ocr_probe=fixed_ocr,
    )
    run_b = collect_artifacts(
        output_dir=tmp_path / "run_b",
        acronyms_path=acronyms_file,
        ocr_probe=fixed_ocr,
    )

    for name in REQUIRED_ARTIFACTS:
        bytes_a = Path(run_a["artifacts_map"][name]).read_bytes()
        bytes_b = Path(run_b["artifacts_map"][name]).read_bytes()
        assert bytes_a == bytes_b, f"Artefato {name} não foi determinístico"

    assert run_a["report"]["stable_identity"] == run_b["report"]["stable_identity"]
    assert "collected_at_utc" in run_a["report"]["volatile_metadata"]
    assert "collected_at_utc" not in run_a["report"]["stable_identity"]


def test_hash_change_detection_and_mid_run_source_drift(tmp_path):
    copied_pkg = _copy_package_tree(tmp_path / "repo")
    acronyms_file = _write_sample_acronyms(tmp_path / "acronyms.json")

    base = collect_artifacts(
        output_dir=tmp_path / "base",
        acronyms_path=acronyms_file,
        source_root=copied_pkg,
    )
    base_hashes = base["report"]["stable_identity"]["artifacts_sha256"]

    # 1) Alteração na normalização muda normalization e code, mantendo prompt/regex/acronyms.
    text_py = copied_pkg / "matcher" / "text.py"
    text_py.write_text(text_py.read_text(encoding="utf-8") + "\n# ajuste\n", encoding="utf-8")
    after_norm = collect_artifacts(
        output_dir=tmp_path / "after_norm",
        acronyms_path=acronyms_file,
        source_root=copied_pkg,
    )
    norm_hashes = after_norm["report"]["stable_identity"]["artifacts_sha256"]
    assert norm_hashes["normalization"] != base_hashes["normalization"]
    assert norm_hashes["code"] != base_hashes["code"]
    assert norm_hashes["prompt"] == base_hashes["prompt"]
    assert norm_hashes["acronyms"] == base_hashes["acronyms"]

    # 2) Alteração no PROMPT de gemini.py muda prompt e code.
    gemini_py = copied_pkg / "extractor" / "gemini.py"
    gemini_text = gemini_py.read_text(encoding="utf-8").replace(
        'PROMPT_VERSION = "entities-v2"',
        'PROMPT_VERSION = "entities-v2-test-mutated"',
    )
    gemini_py.write_text(gemini_text, encoding="utf-8")
    after_prompt = collect_artifacts(
        output_dir=tmp_path / "after_prompt",
        acronyms_path=acronyms_file,
        source_root=copied_pkg,
    )
    assert (
        after_prompt["report"]["stable_identity"]["artifacts_sha256"]["prompt"]
        != norm_hashes["prompt"]
    )
    assert after_prompt["report"]["stable_identity"]["prompt_version"] == "entities-v2-test-mutated"

    # 3) Alteração no dicionário explícito de siglas muda acronyms.
    acronyms_file_2 = _write_sample_acronyms(
        tmp_path / "acronyms_v2.json",
        table={"UFRA": "Universidade Federal Rural da Amazonia", "CNPQ": "Conselho Nacional"},
    )
    after_acronyms = collect_artifacts(
        output_dir=tmp_path / "after_acronyms",
        acronyms_path=acronyms_file_2,
        source_root=copied_pkg,
    )
    assert (
        after_acronyms["report"]["stable_identity"]["artifacts_sha256"]["acronyms"]
        != norm_hashes["acronyms"]
    )

    # 4) Deriva entre leitura inicial e fim da coleta gera aviso explícito.
    def mutate_during_run():
        rules_py = copied_pkg / "matcher" / "rules.py"
        rules_py.write_text(rules_py.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")

    with pytest.warns(RuntimeWarning, match="modificados"):
        drifted = collect_artifacts(
            output_dir=tmp_path / "drifted",
            acronyms_path=acronyms_file,
            source_root=copied_pkg,
            post_write_hook=mutate_during_run,
        )
    volatile = drifted["report"]["volatile_metadata"]
    assert volatile["source_drift_detected"] is True
    assert "src/comprova_lattes/matcher/rules.py" in volatile["changed_sources_during_collection"]


def test_no_secrets_no_settings_no_absolute_env_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "GEMINI_API_KEY=SUPER_SECRET_DOTENV_KEY\n"
        "DATABASE_URL=postgresql://admin:super_secret_pw@db.internal/app\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GEMINI_API_KEY", "SUPER_SECRET_ENV_KEY")
    monkeypatch.setenv("TESSERACT_CMD", str(tmp_path / "secret_user_dir" / "tesseract.exe"))

    acronyms_dir = tmp_path / "user_secret_dir"
    acronyms_dir.mkdir(parents=True, exist_ok=True)
    acronyms_file = _write_sample_acronyms(acronyms_dir / "siglas.json")

    leaky_ocr = lambda: {
        "engine": "tesseract",
        "available": True,
        "executable": r"C:\Users\Caleb\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
        "tesseract_version": "tesseract v5.4.0",
        "language": "por",
        "language_available": True,
        "available_languages": ["eng", "por"],
        "tessdata_dir": r"C:\Users\Caleb\tessdata",
        "dpi": 300,
        "pdf_render_scale": 300 / 72.0,
        "timeout_seconds": 30.0,
        "max_pdf_pages": 10,
        "max_image_pixels": 25_000_000,
        "supported_mime_types": ["application/pdf", "image/jpeg", "image/png"],
        "pdf_conversion_library": "pypdfium2",
        "pypdfium2_version": "5.0.0",
        "pdfium_version": "130",
        "pillow_version": "13.0.0",
        "pdf_text_extraction": "disabled_raster_only",
        "error": r"Aviso em 'C:\Users\Caleb\Desktop\algo.txt' ignorado",
        "limitations": [],
    }

    out_dir = tmp_path / "artifacts_out"
    result = collect_artifacts(
        output_dir=out_dir,
        acronyms_path=acronyms_file,
        ocr_probe=leaky_ocr,
    )

    forbidden_substrings = [
        "SUPER_SECRET_DOTENV_KEY",
        "SUPER_SECRET_ENV_KEY",
        "super_secret_pw",
        "secret_user_dir",
        "user_secret_dir",
        str(Path.home()),
        str(tmp_path),
        sys.executable,
        r"C:\Users\Caleb",
    ]
    files_to_audit = [Path(p) for p in result["artifacts_map"].values()] + [result["report_file"]]
    for file_path in files_to_audit:
        content = file_path.read_text(encoding="utf-8")
        for token in forbidden_substrings:
            assert token not in content, f"Token proibido {token!r} vazou em {file_path.name}"

    env_json = json.loads(Path(result["artifacts_map"]["environment"]).read_text(encoding="utf-8"))
    assert "executable" not in env_json["tesseract"]
    assert "tessdata_dir" not in env_json["tesseract"]
    assert env_json["tesseract"]["executable_detected"] is True
    assert env_json["tesseract"]["tessdata_dir_configured"] is True
    assert env_json["tesseract"]["status"] == "available"
    assert env_json["collection_policy"]["settings_loaded"] is False


def test_unavailable_pillow_and_tesseract_documented_without_network(tmp_path, monkeypatch):
    import comprova_lattes.experiments.render as render_mod

    monkeypatch.setattr(
        render_mod,
        "rasterizer_metadata",
        lambda: (_ for _ in ()).throw(RuntimeError("Pillow ausente")),
    )
    acronyms_file = _write_sample_acronyms(tmp_path / "acronyms.json")
    result = collect_artifacts(
        output_dir=tmp_path / "out",
        acronyms_path=acronyms_file,
        ocr_probe=lambda: {
            "engine": "tesseract",
            "available": False,
            "executable": None,
            "language": "por",
            "language_available": False,
            "error": "tesseract não instalado",
        },
    )

    env_data = json.loads(Path(result["artifacts_map"]["environment"]).read_text(encoding="utf-8"))
    assert env_data["pillow_freetype"]["status"] == "unavailable"
    assert env_data["pillow_freetype"]["available"] is False
    assert env_data["tesseract"]["status"] == "unavailable"
    assert env_data["tesseract"]["available"] is False
    assert result["report"]["stable_identity"]["pillow_status"] == "unavailable"
    assert result["report"]["stable_identity"]["tesseract_status"] == "unavailable"


def test_rejects_corpus_or_invalid_acronyms_file(tmp_path):
    bad_corpus = tmp_path / "corpus.json"
    bad_corpus.write_text(json.dumps({"seed": 42, "cases": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="corpus"):
        collect_artifacts(output_dir=tmp_path / "out1", acronyms_path=bad_corpus)

    bad_type = tmp_path / "list.json"
    bad_type.write_text(json.dumps(["a", "b"]), encoding="utf-8")
    with pytest.raises(TypeError):
        collect_artifacts(output_dir=tmp_path / "out2", acronyms_path=bad_type)


def test_cli_module_execution_does_not_load_settings_or_freeze(tmp_path, capsys):
    acronyms_file = _write_sample_acronyms(tmp_path / "acronyms.json")
    out_dir = tmp_path / "cli_out"

    exit_code = main(
        [
            "--output-dir",
            str(out_dir),
            "--acronyms",
            str(acronyms_file),
            "--model",
            "gemini-3.5-flash-lite",
        ]
    )
    assert exit_code == 0
    stdout_payload = json.loads(capsys.readouterr().out)
    assert stdout_payload["frozen"] is False
    assert set(cli_read(Path(stdout_payload["artifacts_file"]))) == set(REQUIRED_ARTIFACTS)

    # Execução em subprocesso isolado comprova que config/Settings/.env e google.genai não carregam.
    (tmp_path / ".env").write_text("GEMINI_API_KEY=SUBPROCESS_SECRET_KEY\n", encoding="utf-8")
    sub_out = tmp_path / "sub_out"
    api_dir = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(api_dir / "src"), str(api_dir / ".venv" / "Lib" / "site-packages")]
    )
    probe_script = (
        "import sys; "
        "from comprova_lattes.experiments.artifacts import main; "
        f"rc = main(['--output-dir', {str(sub_out)!r}, '--acronyms', {str(acronyms_file)!r}]); "
        "assert rc == 0; "
        "assert 'comprova_lattes.config' not in sys.modules; "
        "assert 'google.genai' not in sys.modules; "
        "assert 'comprova_lattes.extractor.gemini' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe_script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr

    cli_out = tmp_path / "module_cli_out"
    cli_proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "comprova_lattes.experiments.artifacts",
            "--output-dir",
            str(cli_out),
            "--acronyms",
            str(acronyms_file),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert cli_proc.returncode == 0, cli_proc.stderr
    cli_summary = json.loads(cli_proc.stdout)
    assert cli_summary["frozen"] is False
    assert set(cli_read(Path(cli_summary["artifacts_file"]))) == set(REQUIRED_ARTIFACTS)
