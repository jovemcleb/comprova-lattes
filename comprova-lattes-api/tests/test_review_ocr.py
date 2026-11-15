"""Testes offline do serviço local `review_ocr` e do protocolo JSON de revisão assistida por OCR."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from comprova_lattes.experiments.annotation_package import (
    FORBIDDEN_KEYS,
    PACKAGE_VERSION,
    build_package,
    compute_package_sha256,
    validate_package,
)
from comprova_lattes.experiments.baseline import FIELDS
from comprova_lattes.experiments.ocr import (
    TesseractExecutionError,
    TesseractLanguageError,
    TesseractNotFoundError,
    TesseractOCR,
    TesseractTimeoutError,
)
from comprova_lattes.experiments.render import pdf, png, raster
from comprova_lattes.experiments.review_ocr import (
    ASSIST_DIAGNOSTICS_VERSION,
    ASSISTED_PRESET_ID,
    BASELINE_PRESET_ID,
    DEFAULT_ASSISTED_OCR_DPI,
    DEFAULT_ASSISTED_OCR_PSM,
    DEFAULT_ASSISTED_PDF_RESAMPLING,
    DEFAULT_ASSISTED_UPSCALE_SMALL_IMAGES,
    DEFAULT_CORS_ORIGINS,
    DEFAULT_REVIEW_OCR_HOST,
    DEFAULT_REVIEW_OCR_PORT,
    PROVIDER_NAME,
    SERVICE_VERSION,
    build_ocr_for_preset,
    create_review_ocr_app,
    main,
    max_base64_chars,
    validate_loopback_host,
)
from comprova_lattes.experiments.synthetic import generate


def _sample_png_bytes() -> bytes:
    w, h, px = raster("CERTIFICADO\nTitular: PESSOA TESTE", seed=7, degradation=0, layout=0)
    return png(w, h, px)


def _sample_pdf_bytes() -> bytes:
    w, h, px = raster("CERTIFICADO\nTitular: PESSOA TESTE", seed=7, degradation=0, layout=0)
    return pdf(w, h, px)


def _sample_jpeg_bytes() -> bytes:
    img = Image.new("RGB", (80, 40), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _valid_payload(
    data: bytes,
    *,
    document_id: str = "case-001",
    mime_type: str = "image/png",
) -> dict[str, str]:
    return {
        "document_id": document_id,
        "mime_type": mime_type,
        "sha256": hashlib.sha256(data).hexdigest(),
        "content_base64": base64.b64encode(data).decode("ascii"),
    }


class StubOCR:
    def __init__(self, text: str = "", *, dpi: int = 300, lang: str = "por") -> None:
        self.text = text
        self.dpi = dpi
        self.lang = lang
        self.timeout_seconds = 15.0
        self.max_pdf_pages = 10
        self.max_image_pixels = 25_000_000
        self.calls: list[tuple[bytes, str]] = []

    def version(self) -> str:
        return "tesseract 5.4.0.20240606\n leptonica-1.84.1"

    def metadata(self) -> dict[str, object]:
        return {
            "available": True,
            "tesseract_version": "tesseract 5.4.0.20240606",
            "error": None,
        }

    def __call__(self, data: bytes, mime_type: str) -> str:
        self.calls.append((data, mime_type))
        return self.text


def test_module_runs_offline_without_settings_db_queue_or_gemini():
    script = (
        "import sys\n"
        "import comprova_lattes.experiments.review_ocr\n"
        "banned = (\n"
        "    'sqlalchemy',\n"
        "    'psycopg',\n"
        "    'redis',\n"
        "    'celery',\n"
        "    'google.genai',\n"
        "    'comprova_lattes.config',\n"
        "    'comprova_lattes.api.db',\n"
        ")\n"
        "loaded = [m for m in banned if m in sys.modules]\n"
        "sys.exit(1 if loaded else 0)\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], check=False, capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stderr


def test_loopback_host_validation_and_cli_rejects_external_bind(capsys):
    assert validate_loopback_host("127.0.0.1") == "127.0.0.1"
    assert validate_loopback_host("localhost") == "localhost"
    assert validate_loopback_host("::1") == "::1"
    assert DEFAULT_REVIEW_OCR_HOST == "127.0.0.1"
    assert DEFAULT_REVIEW_OCR_PORT == 8766

    for forbidden_host in ("0.0.0.0", "::", "192.168.1.10", "example.com"):
        with pytest.raises(ValueError, match="loopback"):
            validate_loopback_host(forbidden_host)

    assert main(["--host", "0.0.0.0", "--check"]) == 1
    assert "loopback" in capsys.readouterr().err.lower()

    assert main(["--port", "80", "--check"]) == 1
    assert "porta" in capsys.readouterr().err.lower()


def test_cors_and_loopback_host_header_enforcement():
    stub = StubOCR("Titular: PESSOA TESTE\n")
    app = create_review_ocr_app(ocr=stub, allow_testserver=True)
    client = TestClient(app)
    png_bytes = _sample_png_bytes()
    payload = _valid_payload(png_bytes)

    for allowed_origin in DEFAULT_CORS_ORIGINS:
        preflight = client.options(
            "/ocr",
            headers={
                "Origin": allowed_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers.get("access-control-allow-origin") == allowed_origin

        res = client.post("/ocr", json=payload, headers={"Origin": allowed_origin})
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == allowed_origin

    for bad_origin in ("http://evil.example.com", "http://127.0.0.1:3000", "https://localhost:5173"):
        blocked = client.post("/ocr", json=payload, headers={"Origin": bad_origin})
        assert blocked.status_code == 403
        assert blocked.json()["error_code"] == "FORBIDDEN_ORIGIN"
        assert "access-control-allow-origin" not in blocked.headers

    strict_app = create_review_ocr_app(ocr=stub, allow_testserver=False)
    strict_client = TestClient(strict_app)
    bad_host = strict_client.post("/ocr", json=payload, headers={"Host": "192.168.0.50:8766"})
    assert bad_host.status_code == 403
    assert bad_host.json()["error_code"] == "FORBIDDEN_HOST"

    ok_host = strict_client.post("/ocr", json=payload, headers={"Host": "127.0.0.1:8766"})
    assert ok_host.status_code == 200


def test_payload_limits_enforced_before_base64_decode_and_ocr():
    stub = StubOCR("Titular: PESSOA TESTE")
    small_limit = 128
    app = create_review_ocr_app(ocr=stub, max_document_bytes=small_limit)
    client = TestClient(app)

    oversized_bytes = b"\x89PNG\r\n\x1a\n" + (b"A" * 300)
    oversized_b64 = base64.b64encode(oversized_bytes).decode("ascii")
    assert len(oversized_b64) > max_base64_chars(small_limit)

    res = client.post(
        "/ocr",
        json={
            "document_id": "case-001",
            "mime_type": "image/png",
            "sha256": hashlib.sha256(oversized_bytes).hexdigest(),
            "content_base64": oversized_b64,
        },
    )
    assert res.status_code == 413
    assert res.json()["error_code"] == "PAYLOAD_TOO_LARGE"
    assert stub.calls == []

    huge_raw = b'{"document_id":"case-001","content_base64":"' + (b"A" * 8000) + b'"}'
    res_body = client.post(
        "/ocr",
        content=huge_raw,
        headers={"Content-Type": "application/json"},
    )
    assert res_body.status_code == 413
    assert res_body.json()["error_code"] == "PAYLOAD_TOO_LARGE"
    assert stub.calls == []


@pytest.mark.parametrize(
    "forbidden_field",
    ["xml", "record", "gold", "expected", "operator", "package_sha256", "private_map", "curriculum"],
)
def test_rejects_xml_gold_and_forbidden_keys_in_request(forbidden_field):
    stub = StubOCR("Titular: PESSOA TESTE")
    client = TestClient(create_review_ocr_app(ocr=stub))
    payload = _valid_payload(_sample_png_bytes())
    payload[forbidden_field] = "proibido"

    res = client.post("/ocr", json=payload)
    assert res.status_code == 422
    assert res.json()["error_code"] == "FORBIDDEN_PAYLOAD_FIELDS"
    assert stub.calls == []


def test_sha256_validation_echo_and_mime_signature_checks():
    stub = StubOCR("Titular: PESSOA TESTE\nCarga horária: 40\n")
    client = TestClient(create_review_ocr_app(ocr=stub))
    png_bytes = _sample_png_bytes()
    pdf_bytes = _sample_pdf_bytes()
    jpeg_bytes = _sample_jpeg_bytes()

    for mime, raw in (
        ("image/png", png_bytes),
        ("application/pdf", pdf_bytes),
        ("image/jpeg", jpeg_bytes),
    ):
        req = _valid_payload(raw, document_id="case-002", mime_type=mime)
        res = client.post("/ocr", json=req)
        assert res.status_code == 200
        body = res.json()
        assert body["document_id"] == "case-002"
        assert body["mime_type"] == mime
        assert body["sha256"] == req["sha256"]

    wrong_sha_req = _valid_payload(png_bytes, document_id="case-003")
    wrong_sha_req["sha256"] = hashlib.sha256(pdf_bytes).hexdigest()
    mismatch = client.post("/ocr", json=wrong_sha_req)
    assert mismatch.status_code == 422
    mismatch_json = mismatch.json()
    assert mismatch_json["error_code"] == "SHA256_MISMATCH"
    assert mismatch_json["document_id"] == "case-003"
    assert mismatch_json["expected_sha256"] == wrong_sha_req["sha256"]
    assert mismatch_json["actual_sha256"] == hashlib.sha256(png_bytes).hexdigest()

    # PNG enviado com MIME application/pdf mas hash correspondente aos bytes PNG -> assinatura falha
    spoof_mime = {
        "document_id": "case-004",
        "mime_type": "application/pdf",
        "sha256": hashlib.sha256(png_bytes).hexdigest(),
        "content_base64": base64.b64encode(png_bytes).decode("ascii"),
    }
    sig_err = client.post("/ocr", json=spoof_mime)
    assert sig_err.status_code == 422
    assert sig_err.json()["error_code"] == "MIME_SIGNATURE_MISMATCH"

    bad_mime = _valid_payload(png_bytes)
    bad_mime["mime_type"] = "text/html"
    assert client.post("/ocr", json=bad_mime).status_code == 415


def test_separates_ocr_raw_text_from_regex_fields_without_marking_absent():
    ocr_text = (
        "CERTIFICADO DE EXTENSÃO UNIVERSITÁRIA\n"
        "Texto livre adicional reconhecido pelo Tesseract fora dos rótulos.\n"
        "Titular: MARIA CLARA ALMEIDA\n"
        "Atividade: CURSO DE METODOLOGIA CIENTIFICA\n"
        "Instituição emissora: UNIVERSIDADE FEDERAL RURAL DA AMAZONIA\n"
        "Sigla da instituição: UFRA\n"
        "Identificação da instituição: UNIVERSIDADE FEDERAL RURAL DA AMAZONIA - UFRA\n"
        "Ano de início: 2022\n"
        "Ano de conclusão: 2023\n"
        "Carga horária: 60\n"
    )
    stub = StubOCR(ocr_text, dpi=300, lang="por")
    client = TestClient(create_review_ocr_app(ocr=stub))
    png_bytes = _sample_png_bytes()
    res = client.post("/ocr", json=_valid_payload(png_bytes, document_id="case-005"))
    assert res.status_code == 200
    body = res.json()

    assert not (set(body.keys()) & FORBIDDEN_KEYS)
    assert body["service_version"] == SERVICE_VERSION
    assert body["provider"] == PROVIDER_NAME
    assert body["tesseract_version"] == "tesseract 5.4.0.20240606"
    assert body["params"] == {
        "dpi": 300,
        "lang": "por",
        "timeout_ms": 15000,
        "max_pdf_pages": 10,
        "max_image_pixels": 25_000_000,
        "pdf_text_extraction": "disabled_raster_only",
        "regex_extractor": "OCRRegex",
    }
    assert body["ocr_text"] == ocr_text
    assert "Texto livre adicional reconhecido pelo Tesseract" in body["ocr_text"]

    regex_fields = body["regex_fields"]
    assert set(regex_fields.keys()) == set(FIELDS)
    assert regex_fields["holder_name"] == "MARIA CLARA ALMEIDA"
    assert regex_fields["activity_title"] == "CURSO DE METODOLOGIA CIENTIFICA"
    assert regex_fields["issuer_institution"] == "UNIVERSIDADE FEDERAL RURAL DA AMAZONIA"
    assert regex_fields["issuer_acronym"] == "UFRA"
    assert regex_fields["issuer_name_acronym_evidence"] == (
        "UNIVERSIDADE FEDERAL RURAL DA AMAZONIA - UFRA"
    )
    assert regex_fields["start_year"] == "2022"
    assert regex_fields["end_year"] == "2023"
    assert regex_fields["workload_hours"] == "60"

    # Campos não extraídos pela RegEx ficam null (e listados em unextracted_fields), nunca 'absent'/'ausente'
    assert regex_fields["event_name"] is None
    assert regex_fields["participation_role_raw"] is None
    assert regex_fields["activity_year"] is None
    assert set(body["unextracted_fields"]) == {
        "event_name",
        "participation_role_raw",
        "activity_year",
    }
    assert body["extracted_field_count"] == 8
    serialized = json.dumps(body, ensure_ascii=False).lower()
    assert '"absent"' not in serialized


def test_tesseract_errors_and_adapter_limits_return_explicit_codes(monkeypatch):
    png_bytes = _sample_png_bytes()
    pdf_bytes = _sample_pdf_bytes()

    def raise_not_found(data: bytes, mime: str) -> str:
        raise TesseractNotFoundError("tesseract.exe ausente")

    def raise_lang(data: bytes, mime: str) -> str:
        raise TesseractLanguageError("por.traineddata ausente")

    def raise_timeout(data: bytes, mime: str) -> str:
        raise TesseractTimeoutError("Timeout de 30s excedido")

    def raise_exec(data: bytes, mime: str) -> str:
        raise TesseractExecutionError("Código 2")

    for fn, expected_status, expected_code in (
        (raise_not_found, 503, "TESSERACT_NOT_FOUND"),
        (raise_lang, 503, "TESSERACT_LANGUAGE_MISSING"),
        (raise_timeout, 504, "TESSERACT_TIMEOUT"),
        (raise_exec, 502, "TESSERACT_EXECUTION_ERROR"),
    ):
        client = TestClient(create_review_ocr_app(ocr=fn))
        res = client.post("/ocr", json=_valid_payload(png_bytes))
        assert res.status_code == expected_status
        assert res.json()["error_code"] == expected_code

    # Limite de pixels e limite de páginas do PDF reutilizando o adaptador TesseractOCR real
    def ok_runner(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, "List of available languages:\npor\n", "")

    tiny_pixel_ocr = TesseractOCR(
        executable="C:/fake/tesseract.exe", max_image_pixels=1024, runner=ok_runner
    )
    pixel_client = TestClient(create_review_ocr_app(ocr=tiny_pixel_ocr))
    pixel_res = pixel_client.post("/ocr", json=_valid_payload(png_bytes))
    assert pixel_res.status_code == 422
    assert pixel_res.json()["error_code"] == "OCR_RENDER_ERROR"
    assert "pixels" in pixel_res.json()["detail"]

    import pypdfium2 as pdfium

    class FakeTenPagePdf:
        def __init__(self, data):
            pass

        def __len__(self):
            return 6

        def close(self):
            pass

    monkeypatch.setattr(pdfium, "PdfDocument", FakeTenPagePdf)
    page_cap_ocr = TesseractOCR(
        executable="C:/fake/tesseract.exe", max_pdf_pages=2, runner=ok_runner
    )
    page_client = TestClient(create_review_ocr_app(ocr=page_cap_ocr))
    page_res = page_client.post(
        "/ocr", json=_valid_payload(pdf_bytes, mime_type="application/pdf")
    )
    assert page_res.status_code == 422
    assert page_res.json()["error_code"] == "OCR_RENDER_ERROR"
    assert "2 páginas" in page_res.json()["detail"]


def test_bounded_concurrency_rejects_overlapping_requests():
    entered = threading.Event()
    release = threading.Event()

    def slow_ocr(data: bytes, mime: str) -> str:
        entered.set()
        release.wait(timeout=5.0)
        return "Titular: CONCORRENCIA OK\n"

    app = create_review_ocr_app(ocr=slow_ocr, max_concurrency=1)
    client = TestClient(app)
    payload = _valid_payload(_sample_png_bytes())

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(client.post, "/ocr", json=payload)
        assert entered.wait(timeout=3.0)
        second_res = client.post("/ocr", json=payload)
        assert second_res.status_code == 429
        assert second_res.json()["error_code"] == "OCR_CONCURRENCY_LIMIT"
        release.set()
        first_res = first_future.result(timeout=5.0)
        assert first_res.status_code == 200

    third_res = client.post("/ocr", json=payload)
    assert third_res.status_code == 200


def test_review_ocr_presets_are_explicitly_audited_without_mutating_baseline_defaults():
    assisted_ocr = build_ocr_for_preset("assisted", executable="tesseract")
    assert assisted_ocr.dpi == DEFAULT_ASSISTED_OCR_DPI == 288
    assert assisted_ocr.pdf_resampling == DEFAULT_ASSISTED_PDF_RESAMPLING == "pillow_lanczos"
    assert assisted_ocr.upscale_small_images is DEFAULT_ASSISTED_UPSCALE_SMALL_IMAGES is True
    assert assisted_ocr.psm == DEFAULT_ASSISTED_OCR_PSM == 3

    baseline_ocr = build_ocr_for_preset("baseline", executable="tesseract")
    assert baseline_ocr.dpi == 300
    assert baseline_ocr.pdf_resampling == "pdfium"
    assert baseline_ocr.upscale_small_images is False
    assert baseline_ocr.psm is None

    with pytest.raises(ValueError, match="Preset OCR inválido"):
        build_ocr_for_preset("custom", executable="tesseract")

    assisted_app = create_review_ocr_app(preset="assisted", ocr=assisted_ocr)
    assisted_health = TestClient(assisted_app).get("/health").json()
    assert assisted_health["diagnostics_version"] == ASSIST_DIAGNOSTICS_VERSION
    assert assisted_health["assist_preset"] == {
        "preset_id": ASSISTED_PRESET_ID,
        "baseline_compatible": False,
        "dpi": 288,
        "pdf_resampling": "pillow_lanczos",
        "upscale_small_images": True,
        "psm": 3,
    }

    baseline_app = create_review_ocr_app(preset="baseline", ocr=baseline_ocr)
    baseline_health = TestClient(baseline_app).get("/health").json()
    assert baseline_health["assist_preset"] == {
        "preset_id": BASELINE_PRESET_ID,
        "baseline_compatible": True,
        "dpi": 300,
        "pdf_resampling": "pdfium",
        "upscale_small_images": False,
        "psm": None,
    }


def test_invalid_year_and_syntax_suggestions_are_blocked_visibly_without_altering_raw_ocr():
    raw_ocr = (
        "DECL&RAÇHD DE PARTICIPAÇED EM EVENTO\n"
        "Titular: Vitor Ferreira\n"
        "Atividade: Seminário de Métodos Digitais\n"
        "Instituição emissora: Escola Vale Regional - EVR\n"
        "Sigla da instituição: EVR\n"
        "Identificação da instituição: Identificação da instituição: Escola Vale Regional - EVR | Sigla da instituição: EVR\n"
        "Carga horária: 40h\n"
        "Ano de início: 20381\n"
        "Ano de conclusão: 2031\n"
        "Ano da atividade: 20a1\n"
    )
    stub = StubOCR(raw_ocr, dpi=288)
    client = TestClient(create_review_ocr_app(ocr=stub))
    res = client.post("/ocr", json=_valid_payload(_sample_png_bytes()))
    assert res.status_code == 200
    body = res.json()

    # Texto bruto permanece 100% imutável e sem autocorreção silenciosa 20381 -> 2031
    assert body["ocr_text"] == raw_ocr
    assert "20381" in body["ocr_text"]
    assert "DECL&RAÇHD" in body["ocr_text"]

    # Campos inválidos não vão para regex_fields (permanecem null) e não viram ausentes
    assert body["regex_fields"]["start_year"] is None
    assert body["regex_fields"]["workload_hours"] is None
    assert body["regex_fields"]["activity_year"] is None
    assert "start_year" not in body["unextracted_fields"]
    assert "workload_hours" not in body["unextracted_fields"]
    assert "activity_year" not in body["unextracted_fields"]

    # Valores inválidos ficam visíveis + alertas claros + campos válidos irmãos sobrevivem
    assert body["invalid_regex_fields"] == {
        "start_year": "20381",
        "activity_year": "20a1",
        "workload_hours": "40h",
    }
    assert "start_year" in body["field_warnings"]
    assert "20381" in body["field_warnings"]["start_year"]
    assert "não foi corrigido nem preenchido automaticamente" in body["field_warnings"]["start_year"]
    assert "workload_hours" in body["field_warnings"]
    assert "activity_year" in body["field_warnings"]
    assert any("20381" in w for w in body["warnings"])

    assert body["regex_fields"]["holder_name"] == "Vitor Ferreira"
    assert body["regex_fields"]["end_year"] == "2031"
    assert body["regex_fields"]["issuer_institution"] == "Escola Vale Regional - EVR"
    assert body["regex_fields"]["issuer_acronym"] == "EVR"
    assert body["regex_fields"]["issuer_name_acronym_evidence"] == (
        "Identificação da instituição: Escola Vale Regional - EVR | Sigla da instituição: EVR"
    )
    # params continua restrito às 7 chaves originais de compatibilidade do draft.ts
    assert set(body["params"].keys()) == {
        "dpi",
        "lang",
        "timeout_ms",
        "max_pdf_pages",
        "max_image_pixels",
        "pdf_text_extraction",
        "regex_extractor",
    }
    assert body["extracted_field_count"] == 6
    assert body["diagnostics_version"] == ASSIST_DIAGNOSTICS_VERSION


def test_legitimate_four_digit_year_and_broken_issuer_relation_handling():
    legit_text = (
        "DECLARAÇÃO DE PARTICIPAÇÃO EM EVENTO\n"
        "Titular: Vitor Ferreira\n"
        "Atividade: Curso de Análise Documental\n"
        "Instituição emissora: Universidade Exemplo - UE\n"
        "Sigla da instituição: OUTRA\n"
        "Identificação da instituição: Evidência sem relação válida\n"
        "Carga horária: 40\n"
        "Ano de início: 2031\n"
        "Ano de conclusão: 2031\n"
        "Ano da atividade: 2031\n"
    )
    client = TestClient(create_review_ocr_app(ocr=StubOCR(legit_text)))
    body = client.post("/ocr", json=_valid_payload(_sample_png_bytes())).json()
    assert body["regex_fields"]["start_year"] == "2031"
    assert body["regex_fields"]["end_year"] == "2031"
    assert body["regex_fields"]["workload_hours"] == "40"
    # Relação instituição/sigla inconsistente é bloqueada em issuer_name_acronym_evidence sem inventar ausência
    assert body["regex_fields"]["issuer_name_acronym_evidence"] is None
    assert "issuer_name_acronym_evidence" in body["invalid_regex_fields"]
    assert "issuer_name_acronym_evidence" in body["field_warnings"]
    assert "issuer_name_acronym_evidence" not in body["unextracted_fields"]

    # Documento totalmente ilegível preserva ausência real sem falsos alertas inválidos
    illegible = client.post(
        "/ocr",
        json=_valid_payload(_sample_png_bytes()),
    )
    assert illegible.status_code == 200
    empty_client = TestClient(create_review_ocr_app(ocr=StubOCR("...   \n")))
    empty_body = empty_client.post("/ocr", json=_valid_payload(_sample_png_bytes())).json()
    assert empty_body["extracted_field_count"] == 0
    assert empty_body["invalid_regex_fields"] == {}
    assert empty_body["field_warnings"] == {}
    assert set(empty_body["unextracted_fields"]) == set(FIELDS)


def test_package_hashes_unchanged_and_frontend_async_protocol_preserves_xml_and_base_hashes():
    """Verifica que o pacote `annotation-package-v1` mantém a versão e os hashes intactos
    e executa os helpers TypeScript (`package.ts`, `draft.ts`, `ocr.ts`) via Node/Vite para
    comprovar:
    1) funcionamento manual sem servidor OCR;
    2) auxílio OCR assíncrono não esconde nem altera XML, `xml_sha256`, `document_sha256` ou `package_sha256`;
    3) rejeição de resposta OCR trocada (hash/document_id divergente);
    4) ausência de extração na RegEx não marca campo como ausente;
    5) compatibilidade de importação `annotation-export-v1` e bloqueio de mistura silenciosa entre
       rascunhos `unassisted` e `ocr_assisted`.
    """
    corpus = generate(seed=42, pilot_families=5, final_families=5)
    built = build_package(corpus)
    assert built.package["package_version"] == PACKAGE_VERSION == "annotation-package-v1"
    assert built.package["package_sha256"] == compute_package_sha256(built.package)
    validate_package(built.package)

    doc_case = next(c for c in built.package["cases"] if c["document"] is not None)
    stub_text = (
        "CERTIFICADO DE TESTE\n"
        "Titular: PESSOA EXEMPLO OCR\n"
        "Carga horária: 40\n"
    )
    stub = StubOCR(stub_text)
    client = TestClient(create_review_ocr_app(ocr=stub))
    ocr_http_res = client.post(
        "/ocr",
        json={
            "document_id": doc_case["case_id"],
            "mime_type": doc_case["document"]["mime_type"],
            "sha256": doc_case["document"]["sha256"],
            "content_base64": doc_case["document"]["content_base64"],
        },
    )
    assert ocr_http_res.status_code == 200
    ocr_response_json = ocr_http_res.json()

    node_script = """
import { createServer } from 'vite';

const server = await createServer({
  root: process.cwd(),
  logLevel: 'silent',
  server: { middlewareMode: true },
});

try {
  const pkgMod = await server.ssrLoadModule('/src/lib/annotation/package.ts');
  const draftMod = await server.ssrLoadModule('/src/lib/annotation/draft.ts');
  const ocrMod = await server.ssrLoadModule('/src/lib/annotation/ocr.ts');
  const canonicalMod = await server.ssrLoadModule('/src/lib/annotation/canonical.ts');

  const input = JSON.parse(process.env.TEST_PAYLOAD_JSON);
  const pkg = await pkgMod.parseAnnotationPackage(JSON.stringify(input.package));
  if (pkg.package_sha256 !== input.package.package_sha256) {
    throw new Error('package_sha256 alterado na leitura TS');
  }

  const targetCaseId = input.docCaseId;
  const pkgCase = pkg.cases.find(c => c.case_id === targetCaseId);
  const originalXmlText = pkgMod.decodeXml(pkgCase);
  const originalXmlSha = pkgCase.xml.sha256;
  const originalDocSha = pkgCase.document.sha256;

  // 1) Req payload contém exclusivamente document_id, mime_type, sha256 e content_base64 (sem XML/record)
  const reqPayload = ocrMod.buildOcrRequestPayload(pkgCase);
  const reqKeys = Object.keys(reqPayload).sort().join(',');
  if (reqKeys !== 'content_base64,document_id,mime_type,sha256') {
    throw new Error('Payload OCR contém chaves inesperadas: ' + reqKeys);
  }

  // 2) Comportamento manual sem servidor OCR (offline failure não bloqueia edição nem altera hashes)
  let unassistedDraft = draftMod.newDraft(pkg, 'Caleb', new Date('2026-11-15T18:00:00Z'), 'unassisted');
  if (unassistedDraft.review_mode !== 'unassisted' || unassistedDraft.evaluation_condition !== 'independent_unassisted_human_review') {
    throw new Error('Condição inicial deveria ser unassisted');
  }

  // 3) Verifica resposta OCR real do endpoint e rejeita resposta trocada (hash/id diferente)
  const verifiedOcr = ocrMod.validateOcrResponse(input.ocrResponse, {
    document_id: pkgCase.case_id,
    mime_type: pkgCase.document.mime_type,
    sha256: pkgCase.document.sha256,
  });

  let swapRejected = false;
  try {
    ocrMod.validateOcrResponse(
      { ...input.ocrResponse, sha256: '0'.repeat(64) },
      {
        document_id: pkgCase.case_id,
        mime_type: pkgCase.document.mime_type,
        sha256: pkgCase.document.sha256,
      },
    );
  } catch {
    swapRejected = true;
  }
  if (!swapRejected) throw new Error('Deveria rejeitar resposta OCR com SHA-256 trocado');

  // 4) Edição manual em andamento antes de chegar resposta assíncrona do OCR
  let assistedDraft = draftMod.enableOcrAssistedMode(unassistedDraft, new Date('2026-11-15T18:01:00Z'));
  assistedDraft = {
    ...assistedDraft,
    cases: {
      ...assistedDraft.cases,
      [targetCaseId]: {
        ...assistedDraft.cases[targetCaseId],
        phase1: {
          ...assistedDraft.cases[targetCaseId].phase1,
          fields: {
            ...assistedDraft.cases[targetCaseId].phase1.fields,
            event_name: { state: 'absent', value: '' },
          },
        },
      },
    },
  };

  // Resposta assíncrona chega: NÃO preenche campos automaticamente e NÃO esconde/altera XML nem hashes base
  assistedDraft = draftMod.applyAsyncOcrResult(
    assistedDraft,
    targetCaseId,
    verifiedOcr,
    new Date('2026-11-15T18:02:00Z'),
  );
  const afterOcrCase = assistedDraft.cases[targetCaseId];
  if (assistedDraft.package_sha256 !== pkg.package_sha256) throw new Error('package_sha256 alterado após OCR assíncrono');
  if (afterOcrCase.xml_sha256 !== originalXmlSha) throw new Error('xml_sha256 alterado após OCR assíncrono');
  if (afterOcrCase.document_sha256 !== originalDocSha) throw new Error('document_sha256 alterado após OCR assíncrono');
  if (pkgMod.decodeXml(pkgCase) !== originalXmlText) throw new Error('XML decodificado alterado');
  if (afterOcrCase.phase1.fields.holder_name.state !== null || afterOcrCase.phase1.fields.holder_name.value !== '') {
    throw new Error('OCR não pode preencher automaticamente campos em branco');
  }
  if (afterOcrCase.phase1.fields.event_name.state !== 'absent') {
    throw new Error('Resposta assíncrona do OCR perdeu edição manual anterior');
  }
  if (afterOcrCase.ocr_assistance.assisted_before_completion !== true) {
    throw new Error('assisted_before_completion deve ser true quando OCR ocorre antes da conclusão');
  }
  if (assistedDraft.evaluation_condition !== 'ocr_assisted_human_review') {
    throw new Error('Condição do rascunho deve ser ocr_assisted_human_review');
  }

  // 5) Campo não extraído pela RegEx (null) jamais pode ser copiado ou marcado como ausente pelo helper
  let unextractedBlocked = false;
  try {
    draftMod.recordOcrCopyField(afterOcrCase, 'activity_year', true);
  } catch {
    unextractedBlocked = true;
  }
  if (!unextractedBlocked) throw new Error('Campo null na RegEx não pode ser aplicado');
  if (afterOcrCase.phase1.fields.activity_year.state !== null) {
    throw new Error('Campo não extraído pela RegEx não pode receber estado automático');
  }

  // 6) Cópia explícita pelo botão de um campo extraído + possibilidade de rejeição manual preservando auditoria
  let caseWithCopy = draftMod.recordOcrCopyRawText(afterOcrCase, new Date('2026-11-15T18:03:00Z'));
  caseWithCopy = draftMod.recordOcrCopyField(caseWithCopy, 'holder_name', true, new Date('2026-11-15T18:03:05Z'));
  if (caseWithCopy.phase1.fields.holder_name.state !== 'present' || caseWithCopy.phase1.fields.holder_name.value !== 'PESSOA EXEMPLO OCR') {
    throw new Error('Falha ao aplicar valor explicitamente solicitado pelo usuário');
  }
  const rejectedCase = draftMod.rejectOcrFieldSuggestion(caseWithCopy, 'holder_name');
  if (rejectedCase.phase1.fields.holder_name.state !== null || rejectedCase.phase1.fields.holder_name.value !== '') {
    throw new Error('Falha ao rejeitar manualmente sugestão OCR');
  }
  if (!rejectedCase.ocr_assistance.observable_copied_fields.includes('holder_name')) {
    throw new Error('Rejeição manual não deve apagar o histórico auditável de que o OCR foi consultado');
  }

  assistedDraft = {
    ...assistedDraft,
    cases: { ...assistedDraft.cases, [targetCaseId]: caseWithCopy },
  };

  // 7) Exportação v2 assistida + verificação de hash canônico e reimportação com bloqueio de mistura silenciosa
  const exportedV2 = await draftMod.buildExport(assistedDraft, pkg, 'draft', new Date('2026-11-15T18:04:00Z'));
  if (exportedV2.export_version !== 'annotation-export-v2') throw new Error('Versão v2 esperada');
  if (exportedV2.review_mode !== 'ocr_assisted' || exportedV2.evaluation_condition !== 'ocr_assisted_human_review') {
    throw new Error('Metadados de condição assistida ausentes na exportação v2');
  }

  let mixBlocked = false;
  try {
    await draftMod.parseExport(JSON.stringify(exportedV2), pkg, 'Caleb', {
      expectedMode: 'unassisted',
      allowModeSwitch: false,
    });
  } catch {
    mixBlocked = true;
  }
  if (!mixBlocked) throw new Error('Mistura silenciosa entre rascunho assistido e sessão não assistida deveria ser bloqueada');

  const reimportedV2 = await draftMod.parseExport(JSON.stringify(exportedV2), pkg, 'Caleb', {
    expectedMode: 'ocr_assisted',
  });
  if (reimportedV2.cases[targetCaseId].ocr_assistance.provider !== 'tesseract-local') {
    throw new Error('Rastreabilidade do provedor OCR perdida na reimportação v2');
  }

  // 8) Compatibilidade retroativa com exportação legada annotation-export-v1
  const v1Cases = pkg.cases.map(c => {
    const empty = draftMod.emptyCase(c);
    const { ocr_assistance: _omit, ...legacyCase } = empty;
    return legacyCase;
  });
  const v1Body = {
    export_version: 'annotation-export-v1',
    kind: 'draft',
    package_version: pkg.package_version,
    guide_version: pkg.guide_version,
    package_sha256: pkg.package_sha256,
    reviewer: 'Caleb',
    exported_at: '2026-11-15T17:00:00.000Z',
    cases: v1Cases,
  };
  const v1Sha = await canonicalMod.canonicalSha256(v1Body);
  const v1Export = { ...v1Body, annotation_sha256: v1Sha };

  const migratedDraft = await draftMod.parseExport(JSON.stringify(v1Export), pkg, 'Caleb', {
    expectedMode: 'unassisted',
  });
  if (migratedDraft.review_mode !== 'unassisted' || migratedDraft.migrated_from_export_version !== 'annotation-export-v1') {
    throw new Error('Migração de annotation-export-v1 não preservou metadados esperados');
  }

  // 9) Renderização SSR dos componentes React (DocumentPhase + OcrAssistPanel + ComparisonPhase)
  const React = await import('react');
  const { renderToStaticMarkup } = await import('react-dom/server');
  const docPhaseMod = await server.ssrLoadModule('/src/components/annotation/DocumentPhase.tsx');
  const compPhaseMod = await server.ssrLoadModule('/src/components/annotation/ComparisonPhase.tsx');

  const docHtml = renderToStaticMarkup(
    React.createElement(docPhaseMod.DocumentPhase, {
      pkgCase,
      annotation: assistedDraft.cases[targetCaseId],
      reviewMode: 'ocr_assisted',
      onChange: () => {},
      onOptInAndRead: () => {},
      onOcrSuccess: () => {},
      onOcrFailure: () => {},
    }),
  );
  if (!docHtml.includes('Texto bruto reconhecido pelo Tesseract') || !docHtml.includes('Valores recortados por expressão regular')) {
    throw new Error('Painel OCR não renderizou blocos separados de texto bruto e RegEx');
  }
  if (!docHtml.includes('Não extraído pela RegEx')) {
    throw new Error('Painel OCR não indicou ausência de extração na RegEx');
  }

  const savedCase = {
    ...assistedDraft.cases[targetCaseId],
    phase1: {
      ...assistedDraft.cases[targetCaseId].phase1,
      status: 'saved',
      saved_at: '2026-11-15T18:05:00.000Z',
    },
    phase2: draftMod.emptyPhase2(),
  };
  const compHtml = renderToStaticMarkup(
    React.createElement(compPhaseMod.ComparisonPhase, {
      pkgCase,
      annotation: savedCase,
      onChange: () => {},
    }),
  );
  if (!compHtml.includes('2. Compare com o que foi declarado no currículo') || !compHtml.includes('Auxílio OCR consultado:')) {
    throw new Error('ComparisonPhase não exibiu XML ou rastreabilidade OCR');
  }

  // 10) Regressão de sugestão inválida (ano de 5 dígitos 20381 vs legítimo 2031): defesa no cliente e painel sem auto-correção
  const injectedInvalidRes = {
    ...input.ocrResponse,
    ocr_text:
      'DECL&RAÇHD DE PARTICIPAÇED EM EVENTO\\n' +
      'Titular: PESSOA EXEMPLO OCR\\n' +
      'Carga horária: 40h\\n' +
      'Ano de início: 20381\\n' +
      'Ano de conclusão: 2031\\n',
    regex_fields: {
      ...input.ocrResponse.regex_fields,
      holder_name: 'PESSOA EXEMPLO OCR',
      workload_hours: '40h',
      start_year: '20381',
      end_year: '2031',
    },
    extracted_field_count: 4,
    unextracted_fields: input.ocrResponse.unextracted_fields.filter(
      f => f !== 'holder_name' && f !== 'workload_hours' && f !== 'start_year' && f !== 'end_year',
    ),
  };
  const sanitized = ocrMod.validateOcrResponse(injectedInvalidRes, {
    document_id: pkgCase.case_id,
    mime_type: pkgCase.document.mime_type,
    sha256: pkgCase.document.sha256,
  });
  if (sanitized.regex_fields.start_year !== null || sanitized.regex_fields.workload_hours !== null) {
    throw new Error('Cliente TS permitiu sugestão sintaticamente inválida em regex_fields');
  }
  if (sanitized.regex_fields.end_year !== '2031') {
    throw new Error('Cliente TS descartou ano legítimo 2031');
  }
  if (!sanitized.ocr_text.includes('20381') || !sanitized.ocr_text.includes('DECL&RAÇHD')) {
    throw new Error('Cliente TS adulterou texto bruto OCR');
  }
  if (sanitized.invalid_regex_fields.start_year !== '20381' || sanitized.invalid_regex_fields.workload_hours !== '40h') {
    throw new Error('Cliente TS não preservou invalid_regex_fields visíveis para conferência');
  }
  if (sanitized.unextracted_fields.includes('start_year') || sanitized.unextracted_fields.includes('workload_hours')) {
    throw new Error('Captura inválida virou campo ausente na lista unextracted_fields');
  }

  let invalidAppliedDraft = draftMod.applyAsyncOcrResult(assistedDraft, targetCaseId, sanitized);
  if (invalidAppliedDraft.cases[targetCaseId].phase1.fields.start_year.value !== '') {
    throw new Error('Ano inválido 20381 preencheu silenciosamente campo Phase1');
  }
  let blockedApplyRejected = false;
  try {
    invalidAppliedDraft = draftMod.recordOcrCopyField(invalidAppliedDraft, targetCaseId, 'start_year', true);
  } catch {
    blockedApplyRejected = true;
  }
  if (!blockedApplyRejected) {
    throw new Error('recordOcrCopyField aceitou aplicar campo inválido bloqueado');
  }

  // Simula recarregamento do rascunho apenas do localStorage (sem latestResponse em memória)
  const inspectedReloaded = ocrMod.inspectCaseOcrAssistance(invalidAppliedDraft.cases[targetCaseId].ocr_assistance, null);
  if (inspectedReloaded.invalidFields.start_year !== '20381' || inspectedReloaded.validFields.end_year !== '2031') {
    throw new Error('inspectCaseOcrAssistance não recuperou captura inválida/válida do ocr_raw_text após recarga');
  }

  const invalidPanelHtml = renderToStaticMarkup(
    React.createElement(docPhaseMod.DocumentPhase, {
      pkgCase,
      annotation: invalidAppliedDraft.cases[targetCaseId],
      reviewMode: 'ocr_assisted',
      onChange: () => {},
      onOptInAndRead: () => {},
      onOcrSuccess: () => {},
      onOcrFailure: () => {},
    }),
  );
  if (
    !invalidPanelHtml.includes('20381') ||
    !invalidPanelHtml.includes('Captura RegEx inválida (bloqueada)') ||
    !invalidPanelHtml.includes('Alertas de validação OCR (2 campo(s) bloqueado(s)):')
  ) {
    throw new Error('OcrAssistPanel não exibiu alerta claro nem valor inválido visível para 20381/40h');
  }
  const startYearRowStart = invalidPanelHtml.indexOf('<strong>Ano de início</strong>');
  const endYearRowStart = invalidPanelHtml.indexOf('<strong>Ano de conclusão</strong>');
  if (startYearRowStart < 0 || endYearRowStart <= startYearRowStart) {
    throw new Error('Linhas de Ano de início / Ano de conclusão não encontradas no painel OCR');
  }
  const startYearRowHtml = invalidPanelHtml.slice(startYearRowStart, endYearRowStart);
  if (startYearRowHtml.includes('Usar no campo') || startYearRowHtml.includes('Não extraído pela RegEx')) {
    throw new Error('Linha de Ano de início inválido exibiu botão de preenchimento ou marcou Não extraído pela RegEx');
  }
} finally {
  await server.close();
}
"""
    import os
    from pathlib import Path

    app_dir = Path(__file__).resolve().parents[2] / "comprova-lattes-app"
    env = dict(os.environ)
    env["TEST_PAYLOAD_JSON"] = json.dumps(
        {
            "package": built.package,
            "docCaseId": doc_case["case_id"],
            "ocrResponse": ocr_response_json,
        }
    )
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", node_script],
        cwd=str(app_dir),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"Falha no teste de protocolo TS:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.10"])
def test_external_bind_stays_forbidden_without_container_opt_in(host):
    from comprova_lattes.experiments.review_ocr import resolve_bind_host

    with pytest.raises(ValueError):
        resolve_bind_host(host)


def test_container_bind_requires_explicit_flag_and_wildcard():
    from comprova_lattes.experiments.review_ocr import build_arg_parser, resolve_bind_host

    args = build_arg_parser().parse_args(["--container-bind", "--host", "0.0.0.0"])
    assert resolve_bind_host(args.host, container_bind=args.container_bind) == "0.0.0.0"
    assert resolve_bind_host("127.0.0.1") == "127.0.0.1"
    for host in ("127.0.0.1", "192.168.1.10", "::"):
        with pytest.raises(ValueError):
            resolve_bind_host(host, container_bind=True)
