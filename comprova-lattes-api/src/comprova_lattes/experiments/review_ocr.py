"""Serviço HTTP local, independente e offline de auxílio OCR para `/revisao-experimental`.

Executa exclusivamente em loopback (`127.0.0.1` / `localhost`, porta padrão `8766`) via FastAPI e
uvicorn já instalados no ambiente, sem carregar `Settings`/`.env`, banco de dados, fila Celery/Redis
ou cliente Gemini.

Reaproveita `TesseractOCR` e `OCRRegex`, mantendo o texto bruto reconhecido pelo Tesseract
separado dos valores recortados por expressão regular e sinalizando ausência de extração na RegEx
sem rotular automaticamente qualquer campo como ausente no comprovante.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import re
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.concurrency import run_in_threadpool

from .baseline import FIELD_LABELS_PT, FIELDS, OCRRegex
from .ocr import (
    DEFAULT_MAX_IMAGE_PIXELS,
    DEFAULT_MAX_PDF_PAGES,
    DEFAULT_OCR_DPI,
    DEFAULT_OCR_LANG,
    DEFAULT_OCR_TIMEOUT_SECONDS,
    DEFAULT_PDF_RESAMPLING,
    SUPPORTED_OCR_MIME_TYPES,
    SUPPORTED_PDF_RESAMPLING_MODES,
    OCRError,
    OCRRenderError,
    TesseractExecutionError,
    TesseractLanguageError,
    TesseractNotFoundError,
    TesseractOCR,
    TesseractTimeoutError,
)

SERVICE_VERSION = "review-ocr-service-v1"
ASSIST_DIAGNOSTICS_VERSION = "ocr-diagnostics-v1"
ASSISTED_PRESET_ID = "assisted-lanczos-4x-dpi288-v1"
BASELINE_PRESET_ID = "baseline-default-v1"
PROVIDER_NAME = "tesseract-local"
DEFAULT_REVIEW_OCR_HOST = "127.0.0.1"
DEFAULT_REVIEW_OCR_PORT = 8766
DEFAULT_MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_CONCURRENCY = 1
DEFAULT_ASSISTED_OCR_DPI = 288
DEFAULT_ASSISTED_PDF_RESAMPLING = "pillow_lanczos"
DEFAULT_ASSISTED_UPSCALE_SMALL_IMAGES = True
DEFAULT_ASSISTED_OCR_PSM = 3
SUPPORTED_PRESETS: tuple[str, ...] = ("assisted", "baseline")
MAX_FIELD_VALUE_LENGTH = 500
_YEAR_FIELDS: frozenset[str] = frozenset({"start_year", "end_year", "activity_year"})
_FOUR_DIGIT_YEAR_PATTERN = re.compile(r"^\d{4}$")
_DIGITS_ONLY_PATTERN = re.compile(r"^\d+$")

ALLOWED_LOOPBACK_HOSTS: frozenset[str] = frozenset({"127.0.0.1", "localhost", "::1", "[::1]"})
DEFAULT_CORS_ORIGINS: tuple[str, ...] = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

FORBIDDEN_REQUEST_KEYS: frozenset[str] = frozenset(
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
        "xml",
        "record",
        "cases",
        "package_sha256",
        "private_map",
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

METHODOLOGY_WARNINGS: tuple[str, ...] = (
    (
        "Saída gerada por TesseractOCR + OCRRegex (mesma pilha do baseline clássico). "
        "Pode induzir viés pró-baseline se copiada sem conferência visual direta no comprovante."
    ),
    (
        "A saída do OCR nunca constitui gabarito. Campos com valor null em regex_fields "
        "indicam apenas ausência de captura pela RegEx, não ausência nem ilegibilidade no documento."
    ),
)


class ReviewOCRRequest(BaseModel):
    """Contrato estrito de entrada: somente ID neutro/documento, MIME, SHA-256 e bytes base64."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str
    mime_type: str
    sha256: str
    content_base64: str


def max_base64_chars(max_document_bytes: int) -> int:
    """Limite exato de caracteres base64 correspondente a `max_document_bytes` antes do decode."""
    return ((max_document_bytes + 2) // 3) * 4


def max_request_body_bytes(max_document_bytes: int) -> int:
    """Limite de bytes do corpo HTTP JSON antes de decodificar JSON/base64."""
    return max_base64_chars(max_document_bytes) + 4096


def validate_loopback_host(host: str) -> str:
    """Garante que o servidor nunca faça bind em interfaces externas (`0.0.0.0`, IPs de rede, etc.)."""
    cleaned = host.strip().lower()
    if cleaned not in ALLOWED_LOOPBACK_HOSTS:
        raise ValueError(
            f"Host {host!r} proibido: o serviço review_ocr aceita somente loopback "
            "(127.0.0.1 ou localhost)."
        )
    return "127.0.0.1" if cleaned == "127.0.0.1" else cleaned


def resolve_bind_host(host: str, *, container_bind: bool = False) -> str:
    """Container opt-in; Compose must publish its port only on the host loopback."""
    if container_bind:
        if host.strip() != "0.0.0.0":
            raise ValueError("--container-bind exige --host 0.0.0.0; publique a porta apenas em 127.0.0.1.")
        return "0.0.0.0"
    return validate_loopback_host(host)


def _extract_hostname(host_header: str) -> str:
    raw = host_header.strip().lower()
    if not raw:
        return ""
    if raw.startswith("["):
        end = raw.find("]")
        return raw[: end + 1] if end != -1 else raw
    return raw.split(":", 1)[0]


def _find_forbidden_key(value: Any, path: str = "$") -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_str = str(key)
            if key_str in FORBIDDEN_REQUEST_KEYS:
                return f"{path}.{key_str}"
            nested = _find_forbidden_key(child, f"{path}.{key_str}")
            if nested is not None:
                return nested
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            nested = _find_forbidden_key(item, f"{path}[{index}]")
            if nested is not None:
                return nested
    return None


def _sniff_matches(mime_type: str, data: bytes) -> bool:
    if mime_type == "application/pdf":
        return data.startswith(b"%PDF-")
    if mime_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    return False


def _error_response(
    status_code: int,
    error_code: str,
    detail: str,
    *,
    document_id: str | None = None,
    sha256: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "error_code": error_code,
        "detail": detail,
        "document_id": document_id,
        "sha256": sha256,
    }
    if extra:
        payload.update(extra)
    return JSONResponse(status_code=status_code, content=payload)


@dataclass(frozen=True)
class RegexFieldAnalysis:
    """Resultado auditável da captura por `OCRRegex`, separando válidos e inválidos."""

    regex_fields: dict[str, str | None]
    invalid_regex_fields: dict[str, str]
    field_warnings: dict[str, str]
    general_warnings: list[str]


def _validate_single_regex_field(
    document_id: str,
    data: bytes,
    mime_type: str,
    field: str,
    matched_line: str,
    raw_value: str,
    pattern: str,
) -> tuple[str | None, str | None]:
    label = FIELD_LABELS_PT.get(field, field)
    if len(raw_value) > MAX_FIELD_VALUE_LENGTH:
        return (
            None,
            (
                f"{label}: valor capturado excede {MAX_FIELD_VALUE_LENGTH} caracteres "
                "e não foi aplicado automaticamente; confira o comprovante."
            ),
        )
    if field in _YEAR_FIELDS and not _FOUR_DIGIT_YEAR_PATTERN.fullmatch(raw_value):
        if _DIGITS_ONLY_PATTERN.fullmatch(raw_value):
            return (
                None,
                (
                    f"{label} capturado ('{raw_value}') possui {len(raw_value)} dígitos "
                    "(esperado ano com exatamente 4 dígitos). Possível erro de OCR; "
                    "não foi corrigido nem preenchido automaticamente — confira a imagem."
                ),
            )
        return (
            None,
            (
                f"{label} capturado ('{raw_value}') não é um ano válido de 4 dígitos. "
                "Não foi corrigido nem preenchido automaticamente — confira a imagem."
            ),
        )
    single = OCRRegex(
        lambda *_args, line=matched_line: line,
        patterns={field: pattern},
    ).extract(document_id, data, mime_type)
    val = getattr(single, field, None) if single.extraction_status == "OK" else None
    if val is None:
        if field == "workload_hours":
            return (
                None,
                (
                    f"{label} capturada ('{raw_value}') não é um número decimal válido "
                    "(ex.: 40 ou 40.5). Não foi preenchida automaticamente — confira o comprovante."
                ),
            )
        return (
            None,
            (
                f"{label} capturado ('{raw_value}') é inválido pelo contrato de campo. "
                "Não foi preenchido automaticamente — confira o comprovante."
            ),
        )
    return str(val), None


def _analyze_regex_fields(
    document_id: str,
    data: bytes,
    mime_type: str,
    ocr_text: str,
    patterns: dict[str, str] | None = None,
) -> RegexFieldAnalysis:
    """Recorta campos via `OCRRegex`, mantendo capturas inválidas visíveis sem preencher campo válido."""
    empty_fields: dict[str, str | None] = {field: None for field in FIELDS}
    if not ocr_text or not ocr_text.strip():
        return RegexFieldAnalysis(
            regex_fields=empty_fields,
            invalid_regex_fields={},
            field_warnings={},
            general_warnings=[],
        )

    extractor = OCRRegex(lambda *_: ocr_text, patterns=patterns)
    regex_fields: dict[str, str | None] = {field: None for field in FIELDS}
    invalid_regex_fields: dict[str, str] = {}
    field_warnings: dict[str, str] = {}
    matched_lines: dict[str, str] = {}
    raw_captures: dict[str, str] = {}

    for field in FIELDS:
        pattern = extractor.patterns[field]
        found = re.search(pattern, ocr_text, flags=re.MULTILINE | re.IGNORECASE)
        if not found:
            continue
        matched_lines[field] = found.group(0)
        raw_captures[field] = found.group(1).strip()

    for field in FIELDS:
        if field not in raw_captures or field == "issuer_name_acronym_evidence":
            continue
        valid_val, warning = _validate_single_regex_field(
            document_id,
            data,
            mime_type,
            field,
            matched_lines[field],
            raw_captures[field],
            extractor.patterns[field],
        )
        if valid_val is not None:
            regex_fields[field] = valid_val
        else:
            invalid_regex_fields[field] = raw_captures[field][:MAX_FIELD_VALUE_LENGTH]
            if warning:
                field_warnings[field] = warning

    if "issuer_name_acronym_evidence" in raw_captures:
        raw_ev = raw_captures["issuer_name_acronym_evidence"]
        if len(raw_ev) > MAX_FIELD_VALUE_LENGTH:
            invalid_regex_fields["issuer_name_acronym_evidence"] = raw_ev[:MAX_FIELD_VALUE_LENGTH]
            field_warnings["issuer_name_acronym_evidence"] = (
                f"{FIELD_LABELS_PT['issuer_name_acronym_evidence']}: valor capturado excede "
                f"{MAX_FIELD_VALUE_LENGTH} caracteres e não foi aplicado automaticamente."
            )
        else:
            combined_lines = [matched_lines["issuer_name_acronym_evidence"]]
            combined_patterns = {
                "issuer_name_acronym_evidence": extractor.patterns["issuer_name_acronym_evidence"]
            }
            for dep in ("issuer_institution", "issuer_acronym"):
                if regex_fields[dep] is not None and dep in matched_lines:
                    combined_lines.append(matched_lines[dep])
                    combined_patterns[dep] = extractor.patterns[dep]
            combined_text = "\n".join(combined_lines)
            rel_rec = OCRRegex(
                lambda *_args, txt=combined_text: txt,
                patterns=combined_patterns,
            ).extract(document_id, data, mime_type)
            rel_val = (
                rel_rec.issuer_name_acronym_evidence if rel_rec.extraction_status == "OK" else None
            )
            if rel_val is not None:
                regex_fields["issuer_name_acronym_evidence"] = str(rel_val)
            else:
                invalid_regex_fields["issuer_name_acronym_evidence"] = raw_ev
                field_warnings["issuer_name_acronym_evidence"] = (
                    f"{FIELD_LABELS_PT['issuer_name_acronym_evidence']} capturada ('{raw_ev}') "
                    "não comprova simultaneamente nome e sigla válidos nos campos extraídos. "
                    "Valor bruto preservado para conferência visual; não aplicado automaticamente."
                )

    general_warnings = [
        f"Sugestão inválida bloqueada em '{FIELD_LABELS_PT.get(field, field)}': {msg}"
        for field, msg in field_warnings.items()
    ]
    return RegexFieldAnalysis(
        regex_fields=regex_fields,
        invalid_regex_fields=invalid_regex_fields,
        field_warnings=field_warnings,
        general_warnings=general_warnings,
    )


def _extract_regex_fields(
    document_id: str,
    data: bytes,
    mime_type: str,
    ocr_text: str,
    patterns: dict[str, str] | None = None,
) -> dict[str, str | None]:
    """Recorta campos válidos via `OCRRegex` sem rotular ausência de captura como campo ausente."""
    return _analyze_regex_fields(
        document_id, data, mime_type, ocr_text, patterns=patterns
    ).regex_fields


def _resolve_version_line(ocr: Any) -> str:
    version_fn = getattr(ocr, "version", None)
    if callable(version_fn):
        try:
            raw_version = str(version_fn()).strip()
            if raw_version:
                return raw_version.splitlines()[0].strip()
        except OCRError:
            pass
    return "tesseract (versão não disponível)"


def _build_params_metadata(ocr: Any) -> dict[str, Any]:
    dpi = int(getattr(ocr, "dpi", DEFAULT_OCR_DPI))
    lang = str(getattr(ocr, "lang", DEFAULT_OCR_LANG))
    timeout_seconds = float(getattr(ocr, "timeout_seconds", DEFAULT_OCR_TIMEOUT_SECONDS))
    max_pdf_pages = int(getattr(ocr, "max_pdf_pages", DEFAULT_MAX_PDF_PAGES))
    max_image_pixels = int(getattr(ocr, "max_image_pixels", DEFAULT_MAX_IMAGE_PIXELS))
    return {
        "dpi": dpi,
        "lang": lang,
        "timeout_ms": round(timeout_seconds * 1000),
        "max_pdf_pages": max_pdf_pages,
        "max_image_pixels": max_image_pixels,
        "pdf_text_extraction": "disabled_raster_only",
        "regex_extractor": "OCRRegex",
    }


def _build_assist_preset_metadata(ocr: Any) -> dict[str, Any]:
    dpi = int(getattr(ocr, "dpi", DEFAULT_OCR_DPI))
    pdf_resampling = str(getattr(ocr, "pdf_resampling", DEFAULT_PDF_RESAMPLING))
    upscale_small_images = bool(getattr(ocr, "upscale_small_images", False))
    psm_raw = getattr(ocr, "psm", None)
    psm = int(psm_raw) if isinstance(psm_raw, int) and not isinstance(psm_raw, bool) else None

    is_baseline = (
        dpi == DEFAULT_OCR_DPI
        and pdf_resampling == DEFAULT_PDF_RESAMPLING
        and upscale_small_images is False
        and psm is None
    )
    is_assisted_default = (
        dpi == DEFAULT_ASSISTED_OCR_DPI
        and pdf_resampling == DEFAULT_ASSISTED_PDF_RESAMPLING
        and upscale_small_images is DEFAULT_ASSISTED_UPSCALE_SMALL_IMAGES
        and psm == DEFAULT_ASSISTED_OCR_PSM
    )
    if not isinstance(ocr, TesseractOCR):
        preset_id = "custom-injected"
    elif is_assisted_default:
        preset_id = ASSISTED_PRESET_ID
    elif is_baseline:
        preset_id = BASELINE_PRESET_ID
    else:
        preset_id = "assisted-custom-v1"

    return {
        "preset_id": preset_id,
        "baseline_compatible": is_baseline,
        "dpi": dpi,
        "pdf_resampling": pdf_resampling,
        "upscale_small_images": upscale_small_images,
        "psm": psm,
    }


def build_ocr_for_preset(
    preset: str = "assisted",
    *,
    executable: Path | str | None = None,
    tessdata_dir: Path | str | None = None,
    lang: str = DEFAULT_OCR_LANG,
    dpi: int | None = None,
    timeout_seconds: float = DEFAULT_OCR_TIMEOUT_SECONDS,
    max_pdf_pages: int = DEFAULT_MAX_PDF_PAGES,
    max_image_pixels: int = DEFAULT_MAX_IMAGE_PIXELS,
    psm: int | None = None,
    pdf_resampling: str | None = None,
    upscale_small_images: bool | None = None,
) -> TesseractOCR:
    """Constrói `TesseractOCR` para o serviço assistido sem alterar defaults do baseline."""
    if preset not in SUPPORTED_PRESETS:
        raise ValueError(f"Preset OCR inválido: {preset!r}. Use um de: {SUPPORTED_PRESETS}.")
    if preset == "baseline":
        return TesseractOCR(
            executable=executable,
            tessdata_dir=tessdata_dir,
            lang=lang,
            dpi=DEFAULT_OCR_DPI if dpi is None else dpi,
            timeout_seconds=timeout_seconds,
            max_pdf_pages=max_pdf_pages,
            max_image_pixels=max_image_pixels,
            psm=psm,
            pdf_resampling=DEFAULT_PDF_RESAMPLING if pdf_resampling is None else pdf_resampling,
            upscale_small_images=(
                False if upscale_small_images is None else upscale_small_images
            ),
        )
    return TesseractOCR(
        executable=executable,
        tessdata_dir=tessdata_dir,
        lang=lang,
        dpi=DEFAULT_ASSISTED_OCR_DPI if dpi is None else dpi,
        timeout_seconds=timeout_seconds,
        max_pdf_pages=max_pdf_pages,
        max_image_pixels=max_image_pixels,
        psm=DEFAULT_ASSISTED_OCR_PSM if psm is None else psm,
        pdf_resampling=(
            DEFAULT_ASSISTED_PDF_RESAMPLING if pdf_resampling is None else pdf_resampling
        ),
        upscale_small_images=(
            DEFAULT_ASSISTED_UPSCALE_SMALL_IMAGES
            if upscale_small_images is None
            else upscale_small_images
        ),
    )


def create_review_ocr_app(
    *,
    ocr: Callable[[bytes, str], str] | None = None,
    preset: str = "assisted",
    patterns: dict[str, str] | None = None,
    cors_origins: Sequence[str] = DEFAULT_CORS_ORIGINS,
    max_document_bytes: int = DEFAULT_MAX_DOCUMENT_BYTES,
    max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    allow_testserver: bool = True,
) -> FastAPI:
    """Cria a aplicação FastAPI local de auxílio OCR sem banco, fila ou `.env`."""
    if type(max_document_bytes) is not int or max_document_bytes < 64:
        raise ValueError("max_document_bytes deve ser inteiro >= 64.")
    if type(max_concurrency) is not int or max_concurrency < 1:
        raise ValueError("max_concurrency deve ser inteiro positivo.")

    ocr_engine = ocr if ocr is not None else build_ocr_for_preset(preset)
    allowed_origins = tuple(cors_origins)
    allowed_origins_set = frozenset(allowed_origins)
    allowed_hosts = set(ALLOWED_LOOPBACK_HOSTS)
    if allow_testserver:
        allowed_hosts.add("testserver")

    body_limit = max_request_body_bytes(max_document_bytes)
    b64_limit = max_base64_chars(max_document_bytes)
    semaphore = threading.BoundedSemaphore(max_concurrency)

    application = FastAPI(
        title="Comprova Lattes — Serviço Local de Auxílio OCR (Revisão Experimental)",
        version=SERVICE_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )

    @application.middleware("http")
    async def enforce_loopback_and_origin(request: Request, call_next):
        host_name = _extract_hostname(request.headers.get("host", ""))
        if host_name not in allowed_hosts:
            return _error_response(
                403,
                "FORBIDDEN_HOST",
                "Acesso negado: o serviço OCR aceita apenas conexões loopback (127.0.0.1 / localhost).",
            )
        origin = request.headers.get("origin")
        if origin is not None and origin not in allowed_origins_set:
            return _error_response(
                403,
                "FORBIDDEN_ORIGIN",
                "Origem CORS não autorizada para o serviço OCR local.",
            )
        return await call_next(request)

    @application.get("/health")
    def health_check() -> dict[str, Any]:
        meta_fn = getattr(ocr_engine, "metadata", None)
        meta = meta_fn() if callable(meta_fn) else None
        return {
            "status": "ok",
            "service_version": SERVICE_VERSION,
            "diagnostics_version": ASSIST_DIAGNOSTICS_VERSION,
            "provider": PROVIDER_NAME,
            "available": bool(meta["available"]) if isinstance(meta, Mapping) else True,
            "tesseract_version": (
                meta.get("tesseract_version")
                if isinstance(meta, Mapping)
                else _resolve_version_line(ocr_engine)
            ),
            "params": _build_params_metadata(ocr_engine),
            "assist_preset": _build_assist_preset_metadata(ocr_engine),
            "max_document_bytes": max_document_bytes,
            "max_base64_chars": b64_limit,
            "max_concurrency": max_concurrency,
            "error": meta.get("error") if isinstance(meta, Mapping) else None,
        }

    @application.post("/ocr")
    async def run_ocr(request: Request) -> JSONResponse:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > body_limit:
                    return _error_response(
                        413,
                        "PAYLOAD_TOO_LARGE",
                        (
                            f"Corpo HTTP ({content_length} bytes) excede o limite de "
                            f"{body_limit} bytes antes da decodificação."
                        ),
                    )
            except ValueError:
                return _error_response(400, "INVALID_CONTENT_LENGTH", "Cabeçalho Content-Length inválido.")

        raw_body = await request.body()
        if len(raw_body) > body_limit:
            return _error_response(
                413,
                "PAYLOAD_TOO_LARGE",
                f"Corpo HTTP ({len(raw_body)} bytes) excede o limite de {body_limit} bytes antes da decodificação.",
            )

        try:
            raw_json = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _error_response(
                422,
                "INVALID_JSON_BODY",
                "Corpo da requisição não é um JSON UTF-8 válido.",
            )

        if not isinstance(raw_json, Mapping):
            return _error_response(
                422,
                "INVALID_JSON_BODY",
                "Corpo da requisição deve ser um objeto JSON.",
            )

        forbidden_path = _find_forbidden_key(raw_json)
        if forbidden_path is not None:
            return _error_response(
                422,
                "FORBIDDEN_PAYLOAD_FIELDS",
                (
                    f"Campo proibido detectado ({forbidden_path}): dados de XML, registro "
                    "curricular ou gabarito nunca podem ser enviados ao serviço OCR."
                ),
            )

        raw_b64 = raw_json.get("content_base64")
        raw_doc_id = raw_json.get("document_id") if isinstance(raw_json.get("document_id"), str) else None
        raw_sha = raw_json.get("sha256") if isinstance(raw_json.get("sha256"), str) else None
        if isinstance(raw_b64, str) and len(raw_b64) > b64_limit:
            return _error_response(
                413,
                "PAYLOAD_TOO_LARGE",
                (
                    f"Campo content_base64 ({len(raw_b64)} caracteres) excede o limite de "
                    f"{b64_limit} caracteres antes da decodificação base64."
                ),
                document_id=raw_doc_id,
                sha256=raw_sha,
            )

        try:
            parsed = ReviewOCRRequest.model_validate(raw_json)
        except ValidationError as exc:
            return _error_response(
                422,
                "INVALID_REQUEST_SCHEMA",
                f"Esquema inválido na requisição OCR ({exc.error_count()} erro(s)).",
                document_id=raw_doc_id,
                sha256=raw_sha,
            )

        document_id = parsed.document_id.strip()
        if not document_id or len(document_id) > 120:
            return _error_response(
                422,
                "INVALID_DOCUMENT_ID",
                "document_id deve ser texto não vazio de até 120 caracteres.",
                document_id=parsed.document_id[:120],
                sha256=parsed.sha256,
            )

        if parsed.mime_type not in SUPPORTED_OCR_MIME_TYPES:
            return _error_response(
                415,
                "UNSUPPORTED_MIME_TYPE",
                (
                    f"MIME type não suportado para OCR: {parsed.mime_type!r}. "
                    f"Permitidos: {sorted(SUPPORTED_OCR_MIME_TYPES)}."
                ),
                document_id=document_id,
                sha256=parsed.sha256,
            )

        if not _SHA256_PATTERN.fullmatch(parsed.sha256):
            return _error_response(
                422,
                "INVALID_SHA256",
                "sha256 deve conter exatamente 64 caracteres hexadecimais minúsculos.",
                document_id=document_id,
                sha256=parsed.sha256,
            )

        if not parsed.content_base64:
            return _error_response(
                422,
                "EMPTY_DOCUMENT",
                "content_base64 não pode ser vazio.",
                document_id=document_id,
                sha256=parsed.sha256,
            )

        try:
            data = base64.b64decode(parsed.content_base64, validate=True)
        except (binascii.Error, ValueError):
            return _error_response(
                422,
                "INVALID_BASE64",
                "content_base64 contém codificação base64 inválida.",
                document_id=document_id,
                sha256=parsed.sha256,
            )

        if not data:
            return _error_response(
                422,
                "EMPTY_DOCUMENT",
                "Documento decodificado não contém bytes.",
                document_id=document_id,
                sha256=parsed.sha256,
            )

        if len(data) > max_document_bytes:
            return _error_response(
                413,
                "PAYLOAD_TOO_LARGE",
                f"Documento decodificado ({len(data)} bytes) excede o limite de {max_document_bytes} bytes.",
                document_id=document_id,
                sha256=parsed.sha256,
            )

        actual_sha256 = hashlib.sha256(data).hexdigest()
        if actual_sha256 != parsed.sha256:
            return _error_response(
                422,
                "SHA256_MISMATCH",
                "Hash SHA-256 declarado não confere com os bytes decodificados do comprovante.",
                document_id=document_id,
                sha256=actual_sha256,
                extra={
                    "expected_sha256": parsed.sha256,
                    "actual_sha256": actual_sha256,
                },
            )

        if not _sniff_matches(parsed.mime_type, data):
            return _error_response(
                422,
                "MIME_SIGNATURE_MISMATCH",
                f"Assinatura binária dos bytes não corresponde ao MIME declarado ({parsed.mime_type}).",
                document_id=document_id,
                sha256=actual_sha256,
            )

        if not semaphore.acquire(blocking=False):
            return _error_response(
                429,
                "OCR_CONCURRENCY_LIMIT",
                "Outra leitura OCR já está em andamento neste serviço local. Aguarde concluir e tente novamente.",
                document_id=document_id,
                sha256=actual_sha256,
            )

        try:
            try:
                ocr_text = await run_in_threadpool(ocr_engine, data, parsed.mime_type)
            except TesseractNotFoundError as exc:
                return _error_response(
                    503,
                    "TESSERACT_NOT_FOUND",
                    f"Executável do Tesseract não encontrado localmente: {exc}",
                    document_id=document_id,
                    sha256=actual_sha256,
                )
            except TesseractLanguageError as exc:
                return _error_response(
                    503,
                    "TESSERACT_LANGUAGE_MISSING",
                    f"Idioma OCR ('por') ausente no Tesseract local: {exc}",
                    document_id=document_id,
                    sha256=actual_sha256,
                )
            except TesseractTimeoutError as exc:
                return _error_response(
                    504,
                    "TESSERACT_TIMEOUT",
                    f"Tempo limite excedido ao executar o Tesseract OCR: {exc}",
                    document_id=document_id,
                    sha256=actual_sha256,
                )
            except OCRRenderError as exc:
                return _error_response(
                    422,
                    "OCR_RENDER_ERROR",
                    f"Falha ao preparar imagem ou PDF para OCR (dimensões/páginas/formato): {exc}",
                    document_id=document_id,
                    sha256=actual_sha256,
                )
            except (TesseractExecutionError, OCRError, OSError) as exc:
                return _error_response(
                    502,
                    "TESSERACT_EXECUTION_ERROR",
                    f"Falha operacional ao executar o Tesseract OCR: {exc}",
                    document_id=document_id,
                    sha256=actual_sha256,
                )

            analysis = _analyze_regex_fields(
                document_id, data, parsed.mime_type, ocr_text, patterns=patterns
            )
            version_line = await run_in_threadpool(_resolve_version_line, ocr_engine)
        finally:
            semaphore.release()

        accessed_at = datetime.now(UTC).isoformat()
        regex_fields = analysis.regex_fields
        unextracted = [
            field
            for field in FIELDS
            if regex_fields[field] is None and field not in analysis.invalid_regex_fields
        ]
        extracted_count = sum(1 for field in FIELDS if regex_fields[field] is not None)
        warnings = list(METHODOLOGY_WARNINGS) + analysis.general_warnings

        return JSONResponse(
            status_code=200,
            content={
                "service_version": SERVICE_VERSION,
                "diagnostics_version": ASSIST_DIAGNOSTICS_VERSION,
                "document_id": document_id,
                "mime_type": parsed.mime_type,
                "sha256": actual_sha256,
                "accessed_at": accessed_at,
                "provider": PROVIDER_NAME,
                "tesseract_version": version_line,
                "params": _build_params_metadata(ocr_engine),
                "assist_preset": _build_assist_preset_metadata(ocr_engine),
                "ocr_text": ocr_text,
                "regex_fields": regex_fields,
                "invalid_regex_fields": analysis.invalid_regex_fields,
                "field_warnings": analysis.field_warnings,
                "field_labels": dict(FIELD_LABELS_PT),
                "extracted_field_count": extracted_count,
                "unextracted_fields": unextracted,
                "warnings": warnings,
            },
        )

    return application


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m comprova_lattes.experiments.review_ocr",
        description=(
            "Serviço HTTP local (loopback) e offline de auxílio OCR (TesseractOCR + OCRRegex) "
            "para a tela /revisao-experimental. Não usa banco, fila, Gemini nem .env."
        ),
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_REVIEW_OCR_HOST,
        help="Host de bind loopback (somente 127.0.0.1 ou localhost; padrão: 127.0.0.1).",
    )
    parser.add_argument(
        "--container-bind", action="store_true",
        help="Permite bind 0.0.0.0 dentro do container. Publique somente 127.0.0.1:8766:8766.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_REVIEW_OCR_PORT,
        help=f"Porta TCP local distinta da API principal (padrão: {DEFAULT_REVIEW_OCR_PORT}).",
    )
    parser.add_argument("--executable", type=Path, default=None, help="Caminho explícito do binário tesseract.")
    parser.add_argument("--tessdata-dir", type=Path, default=None, help="Diretório tessdata opcional.")
    parser.add_argument("--lang", default=DEFAULT_OCR_LANG, help="Idioma do Tesseract (padrão: por).")
    parser.add_argument(
        "--preset",
        choices=SUPPORTED_PRESETS,
        default="assisted",
        help=(
            "Perfil OCR do serviço assistido (padrão: assisted — 288 DPI, pillow_lanczos, "
            "upscale de imagens pequenas, PSM 3; baseline mantém 300 DPI + pdfium sem alterações)."
        ),
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=None,
        help="DPI do OCR (padrão: 288 no preset assisted; 300 no preset baseline).",
    )
    parser.add_argument(
        "--psm",
        type=int,
        default=None,
        help="Modo de segmentação de página (--psm 0..13) explícito.",
    )
    parser.add_argument(
        "--pdf-resampling",
        choices=sorted(SUPPORTED_PDF_RESAMPLING_MODES),
        default=None,
        help="Método de reamostragem PDF (padrão: pillow_lanczos no preset assisted; pdfium no baseline).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_OCR_TIMEOUT_SECONDS,
        help="Timeout por página/execução do subprocesso em segundos (padrão: 30).",
    )
    parser.add_argument(
        "--max-pdf-pages",
        type=int,
        default=DEFAULT_MAX_PDF_PAGES,
        help=f"Limite máximo de páginas por PDF (padrão: {DEFAULT_MAX_PDF_PAGES}).",
    )
    parser.add_argument(
        "--max-image-pixels",
        type=int,
        default=DEFAULT_MAX_IMAGE_PIXELS,
        help=f"Limite máximo de pixels por página/imagem (padrão: {DEFAULT_MAX_IMAGE_PIXELS}).",
    )
    parser.add_argument(
        "--max-document-bytes",
        type=int,
        default=DEFAULT_MAX_DOCUMENT_BYTES,
        help=f"Limite máximo de bytes do comprovante decodificado (padrão: {DEFAULT_MAX_DOCUMENT_BYTES}).",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=DEFAULT_MAX_CONCURRENCY,
        help=f"Máximo de execuções OCR simultâneas (padrão: {DEFAULT_MAX_CONCURRENCY}).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Inspeciona disponibilidade do Tesseract/idioma e configuração do serviço sem manter servidor aberto.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        host = resolve_bind_host(args.host, container_bind=args.container_bind)
        if not (1024 <= args.port <= 65535):
            raise ValueError("Porta deve estar entre 1024 e 65535.")
        ocr = build_ocr_for_preset(
            args.preset,
            executable=args.executable,
            tessdata_dir=args.tessdata_dir,
            lang=args.lang,
            dpi=args.dpi,
            timeout_seconds=args.timeout,
            max_pdf_pages=args.max_pdf_pages,
            max_image_pixels=args.max_image_pixels,
            psm=args.psm,
            pdf_resampling=args.pdf_resampling,
        )
        create_review_ocr_app(
            ocr=ocr,
            max_document_bytes=args.max_document_bytes,
            max_concurrency=args.max_concurrency,
            allow_testserver=False,
        )
    except ValueError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    if args.check:
        meta = ocr.metadata()
        report = {
            "service_version": SERVICE_VERSION,
            "diagnostics_version": ASSIST_DIAGNOSTICS_VERSION,
            "host": host,
            "port": args.port,
            "endpoint": f"http://{host}:{args.port}/ocr",
            "cors_origins": list(DEFAULT_CORS_ORIGINS),
            "max_document_bytes": args.max_document_bytes,
            "max_base64_chars": max_base64_chars(args.max_document_bytes),
            "max_concurrency": args.max_concurrency,
            "assist_preset": _build_assist_preset_metadata(ocr),
            "ocr": meta,
        }
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if meta["available"] else 1

    import uvicorn

    app = create_review_ocr_app(
        ocr=ocr,
        max_document_bytes=args.max_document_bytes,
        max_concurrency=args.max_concurrency,
        allow_testserver=False,
    )
    uvicorn.run(app, host=host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
