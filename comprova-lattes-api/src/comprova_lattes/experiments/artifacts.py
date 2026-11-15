"""Preparador offline de artefatos canônicos e artifacts.json sem executar freeze."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import importlib.util
import json
import platform
import re
import subprocess
import sys
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from comprova_lattes.experiments import baseline, render, synthetic
from comprova_lattes.experiments.freeze import canonical, sha256
from comprova_lattes.experiments.ocr import TesseractOCR
from comprova_lattes.matcher.models import ExtractedDocumentRecord
from comprova_lattes.matcher.text import _ROLES

DEFAULT_EXPERIMENTAL_MODEL = "gemini-3.5-flash-lite"

REQUIRED_ARTIFACTS: tuple[str, ...] = (
    "schema",
    "prompt",
    "regex",
    "acronyms",
    "normalization",
    "generator",
    "code",
    "environment",
)

EXPLICIT_CODE_SCOPE: tuple[str, ...] = (
    "__init__.py",
    "experiments/__init__.py",
    "experiments/__main__.py",
    "experiments/artifacts.py",
    "experiments/baseline.py",
    "experiments/freeze.py",
    "experiments/ocr.py",
    "experiments/render.py",
    "experiments/runner.py",
    "experiments/reporting.py",
    "experiments/statistics.py",
    "experiments/synthetic.py",
    "extractor/__init__.py",
    "extractor/gemini.py",
    "extractor/models.py",
    "matcher/__init__.py",
    "matcher/association.py",
    "matcher/engine.py",
    "matcher/models.py",
    "matcher/rules.py",
    "matcher/text.py",
    "parser/__init__.py",
    "parser/exceptions.py",
    "parser/mappings.py",
    "parser/xml_parser.py",
    "schemas/__init__.py",
    "schemas/lattes.py",
)

_DISALLOWED_ACRONYM_KEYS = frozenset({"cases", "records", "annotations", "payload", "manifest"})
_ALLOWED_WRAPPER_KEYS = frozenset({"acronym_table", "acronyms", "version", "acronym_table_version"})
_PATH_REDACTION_RE = re.compile(
    r"['\"][A-Za-z]:[\\/][^'\"]+['\"]"
    r"|[A-Za-z]:[\\/][^\s'\"()]+"
    r"|/(?:home|Users|tmp|var|opt|usr|etc|mnt|app)(?:/[^\s'\"()]*)+"
)
_GEMINI_MODEL_RE = re.compile(r"(?:models/)?gemini-(\d+)(?:\.(\d+))?-.*")


@dataclass(frozen=True)
class SourceSnapshot:
    """Instantâneo imutável de arquivo fonte usando apenas caminho relativo."""

    relative_path: str
    sha256: str
    size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.relative_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


def _default_source_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _supports_temperature(model: str) -> bool:
    match = _GEMINI_MODEL_RE.fullmatch(model)
    if not match:
        return False
    return int(match[1]) < 3


def _sanitize_text(text: str | None) -> str | None:
    if text is None:
        return None
    return _PATH_REDACTION_RE.sub("<redacted-path>", text)


def _hash_file(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def _snapshot_sources(
    source_root: Path,
    acronyms_path: Path,
) -> tuple[dict[str, SourceSnapshot], SourceSnapshot | None, tuple[str, int]]:
    snapshots: dict[str, SourceSnapshot] = {}
    for rel_path in EXPLICIT_CODE_SCOPE:
        full_path = source_root / rel_path
        if not full_path.is_file():
            raise FileNotFoundError(
                f"Arquivo obrigatório do escopo explícito ausente: src/comprova_lattes/{rel_path}"
            )
        digest, size_bytes = _hash_file(full_path)
        logical_path = f"src/comprova_lattes/{rel_path}"
        snapshots[logical_path] = SourceSnapshot(
            relative_path=logical_path,
            sha256=digest,
            size_bytes=size_bytes,
        )

    pyproject_snapshot: SourceSnapshot | None = None
    pyproject_path = source_root.parent.parent / "pyproject.toml"
    if pyproject_path.is_file():
        digest, size_bytes = _hash_file(pyproject_path)
        pyproject_snapshot = SourceSnapshot(
            relative_path="pyproject.toml",
            sha256=digest,
            size_bytes=size_bytes,
        )

    if not acronyms_path.is_file():
        raise FileNotFoundError(f"Arquivo de siglas explícito não encontrado: {acronyms_path.name}")
    acronyms_digest = _hash_file(acronyms_path)
    return snapshots, pyproject_snapshot, acronyms_digest


def _detect_source_drift(
    source_root: Path,
    acronyms_path: Path,
    initial_snapshots: dict[str, SourceSnapshot],
    initial_pyproject: SourceSnapshot | None,
    initial_acronyms: tuple[str, int],
) -> list[str]:
    changed: list[str] = []
    for rel_path in EXPLICIT_CODE_SCOPE:
        logical_path = f"src/comprova_lattes/{rel_path}"
        full_path = source_root / rel_path
        expected = initial_snapshots[logical_path]
        if not full_path.is_file():
            changed.append(logical_path)
            continue
        digest, size_bytes = _hash_file(full_path)
        if (digest, size_bytes) != (expected.sha256, expected.size_bytes):
            changed.append(logical_path)

    if initial_pyproject is not None:
        pyproject_path = source_root.parent.parent / "pyproject.toml"
        if not pyproject_path.is_file():
            changed.append("pyproject.toml")
        else:
            digest, size_bytes = _hash_file(pyproject_path)
            if (digest, size_bytes) != (initial_pyproject.sha256, initial_pyproject.size_bytes):
                changed.append("pyproject.toml")

    if not acronyms_path.is_file() or _hash_file(acronyms_path) != initial_acronyms:
        changed.append(f"acronyms:{acronyms_path.name}")

    return sorted(changed)


def _load_extraction_payload_schema(models_path: Path) -> dict[str, Any]:
    """Carrega ExtractionPayload isoladamente sem importar extractor.__init__ ou config."""
    module_name = "comprova_lattes._isolated_extractor_models"
    spec = importlib.util.spec_from_file_location(module_name, models_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Não foi possível carregar extractor/models.py para extrair JSON Schema")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        payload_cls = getattr(module, "ExtractionPayload", None)
        if payload_cls is None:
            raise RuntimeError("ExtractionPayload não encontrado em extractor/models.py")
        return payload_cls.model_json_schema()
    finally:
        sys.modules.pop(module_name, None)


def _extract_gemini_prompt_constants(gemini_path: Path) -> dict[str, Any]:
    """Extrai PROMPT, PROMPT_VERSION e SUPPORTED_MIME_TYPES via AST sem carregar Settings/.env."""
    tree = ast.parse(gemini_path.read_text(encoding="utf-8"), filename="extractor/gemini.py")
    extracted: dict[str, Any] = {}
    targets = {"PROMPT_VERSION", "PROMPT", "SUPPORTED_MIME_TYPES"}

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name) or target.id not in targets:
                continue
            name = target.id
            if name in {"PROMPT_VERSION", "PROMPT"}:
                value = ast.literal_eval(node.value)
                if not isinstance(value, str):
                    raise ValueError(f"{name} deve ser str em extractor/gemini.py")
                extracted[name] = value
            elif name == "SUPPORTED_MIME_TYPES":
                if (
                    isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "frozenset"
                    and len(node.value.args) == 1
                ):
                    raw_items = ast.literal_eval(node.value.args[0])
                    extracted[name] = sorted(str(item) for item in raw_items)
                else:
                    raw_items = ast.literal_eval(node.value)
                    extracted[name] = sorted(str(item) for item in raw_items)

    missing = targets - set(extracted)
    if missing:
        raise RuntimeError(
            f"Constantes ausentes em extractor/gemini.py: {', '.join(sorted(missing))}"
        )
    return extracted


def _load_explicit_acronyms(acronyms_path: Path, version_override: str | None) -> dict[str, Any]:
    raw_bytes = acronyms_path.read_bytes()
    try:
        parsed = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Arquivo de siglas inválido ({acronyms_path.name}): {exc}") from exc

    if not isinstance(parsed, dict):
        raise TypeError("Arquivo de siglas deve ser um objeto JSON")

    disallowed_present = _DISALLOWED_ACRONYM_KEYS & set(parsed)
    if disallowed_present:
        raise ValueError(
            "Arquivo de siglas não pode conter estrutura de corpus/anotações/manifesto: "
            f"{sorted(disallowed_present)}"
        )

    version: str | None = version_override
    raw_table: Any
    if "acronym_table" in parsed or "acronyms" in parsed:
        unexpected = set(parsed) - _ALLOWED_WRAPPER_KEYS
        if unexpected:
            raise ValueError(f"Chaves não reconhecidas no arquivo de siglas: {sorted(unexpected)}")
        if "acronym_table" in parsed and "acronyms" in parsed:
            raise ValueError("Informe apenas 'acronym_table' ou 'acronyms', não ambos")
        raw_table = parsed.get("acronym_table", parsed.get("acronyms"))
        if version is None:
            raw_ver = parsed.get("acronym_table_version", parsed.get("version"))
            if raw_ver is not None:
                if not isinstance(raw_ver, str) or not raw_ver.strip():
                    raise ValueError("Versão da tabela de siglas deve ser string não vazia")
                version = raw_ver.strip()
    else:
        raw_table = parsed

    if not isinstance(raw_table, dict):
        raise TypeError("Tabela de siglas deve ser um mapeamento JSON chave -> valor")

    normalized_table: dict[str, str] = {}
    for key, value in raw_table.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Cada sigla no dicionário explícito deve ser string não vazia")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Expansão da sigla {key!r} deve ser string não vazia"
            )
        normalized_table[key.strip()] = value.strip()

    final_version = version.strip() if version and version.strip() else "explicit-file"
    return {
        "artifact": "acronyms",
        "source_filename": acronyms_path.name,
        "source_policy": "explicit_user_file_never_derived_from_final_corpus",
        "input_sha256": sha256(raw_bytes),
        "version": final_version,
        "entry_count": len(normalized_table),
        "acronym_table": dict(sorted(normalized_table.items())),
    }


def _collect_packages() -> dict[str, str]:
    entries: list[tuple[str, str]] = []
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name") if dist.metadata else None
        pkg_name = (name or getattr(dist, "name", "") or "").strip().lower()
        if not pkg_name:
            continue
        entries.append((pkg_name, str(dist.version)))
    packages: dict[str, str] = {}
    for pkg_name, version in sorted(entries):
        if pkg_name not in packages:
            packages[pkg_name] = version
    return packages


def _collect_pillow_environment() -> dict[str, Any]:
    try:
        meta = render.rasterizer_metadata()
    except (ImportError, RuntimeError, OSError) as exc:
        return {
            "status": "unavailable",
            "available": False,
            "pillow_dependency": render.PILLOW_DEPENDENCY,
            "pillow_version": None,
            "freetype_available": False,
            "freetype_version": None,
            "reason": _sanitize_text(str(exc)) or type(exc).__name__,
        }
    return {
        "status": "available",
        "available": True,
        **meta,
    }


def _collect_tesseract_environment(
    ocr_probe: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    probe = ocr_probe if ocr_probe is not None else (lambda: TesseractOCR().metadata())
    try:
        raw = probe()
    except (
        OSError,
        subprocess.SubprocessError,
        ImportError,
        RuntimeError,
        ValueError,
        TypeError,
    ) as exc:
        return {
            "engine": "tesseract",
            "status": "unavailable",
            "available": False,
            "error": _sanitize_text(str(exc)) or type(exc).__name__,
        }

    available = bool(raw.get("available"))
    return {
        "engine": raw.get("engine", "tesseract"),
        "status": "available" if available else "unavailable",
        "available": available,
        "executable_detected": bool(raw.get("executable")),
        "tesseract_version": _sanitize_text(raw.get("tesseract_version")),
        "language": raw.get("language"),
        "language_available": bool(raw.get("language_available")),
        "available_languages": sorted(str(lang) for lang in raw.get("available_languages", [])),
        "tessdata_dir_configured": raw.get("tessdata_dir") is not None,
        "dpi": raw.get("dpi"),
        "pdf_render_scale": raw.get("pdf_render_scale"),
        "timeout_seconds": raw.get("timeout_seconds"),
        "max_pdf_pages": raw.get("max_pdf_pages"),
        "max_image_pixels": raw.get("max_image_pixels"),
        "supported_mime_types": sorted(str(m) for m in raw.get("supported_mime_types", [])),
        "pdf_conversion_library": raw.get("pdf_conversion_library"),
        "pypdfium2_version": raw.get("pypdfium2_version"),
        "pdfium_version": raw.get("pdfium_version"),
        "pillow_version": raw.get("pillow_version"),
        "pdf_text_extraction": raw.get("pdf_text_extraction"),
        "error": _sanitize_text(raw.get("error")),
        "limitations": [str(item) for item in raw.get("limitations", [])],
    }


def _build_artifacts_payloads(
    *,
    source_root: Path,
    snapshots: dict[str, SourceSnapshot],
    pyproject_snapshot: SourceSnapshot | None,
    acronyms_payload: dict[str, Any],
    experimental_model: str,
    ocr_probe: Callable[[], dict[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    def file_entries(*logical_paths: str) -> list[dict[str, Any]]:
        return [snapshots[p].to_dict() for p in sorted(logical_paths)]

    gemini_constants = _extract_gemini_prompt_constants(source_root / "extractor" / "gemini.py")
    temp_supported = _supports_temperature(experimental_model)

    schema_artifact = {
        "artifact": "schema",
        "extractor_payload_model": "comprova_lattes.extractor.models.ExtractionPayload",
        "extracted_record_model": "comprova_lattes.matcher.models.ExtractedDocumentRecord",
        "json_schema": _load_extraction_payload_schema(source_root / "extractor" / "models.py"),
        "extracted_record_json_schema": ExtractedDocumentRecord.model_json_schema(),
        "source_files": file_entries(
            "src/comprova_lattes/extractor/models.py",
            "src/comprova_lattes/matcher/models.py",
        ),
    }

    prompt_artifact = {
        "artifact": "prompt",
        "prompt_version": gemini_constants["PROMPT_VERSION"],
        "prompt": gemini_constants["PROMPT"],
        "strategy": "zero-shot",
        "response_mime_type": "application/json",
        "supported_mime_types": gemini_constants["SUPPORTED_MIME_TYPES"],
        "experimental_model": experimental_model,
        "supports_temperature": temp_supported,
        "temperature": 0.0 if temp_supported else None,
        "temperature_policy": "fixed_zero" if temp_supported else "provider_default",
        "source_files": file_entries("src/comprova_lattes/extractor/gemini.py"),
    }

    regex_artifact = {
        "artifact": "regex",
        "fields": list(baseline.FIELDS),
        "field_labels_pt": dict(baseline.FIELD_LABELS_PT),
        "patterns": dict(baseline.PATTERNS),
        "flags": ["MULTILINE", "IGNORECASE"],
        "source_files": file_entries("src/comprova_lattes/experiments/baseline.py"),
    }

    normalization_artifact = {
        "artifact": "normalization",
        "empty_string_guard": True,
        "similarity_metrics": ["LEVENSHTEIN_NORM", "JARO_WINKLER", "TOKEN_HYBRID"],
        "roles_mapping": dict(sorted(_ROLES.items())),
        "source_files": file_entries("src/comprova_lattes/matcher/text.py"),
    }

    generator_artifact = {
        "artifact": "generator",
        "template_provenance": dict(synthetic.TEMPLATE_PROVENANCE),
        "synthetic_acronyms_radicals": dict(synthetic.SYNTHETIC_ACRONYMS),
        "field_labels": dict(synthetic.FIELD_LABELS),
        "category_order": [str(c) for c in synthetic.CATEGORY_ORDER],
        "category_templates": {
            str(k): list(v) for k, v in synthetic.CATEGORY_TEMPLATES.items()
        },
        "default_template": list(synthetic.DEFAULT_TEMPLATE),
        "rasterizer_version": render.RASTERIZER_VERSION,
        "pillow_dependency": render.PILLOW_DEPENDENCY,
        "supported_chars_count": len(render.SUPPORTED_CHARS),
        "supported_chars_sha256": sha256(canonical(sorted(render.SUPPORTED_CHARS))),
        "source_files": file_entries(
            "src/comprova_lattes/experiments/synthetic.py",
            "src/comprova_lattes/experiments/render.py",
        ),
    }

    code_artifact = {
        "artifact": "code",
        "scope_policy": "explicit_allowlist_no_env_or_corpus_or_git_diff",
        "git_diff_included": False,
        "excluded_from_scope": [
            "config.py",
            ".env*",
            "api/*",
            "worker.py",
            "tests/*",
            "data/*",
            "corpus*",
            "annotations/*",
            "outputs/*",
        ],
        "files": [snapshots[key].to_dict() for key in sorted(snapshots)],
        "pyproject_toml": pyproject_snapshot.to_dict() if pyproject_snapshot else None,
    }

    environment_artifact = {
        "artifact": "environment",
        "python": {
            "version": platform.python_version(),
            "version_info": [
                sys.version_info.major,
                sys.version_info.minor,
                sys.version_info.micro,
            ],
            "implementation": platform.python_implementation(),
            "platform_system": platform.system(),
            "platform_machine": platform.machine(),
        },
        "packages": _collect_packages(),
        "pillow_freetype": _collect_pillow_environment(),
        "tesseract": _collect_tesseract_environment(ocr_probe=ocr_probe),
        "collection_policy": {
            "network_used": False,
            "auto_install_attempted": False,
            "settings_loaded": False,
            "env_vars_dumped": False,
            "pip_config_read": False,
            "process_args_dumped": False,
        },
    }

    return {
        "schema": schema_artifact,
        "prompt": prompt_artifact,
        "regex": regex_artifact,
        "acronyms": acronyms_payload,
        "normalization": normalization_artifact,
        "generator": generator_artifact,
        "code": code_artifact,
        "environment": environment_artifact,
    }


def collect_artifacts(
    *,
    output_dir: Path,
    acronyms_path: Path,
    acronyms_version: str | None = None,
    experimental_model: str = DEFAULT_EXPERIMENTAL_MODEL,
    artifacts_file: Path | None = None,
    report_file: Path | None = None,
    source_root: Path | None = None,
    ocr_probe: Callable[[], dict[str, Any]] | None = None,
    post_write_hook: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Prepara artefatos canônicos e artifacts.json sem executar freeze ou ler corpus."""
    if not isinstance(experimental_model, str) or not experimental_model.strip():
        raise ValueError("Modelo experimental deve ser string não vazia.")
    model = experimental_model.strip()

    resolved_source_root = source_root if source_root is not None else _default_source_root()
    initial_snapshots, initial_pyproject, initial_acronyms = _snapshot_sources(
        resolved_source_root, acronyms_path
    )
    acronyms_payload = _load_explicit_acronyms(acronyms_path, acronyms_version)
    payloads = _build_artifacts_payloads(
        source_root=resolved_source_root,
        snapshots=initial_snapshots,
        pyproject_snapshot=initial_pyproject,
        acronyms_payload=acronyms_payload,
        experimental_model=model,
        ocr_probe=ocr_probe,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts_map: dict[str, str] = {}
    artifacts_sha256: dict[str, str] = {}

    for name in REQUIRED_ARTIFACTS:
        artifact_bytes = canonical(payloads[name])
        artifact_path = output_dir / f"{name}.json"
        artifact_path.write_bytes(artifact_bytes)
        artifacts_map[name] = artifact_path.as_posix()
        artifacts_sha256[name] = sha256(artifact_bytes)

    resolved_artifacts_file = (
        artifacts_file if artifacts_file is not None else output_dir / "artifacts.json"
    )
    resolved_artifacts_file.parent.mkdir(parents=True, exist_ok=True)
    resolved_artifacts_file.write_text(
        json.dumps(artifacts_map, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    if post_write_hook is not None:
        post_write_hook()

    changed_sources = _detect_source_drift(
        resolved_source_root,
        acronyms_path,
        initial_snapshots,
        initial_pyproject,
        initial_acronyms,
    )
    drift_detected = bool(changed_sources)

    warnings_list: list[str] = []
    if drift_detected:
        msg = (
            "Arquivos fonte foram modificados entre a leitura inicial e o fim da coleta: "
            + ", ".join(changed_sources)
        )
        warnings_list.append(msg)
        warnings.warn(msg, RuntimeWarning, stacklevel=2)

    if payloads["generator"]["template_provenance"].get("human_approval_required_before_freeze"):
        warnings_list.append(
            "Templates em português estão em status draft_pending_human_validation e exigem "
            "aprovação humana explícita antes do freeze oficial."
        )

    source_inventory = [initial_snapshots[k].to_dict() for k in sorted(initial_snapshots)]
    if initial_pyproject is not None:
        source_inventory.append(initial_pyproject.to_dict())

    env_payload = payloads["environment"]
    stable_identity = {
        "artifacts_sha256": artifacts_sha256,
        "bundle_sha256": sha256(canonical(artifacts_sha256)),
        "source_inventory": source_inventory,
        "acronyms_input": {
            "filename": acronyms_payload["source_filename"],
            "sha256": acronyms_payload["input_sha256"],
            "version": acronyms_payload["version"],
            "entry_count": acronyms_payload["entry_count"],
        },
        "experimental_model": model,
        "prompt_version": payloads["prompt"]["prompt_version"],
        "rasterizer_version": payloads["generator"]["rasterizer_version"],
        "template_provenance_status": payloads["generator"]["template_provenance"]["status"],
        "pillow_status": env_payload["pillow_freetype"]["status"],
        "tesseract_status": env_payload["tesseract"]["status"],
    }

    report = {
        "format_version": 1,
        "frozen": False,
        "freeze_status": "prepared_not_frozen",
        "stable_identity": stable_identity,
        "volatile_metadata": {
            "collected_at_utc": datetime.now(UTC).isoformat(),
            "source_drift_detected": drift_detected,
            "changed_sources_during_collection": changed_sources,
            "warnings": warnings_list,
        },
    }

    resolved_report_file = (
        report_file if report_file is not None else output_dir / "collection-report.json"
    )
    resolved_report_file.parent.mkdir(parents=True, exist_ok=True)
    resolved_report_file.write_text(
        json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    return {
        "artifacts_map": artifacts_map,
        "artifacts_file": resolved_artifacts_file,
        "report_file": resolved_report_file,
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI offline para preparar artifacts.json e artefatos canônicos pré-freeze."""
    parser = argparse.ArgumentParser(
        description=(
            "Prepara artefatos canônicos determinísticos e artifacts.json compatível com "
            "python -m comprova_lattes.experiments freeze/exp1/exp2/exp3 (sem congelar)."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Diretório destino explícito para os arquivos artefatos e artifacts.json.",
    )
    parser.add_argument(
        "--acronyms",
        type=Path,
        required=True,
        help="Arquivo JSON explícito com dicionário de siglas fornecido pelo usuário.",
    )
    parser.add_argument(
        "--acronyms-version",
        default=None,
        help="Versão explícita opcional da tabela de siglas.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_EXPERIMENTAL_MODEL,
        help=f"Modelo experimental explícito para metadados (padrão: {DEFAULT_EXPERIMENTAL_MODEL}).",
    )
    parser.add_argument(
        "--artifacts-file",
        type=Path,
        default=None,
        help="Caminho alternativo para artifacts.json (padrão: <output-dir>/artifacts.json).",
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=None,
        help=(
            "Caminho alternativo para collection-report.json "
            "(padrão: <output-dir>/collection-report.json)."
        ),
    )
    args = parser.parse_args(argv)

    result = collect_artifacts(
        output_dir=args.output_dir,
        acronyms_path=args.acronyms,
        acronyms_version=args.acronyms_version,
        experimental_model=args.model,
        artifacts_file=args.artifacts_file,
        report_file=args.report_file,
    )
    report = result["report"]
    if report["volatile_metadata"]["source_drift_detected"]:
        for warning in report["volatile_metadata"]["warnings"]:
            print(f"AVISO: {warning}", file=sys.stderr)

    summary = {
        "frozen": report["frozen"],
        "freeze_status": report["freeze_status"],
        "artifacts_file": result["artifacts_file"].as_posix(),
        "report_file": result["report_file"].as_posix(),
        "stable_identity": report["stable_identity"],
        "volatile_metadata": report["volatile_metadata"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
