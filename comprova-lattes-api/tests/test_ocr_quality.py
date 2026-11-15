"""Regressões de qualidade OCR no ensaio assistido e nos documentos PILOTO locais.

Regras científicas respeitadas:
- Nunca lê `xml`, `record`, gabarito, partição `final` ou thresholds.
- Lê apenas `case_id` e `document` do pacote piloto `.tmp-pilot-review/pacote-anotacao-piloto-legivel.json`.
- Preserva integralmente os defaults do baseline (`TesseractOCR()` e `OCRRegex`).
"""

from __future__ import annotations

import base64
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from comprova_lattes.experiments.baseline import OCRRegex
from comprova_lattes.experiments.ocr import TesseractOCR
from comprova_lattes.experiments.render import pdf, png, raster
from comprova_lattes.experiments.review_ocr import (
    ASSISTED_PRESET_ID,
    BASELINE_PRESET_ID,
    build_ocr_for_preset,
    create_review_ocr_app,
)
from comprova_lattes.experiments.synthetic import document_text
from comprova_lattes.matcher.models import ExtractedDocumentRecord

REPO_ROOT = Path(__file__).resolve().parents[2]
PILOT_PACKAGE_PATH = REPO_ROOT / ".tmp-pilot-review" / "pacote-anotacao-piloto-legivel.json"


def _load_pilot_documents_only() -> dict[str, dict[str, object]]:
    if not PILOT_PACKAGE_PATH.exists():
        pytest.skip("Pacote piloto local .tmp-pilot-review/pacote-anotacao-piloto-legivel.json ausente")
    raw = json.loads(PILOT_PACKAGE_PATH.read_text(encoding="utf-8"))
    docs: dict[str, dict[str, object]] = {}
    for case in raw.get("cases", []):
        doc = case.get("document")
        if not doc:
            continue
        docs[case["case_id"]] = {
            "case_id": case["case_id"],
            "mime_type": doc["mime_type"],
            "sha256": doc["sha256"],
            "raw_bytes": base64.b64decode(doc["content_base64"]),
            "content_base64": doc["content_base64"],
        }
    return docs


def _ocr_payload(doc_entry: dict[str, object]) -> dict[str, str]:
    return {
        "document_id": str(doc_entry["case_id"]),
        "mime_type": str(doc_entry["mime_type"]),
        "sha256": str(doc_entry["sha256"]),
        "content_base64": str(doc_entry["content_base64"]),
    }


def test_pilot_case001_baseline_invalid_year_is_blocked_without_raw_tampering():
    docs = _load_pilot_documents_only()
    case_001 = docs["case-001"]

    baseline_app = create_review_ocr_app(preset="baseline")
    client = TestClient(baseline_app)
    res = client.post("/ocr", json=_ocr_payload(case_001))
    assert res.status_code == 200
    body = res.json()

    assert body["assist_preset"] == {
        "preset_id": BASELINE_PRESET_ID,
        "baseline_compatible": True,
        "dpi": 300,
        "pdf_resampling": "pdfium",
        "upscale_small_images": False,
        "psm": None,
    }
    # Baseline local reproduz 20381 e distorções de cabeçalho sem adulteração nem autocorreção 20381 -> 2031
    assert "20381" in body["ocr_text"]
    assert body["regex_fields"]["start_year"] is None
    assert "start_year" not in body["unextracted_fields"]
    assert body["invalid_regex_fields"].get("start_year") == "20381"
    assert "start_year" in body["field_warnings"]
    assert "20381" in body["field_warnings"]["start_year"]


def test_pilot_documents_assisted_preset_improves_readability_and_audits_metadata():
    docs = _load_pilot_documents_only()
    assisted_app = create_review_ocr_app(preset="assisted")
    client = TestClient(assisted_app)

    res_001 = client.post("/ocr", json=_ocr_payload(docs["case-001"])).json()
    assert res_001["assist_preset"] == {
        "preset_id": ASSISTED_PRESET_ID,
        "baseline_compatible": False,
        "dpi": 288,
        "pdf_resampling": "pillow_lanczos",
        "upscale_small_images": True,
        "psm": 3,
    }
    assert "DECLARAÇÃO DE PARTICIPAÇÃO EM EVENTO" in res_001["ocr_text"]
    assert res_001["regex_fields"]["start_year"] == "2031"
    assert res_001["regex_fields"]["end_year"] == "2031"
    assert res_001["regex_fields"]["activity_year"] == "2031"
    assert res_001["regex_fields"]["holder_name"] == "Vitor Ferreira"
    assert "start_year" not in res_001["invalid_regex_fields"]

    # case-002, case-003 e case-004 do piloto também são lidos de forma legível pelo preset assistido
    res_002 = client.post("/ocr", json=_ocr_payload(docs["case-002"])).json()
    assert res_002["regex_fields"]["start_year"] is not None
    assert "DECLARAÇÃO" in res_002["ocr_text"] or "CERTIFICADO" in res_002["ocr_text"]

    res_003 = client.post("/ocr", json=_ocr_payload(docs["case-003"])).json()
    assert res_003["regex_fields"]["start_year"] == "2020"

    res_004 = client.post("/ocr", json=_ocr_payload(docs["case-004"])).json()
    assert "documental." in res_004["ocr_text"]


def test_synthetic_small_png_and_pdf_quality_plus_illegible_handling_and_ocrregex_compat():
    record = ExtractedDocumentRecord(
        document_id="synth-quality-001",
        holder_name="Vitor Ferreira",
        activity_title="Seminario de Qualidade Documental",
        issuer_institution="Escola Vale Regional - EVR",
        issuer_acronym="EVR",
        issuer_name_acronym_evidence="Escola Vale Regional - EVR (EVR)",
        start_year=2031,
        end_year=2031,
        activity_year=2031,
        workload_hours=Decimal(20),
    )
    text = document_text(record, layout=0)
    w, h, px = raster(text, seed=11, degradation=0, layout=0)
    sample_png = png(w, h, px)
    sample_pdf = pdf(w, h, px)

    baseline_ocr = TesseractOCR()
    assisted_ocr = build_ocr_for_preset("assisted")

    # Baseline defaults permanecem intactos e compatíveis com OCRRegex
    assert baseline_ocr.dpi == 300
    assert baseline_ocr.pdf_resampling == "pdfium"
    assert baseline_ocr.upscale_small_images is False
    assert baseline_ocr.psm is None

    rec_base = OCRRegex(baseline_ocr).extract("synth-quality-001", sample_pdf, "application/pdf")
    rec_assist_pdf = OCRRegex(assisted_ocr).extract("synth-quality-001", sample_pdf, "application/pdf")
    rec_assist_png = OCRRegex(assisted_ocr).extract("synth-quality-001", sample_png, "image/png")

    assert rec_base.extraction_status in ("OK", "INVALID_JSON")
    assert rec_assist_pdf.extraction_status == "OK"
    assert rec_assist_pdf.start_year == 2031
    assert rec_assist_png.extraction_status == "OK"
    assert rec_assist_png.start_year == 2031

    # Imagem sintética sem texto legível não gera falso inválido sintático
    blank_w, blank_h, blank_px = raster("   \n   ", seed=1, degradation=2, layout=0)
    blank_png = png(blank_w, blank_h, blank_px)
    client = TestClient(create_review_ocr_app(preset="assisted"))
    blank_res = client.post(
        "/ocr",
        json={
            "document_id": "synth-blank",
            "mime_type": "image/png",
            "sha256": hashlib.sha256(blank_png).hexdigest(),
            "content_base64": base64.b64encode(blank_png).decode("ascii"),
        },
    )
    assert blank_res.status_code == 200
    blank_body = blank_res.json()
    assert blank_body["extracted_field_count"] == 0
    assert blank_body["invalid_regex_fields"] == {}
    assert blank_body["field_warnings"] == {}
