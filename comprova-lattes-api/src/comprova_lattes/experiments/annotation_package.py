"""Exportador offline do pacote sanitizado de anotação humana (somente partição piloto).

Lê um Corpus existente indicado explicitamente e escreve um pacote JSON público para a
interface local ``/revisao-experimental``. Não chama Gemini, API, banco nem fila, e não
executa generate/calibrate/freeze. O pacote nunca contém gabarito, operador, classe esperada,
identidades de família/template/emissor nem os IDs originais dos casos.

Ver ``.specs/docs/human-annotation.md`` para formato, hash e limites.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from comprova_lattes.schemas.lattes import LattesCategory

from .freeze import canonical
from .synthetic import CATEGORY_ORDER, Case, Corpus

PACKAGE_VERSION = "annotation-package-v1"
# Rótulo do guia operacional vigente (rascunho; não implica aprovação humana do guia).
GUIDE_VERSION = "operational-guide-draft-v1"
PRIVATE_MAP_VERSION = "annotation-private-map-v1"
PILOT_CASE_COUNT = len(CATEGORY_ORDER)

# Rotação preferida de operadores por categoria, para variar operadores entre os cinco casos.
_OPERATOR_ROTATION = ("identity", "legitimate", "factual_mutation", "omission", "no_document")

ALLOWED_MIME_TYPES = frozenset({"application/pdf", "image/png", "image/jpeg"})
NEUTRAL_ID_PATTERN = re.compile(r"^case-\d{3,}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

# Chaves que jamais podem aparecer em um pacote público (em qualquer nível).
FORBIDDEN_KEYS = frozenset(
    {
        "gold",
        "expected",
        "operator",
        "family_id",
        "template_id",
        "issuer_id",
        "partition",
        "degradation",
        "seed",
        "curriculum",
        "raw_metadata",
        "confianca_extracao",
        "categoria_sugerida",
        "extraction_status",
        "similarity_score",
        "association_score",
        "match_status",
        "thresholds",
        "field_evidences",
        "reason_code",
        "diagnostics",
    }
)


class PackageError(ValueError):
    """Pacote inválido ou inseguro para publicação aos anotadores."""


class _Public(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PublicDocument(_Public):
    mime_type: str
    sha256: str
    content_base64: str


class PublicXml(_Public):
    sha256: str
    content_base64: str


class PublicRecord(_Public):
    """Registro curricular estruturado necessário à comparação (sem proveniência técnica)."""

    record_id: str | None
    category: LattesCategory
    subtype: str | None
    sequence: str | None
    holder_name: str | None
    institution: str | None
    institution_acronym: str | None
    title: str | None
    event_name: str | None
    city: str | None
    location: str | None
    start_year: int | None
    end_year: int | None
    workload_hours: str | None
    status: str | None
    validation_code: str | None
    nature_raw: str | None
    participation_type_raw: str | None
    participation_form_raw: str | None
    participation_role: str | None


class PublicCase(_Public):
    case_id: str
    document: PublicDocument | None
    xml: PublicXml
    record: PublicRecord


class AnnotationPackage(_Public):
    package_version: Literal["annotation-package-v1"]
    guide_version: str
    package_sha256: str
    cases: tuple[PublicCase, ...]


@dataclass(frozen=True)
class BuiltPackage:
    """Pacote público + mapa privado (neutral_id -> case_id original); nunca juntos em disco."""

    package: dict[str, Any]
    private_map: dict[str, Any]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def compute_package_sha256(payload: Mapping[str, Any]) -> str:
    """Hash do JSON canônico (ASCII, chaves ordenadas) sem o campo ``package_sha256``."""
    body = {key: value for key, value in payload.items() if key != "package_sha256"}
    return _sha256(canonical(body))


def _scan_forbidden_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                raise PackageError(f"Chave proibida em pacote público: {path}.{key}")
            _scan_forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _scan_forbidden_keys(child, f"{path}[{index}]")


def _sniff_matches(mime_type: str, data: bytes) -> bool:
    if mime_type == "application/pdf":
        return data.startswith(b"%PDF-")
    if mime_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    return False


def _decode_checked(content_base64: str, expected_sha256: str, label: str) -> bytes:
    if not _SHA256_PATTERN.fullmatch(expected_sha256):
        raise PackageError(f"{label}: hash SHA-256 malformado")
    try:
        data = base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise PackageError(f"{label}: base64 inválido") from exc
    if _sha256(data) != expected_sha256:
        raise PackageError(f"{label}: hash não confere com os bytes")
    return data


def validate_package(raw: Mapping[str, Any]) -> AnnotationPackage:
    """Valida esquema, chaves proibidas, IDs neutros, MIME, hashes e hash do pacote."""
    if not isinstance(raw, Mapping):
        raise PackageError("Pacote deve ser um objeto JSON")
    _scan_forbidden_keys(raw)
    try:
        package = AnnotationPackage.model_validate(raw)
    except ValidationError as exc:
        raise PackageError(f"Esquema inválido: {exc.error_count()} erro(s): {exc}") from exc
    if not _SHA256_PATTERN.fullmatch(package.package_sha256):
        raise PackageError("package_sha256 malformado")
    if not package.cases:
        raise PackageError("Pacote sem casos")
    seen: set[str] = set()
    for case in package.cases:
        if not NEUTRAL_ID_PATTERN.fullmatch(case.case_id):
            raise PackageError(f"case_id não neutro: {case.case_id!r}")
        if case.case_id in seen:
            raise PackageError(f"case_id duplicado: {case.case_id}")
        seen.add(case.case_id)
        _decode_checked(case.xml.content_base64, case.xml.sha256, f"{case.case_id} xml")
        if case.document is not None:
            if case.document.mime_type not in ALLOWED_MIME_TYPES:
                raise PackageError(f"{case.case_id}: MIME não permitido")
            data = _decode_checked(
                case.document.content_base64, case.document.sha256, f"{case.case_id} documento"
            )
            if not _sniff_matches(case.document.mime_type, data):
                raise PackageError(f"{case.case_id}: bytes não correspondem ao MIME declarado")
    if compute_package_sha256(raw) != package.package_sha256:
        raise PackageError("package_sha256 não confere com o conteúdo")
    return package


def select_pilot_cases(corpus: Corpus) -> tuple[Case, ...]:
    """Cinco casos piloto: uma categoria cada, operadores variados e famílias distintas."""
    pilot = corpus.select("pilot")
    chosen: list[Case] = []
    for rank, category in enumerate(CATEGORY_ORDER):
        preferred = _OPERATOR_ROTATION[rank % len(_OPERATOR_ROTATION)]
        used_families = {c.family_id for c in chosen}
        used_operators = {c.operator for c in chosen}
        candidates = [
            c
            for c in pilot
            if len(c.curriculum.records) == 1
            and c.curriculum.records[0].category == category
            and c.family_id not in used_families
        ]
        if not candidates:
            raise PackageError("Piloto sem cobertura das cinco categorias em famílias distintas")
        candidates.sort(key=lambda c: (c.operator != preferred, c.operator in used_operators))
        chosen.append(candidates[0])
    return tuple(chosen)


def _public_record(case: Case) -> dict[str, Any]:
    record = case.curriculum.records[0]
    data = {name: getattr(record, name) for name in PublicRecord.model_fields}
    data["category"] = record.category.value
    data["status"] = record.status.value if record.status is not None else None
    if record.workload_hours is not None:
        data["workload_hours"] = str(record.workload_hours)
    return data


def _public_case(neutral_id: str, case: Case) -> dict[str, Any]:
    document = None
    if case.document is not None:
        document = {
            "mime_type": case.mime_type,
            "sha256": _sha256(case.document),
            "content_base64": _b64(case.document),
        }
    return {
        "case_id": neutral_id,
        "document": document,
        "xml": {"sha256": _sha256(case.xml), "content_base64": _b64(case.xml)},
        "record": _public_record(case),
    }


def build_package(corpus: Corpus, *, guide_version: str = GUIDE_VERSION) -> BuiltPackage:
    """Constrói o pacote piloto sanitizado. Somente a partição piloto é considerada."""
    if not guide_version.strip():
        raise PackageError("guide_version obrigatório")
    selected = select_pilot_cases(corpus)
    ordered = sorted(
        selected,
        key=lambda c: _sha256(f"{corpus.seed}:annotation-order:{c.case_id}".encode()),
    )
    neutral_ids = {c.case_id: f"case-{index:03d}" for index, c in enumerate(ordered, start=1)}
    payload: dict[str, Any] = {
        "package_version": PACKAGE_VERSION,
        "guide_version": guide_version.strip(),
        "cases": [_public_case(neutral_ids[c.case_id], c) for c in ordered],
    }
    payload["package_sha256"] = compute_package_sha256(payload)
    _assert_no_leak(payload, ordered)
    validate_package(payload)
    private_map = {
        "private_map_version": PRIVATE_MAP_VERSION,
        "package_sha256": payload["package_sha256"],
        "cases": {neutral_ids[c.case_id]: c.case_id for c in ordered},
    }
    return BuiltPackage(package=payload, private_map=private_map)


def _assert_no_leak(payload: Mapping[str, Any], cases: tuple[Case, ...]) -> None:
    _scan_forbidden_keys(payload)
    text = json.dumps(payload, ensure_ascii=False)
    for case in cases:
        for secret in (case.case_id, case.template_id):
            if secret in text:
                raise PackageError("Identificador interno vazou para o pacote público")
        for token in (case.operator, case.expected.value):
            if token in text:
                raise PackageError("Operador ou classe esperada vazou para o pacote público")
    for public_case in payload.get("cases", ()):
        if isinstance(public_case, Mapping):
            outside = {
                k: v for k, v in public_case.items() if k not in ("xml", "record", "document")
            }
            outside_text = json.dumps(outside, ensure_ascii=False).lower()
            for case in cases:
                for identity in (case.family_id.lower(), case.issuer_id.lower()):
                    if identity and identity in outside_text:
                        raise PackageError(
                            "Identidade de família/emissor vazou fora do conteúdo comparado"
                        )


def _load_corpus(path: Path) -> Corpus:
    def hook(obj: dict[str, Any]) -> Any:
        if set(obj) == {"$bytes"}:
            return base64.b64decode(obj["$bytes"], validate=True)
        return obj

    try:
        raw = json.loads(path.read_text(encoding="utf-8"), object_hook=hook)
        return Corpus.model_validate(raw)
    except (OSError, ValueError, ValidationError) as exc:
        raise PackageError(f"Corpus ilegível ou inválido: {type(exc).__name__}") from exc


def _write_json(path: Path, value: Mapping[str, Any], *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise PackageError(f"Arquivo já existe (use --overwrite para substituir): {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def export_package(
    corpus_path: Path,
    output_path: Path,
    *,
    private_map_path: Path | None = None,
    guide_version: str = GUIDE_VERSION,
    overwrite: bool = False,
) -> BuiltPackage:
    if private_map_path is not None and private_map_path.resolve() == output_path.resolve():
        raise PackageError("Mapa privado deve ser um arquivo diferente do pacote público")
    built = build_package(_load_corpus(corpus_path), guide_version=guide_version)
    _write_json(output_path, built.package, overwrite=overwrite)
    if private_map_path is not None:
        _write_json(private_map_path, built.private_map, overwrite=overwrite)
    return built


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m comprova_lattes.experiments.annotation_package",
        description=(
            "Exporta o pacote sanitizado de anotação humana (5 casos da partição piloto) de "
            "um Corpus existente. Offline; não gera, calibra, congela nem chama Gemini/API."
        ),
    )
    parser.add_argument("--corpus", type=Path, required=True, help="Corpus JSON existente")
    parser.add_argument("--output", type=Path, required=True, help="Pacote público de saída")
    parser.add_argument(
        "--private-map",
        type=Path,
        default=None,
        help="Opcional: mapa privado neutro->original. Nunca entregar aos anotadores.",
    )
    parser.add_argument("--guide-version", default=GUIDE_VERSION)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        built = export_package(
            args.corpus,
            args.output,
            private_map_path=args.private_map,
            guide_version=args.guide_version,
            overwrite=args.overwrite,
        )
    except PackageError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    # Resumo deliberadamente sem operadores/classes/categorias: o preparador pode ser anotador.
    print(
        json.dumps(
            {
                "package_version": PACKAGE_VERSION,
                "guide_version": built.package["guide_version"],
                "package_sha256": built.package["package_sha256"],
                "case_count": len(built.package["cases"]),
                "output": args.output.name,
                "private_map_written": args.private_map is not None,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
