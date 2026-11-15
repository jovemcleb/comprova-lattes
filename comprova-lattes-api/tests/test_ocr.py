"""Testes unitários (mocks/limites/contrato PT) e smoke real do adaptador Tesseract OCR."""

import io
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest
from PIL import Image

from comprova_lattes.experiments.baseline import FIELD_LABELS_PT, FIELDS, PATTERNS, OCRRegex
from comprova_lattes.experiments.ocr import (
    OCRRenderError,
    TesseractExecutionError,
    TesseractLanguageError,
    TesseractNotFoundError,
    TesseractOCR,
    TesseractTimeoutError,
    ocr_environment_metadata,
    resolve_tesseract_executable,
)
from comprova_lattes.experiments.ocr import (
    main as ocr_cli_main,
)
from comprova_lattes.experiments.render import pdf, png, raster
from comprova_lattes.experiments.synthetic import document_text, generate
from comprova_lattes.matcher.models import ExtractedDocumentRecord


def _make_jpeg_bytes(width: int = 120, height: int = 60) -> bytes:
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def test_field_labels_pt_contract_exact_mapping():
    expected = {
        "holder_name": "Titular",
        "activity_title": "Atividade",
        "event_name": "Evento",
        "participation_role_raw": "Papel",
        "issuer_institution": "Instituição emissora",
        "issuer_acronym": "Sigla da instituição",
        "issuer_name_acronym_evidence": "Identificação da instituição",
        "start_year": "Ano de início",
        "end_year": "Ano de conclusão",
        "activity_year": "Ano da atividade",
        "workload_hours": "Carga horária",
    }
    assert FIELD_LABELS_PT == expected
    assert set(FIELD_LABELS_PT) == set(FIELDS)
    assert set(PATTERNS) == set(FIELDS)


def test_ocr_regex_legacy_technical_and_pt_contract_labels_compatibility():
    legacy_text = (
        "CERTIFICADO FICTICIO\n"
        "holder_name: PESSOA  FICTICIA  ABC123\n"
        "activity_title: XURSO SINTETICO ABC123\n"
        "event_name: EVENTO FICTICIO ABC123\n"
        "participation_role_raw: APRESENTADOR\n"
        "issuer_institution: INSTITUTO FICTICIO ABC123\n"
        "issuer_acronym: IFABC123\n"
        "issuer_name_acronym_evidence: INSTITUTO FICTICIO ABC123 - IFABC123\n"
        "start_year: 2020\n"
        "end_year: 2024\n"
        "activity_year: 2024\n"
        "workload_hours: 40.5"
    )
    pt_text = (
        "CERTIFICADO DE APRESENTAÇÃO DE TRABALHO\n"
        "Registro sintético de apresentação de trabalho para conferência documental.\n"
        "Carga horária: 40.5\n"
        "Identificação da instituição: INSTITUTO FICTICIO ABC123 - IFABC123\n"
        "Sigla da instituição: IFABC123\n"
        "Instituição emissora: INSTITUTO FICTICIO ABC123\n"
        "Ano da atividade: 2024\n"
        "Ano de conclusão: 2024\n"
        "Ano de início: 2020\n"
        "Papel: APRESENTADOR\n"
        "Evento: EVENTO FICTICIO ABC123\n"
        "Atividade: XURSO SINTETICO ABC123\n"
        "Titular: PESSOA  FICTICIA  ABC123"
    )
    rec_legacy = OCRRegex(lambda *_: legacy_text).extract("doc-1", b"png", "image/png")
    rec_pt = OCRRegex(lambda *_: pt_text).extract("doc-1", b"png", "image/png")

    assert rec_legacy.extraction_status == "OK"
    assert rec_pt == rec_legacy
    assert rec_pt.holder_name == "PESSOA  FICTICIA  ABC123"
    assert rec_pt.issuer_institution == "INSTITUTO FICTICIO ABC123"
    assert rec_pt.issuer_acronym == "IFABC123"
    assert rec_pt.issuer_name_acronym_evidence == "INSTITUTO FICTICIO ABC123 - IFABC123"
    assert rec_pt.workload_hours == Decimal("40.5")
    assert rec_pt.start_year == 2020
    assert rec_pt.end_year == 2024
    assert rec_pt.activity_year == 2024


def test_ocr_regex_institution_acronym_and_evidence_never_cross_contaminate():
    # Garante que "Sigla da instituição" e "Identificação da instituição" não
    # sejam capturados como "Instituição emissora", nem incluam o rótulo no valor,
    # e que rótulo vazio seguido de quebra de linha não capture a linha seguinte.
    text_only_acronym_and_years = (
        "DECLARAÇÃO DE PARTICIPAÇÃO EM EVENTO\n"
        "Titular: \r\n"
        "Atividade: PALESTRA MAGNA\n"
        "Sigla da instituição: UFRA\n"
        "Ano de conclusão: 2024\n"
        "Carga horária: 12"
    )
    rec = OCRRegex(lambda *_: text_only_acronym_and_years).extract("doc-2", b"x", "image/png")
    assert rec.extraction_status == "OK"
    assert rec.holder_name is None
    assert rec.activity_title == "PALESTRA MAGNA"
    assert rec.issuer_acronym == "UFRA"
    assert rec.issuer_institution is None
    assert rec.issuer_name_acronym_evidence is None
    assert rec.start_year is None
    assert rec.end_year == 2024
    assert rec.activity_year is None
    assert rec.workload_hours == Decimal(12)


def test_ocr_regex_error_statuses_and_unknown_pattern_rejection():
    with pytest.raises(ValueError, match="Regex de campo desconhecido"):
        OCRRegex(lambda *_: "ok", patterns={"campo_inexistente": r".*"})

    def raise_timeout(data: bytes, mime: str) -> str:
        raise TesseractTimeoutError("Timeout simulado")

    def raise_subprocess_err(data: bytes, mime: str) -> str:
        raise subprocess.SubprocessError("Falha de subprocesso")

    assert (
        OCRRegex(raise_timeout).extract("d1", b"1", "image/png").extraction_status == "API_ERROR"
    )
    assert (
        OCRRegex(raise_subprocess_err).extract("d2", b"1", "image/png").extraction_status
        == "API_ERROR"
    )
    assert (
        OCRRegex(lambda *_: "   \n\t  ").extract("d3", b"1", "image/png").extraction_status
        == "UNREADABLE"
    )
    # Evidência institucional sem a sigla presente invalida o contrato Pydantic -> INVALID_JSON
    broken_evidence = (
        "Instituição emissora: INSTITUTO FICTICIO 99\n"
        "Sigla da instituição: IF99\n"
        "Identificação da instituição: INSTITUTO FICTICIO 99 - OUTRASIGLA"
    )
    assert (
        OCRRegex(lambda *_: broken_evidence).extract("d4", b"1", "image/png").extraction_status
        == "INVALID_JSON"
    )


def test_subprocess_invocation_without_shell_and_tempdir_cleanup():
    w, h, px = raster("CERTIFICADO\nTitular: TESTE", seed=1, degradation=0, layout=0)
    png_bytes = png(w, h, px)
    pdf_bytes = pdf(w, h, px)
    jpeg_bytes = _make_jpeg_bytes()

    calls: list[dict[str, object]] = []
    observed_temp_files: list[Path] = []

    def fake_runner(args, **kwargs):
        calls.append({"args": list(args), "kwargs": dict(kwargs)})
        if "--list-langs" in args:
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout='List of available languages in "C:/tessdata/" (2):\neng\npor\n',
                stderr="",
            )
        img_arg = Path(args[1])
        assert img_arg.is_file(), "Imagem temporária deve existir durante a chamada ao Tesseract"
        assert img_arg.suffix == ".png"
        observed_temp_files.append(img_arg)
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="Titular: PESSOA TESTE\nCarga horária: 20\n",
            stderr="",
        )

    ocr = TesseractOCR(
        executable="C:/fake/tesseract.exe",
        lang="por",
        dpi=200,
        timeout_seconds=12.5,
        runner=fake_runner,
    )

    for mime, payload in (
        ("image/png", png_bytes),
        ("image/jpeg", jpeg_bytes),
        ("application/pdf", pdf_bytes),
    ):
        out = ocr(payload, mime)
        assert "Titular: PESSOA TESTE" in out

    # 1 chamada a --list-langs (cacheada na instância) + 3 chamadas de OCR
    assert len(calls) == 4
    for call in calls:
        assert call["kwargs"]["shell"] is False
        assert call["kwargs"]["timeout"] == 12.5
        assert call["kwargs"]["check"] is False
    for ocr_call in calls[1:]:
        cmd = ocr_call["args"]
        assert cmd[0] == str(Path("C:/fake/tesseract.exe"))
        assert cmd[2:] == ["stdout", "-l", "por", "--dpi", "200"]

    assert len(observed_temp_files) == 3
    for temp_file in observed_temp_files:
        assert not temp_file.exists(), "Arquivo temporário deveria ter sido removido após OCR"
        assert not temp_file.parent.exists(), "Diretório temporário deveria ter sido removido"


def test_pdf_rasterization_does_not_extract_embedded_text_and_enforces_page_limit(monkeypatch):
    import pypdfium2 as pdfium

    w, h, px = raster("CERTIFICADO\nTitular: RASTER", seed=2, degradation=0, layout=0)
    pdf_bytes = pdf(w, h, px)

    def forbidden_get_textpage(*args, **kwargs):
        raise AssertionError("get_textpage não pode ser chamado no adaptador OCR raster!")

    monkeypatch.setattr(pdfium.PdfPage, "get_textpage", forbidden_get_textpage)

    def fake_runner(args, **kwargs):
        if "--list-langs" in args:
            return subprocess.CompletedProcess(args, 0, "List of available languages:\npor\n", "")
        return subprocess.CompletedProcess(args, 0, "Titular: RASTER\n", "")

    ocr = TesseractOCR(executable="C:/fake/tesseract.exe", runner=fake_runner)
    assert ocr(pdf_bytes, "application/pdf").strip() == "Titular: RASTER"

    class FakeMultiPagePdf:
        def __init__(self, data):
            pass

        def __len__(self):
            return 5

        def close(self):
            pass

    monkeypatch.setattr(pdfium, "PdfDocument", FakeMultiPagePdf)
    ocr_limited = TesseractOCR(
        executable="C:/fake/tesseract.exe", max_pdf_pages=2, runner=fake_runner
    )
    with pytest.raises(OCRRenderError, match="excedendo o limite configurado de 2 páginas"):
        ocr_limited(pdf_bytes, "application/pdf")


def test_missing_portuguese_language_detected_in_list_langs_and_stderr():
    w, h, px = raster("Titular: TESTE", seed=1, degradation=0, layout=0)
    png_bytes = png(w, h, px)

    def runner_without_por(args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout='List of available languages in "C:/tessdata/" (2):\neng\nosd\n',
            stderr="",
        )

    ocr_missing = TesseractOCR(
        executable="C:/fake/tesseract.exe", lang="por", runner=runner_without_por
    )
    with pytest.raises(TesseractLanguageError, match="por\\.traineddata"):
        ocr_missing(png_bytes, "image/png")

    temp_files: list[Path] = []

    def runner_stderr_lang_error(args, **kwargs):
        if "--list-langs" in args:
            return subprocess.CompletedProcess(args, 0, "List of available languages:\npor\n", "")
        temp_files.append(Path(args[1]))
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="Error opening data file C:/tessdata/por.traineddata\nFailed loading language 'por'",
        )

    ocr_stderr = TesseractOCR(
        executable="C:/fake/tesseract.exe", lang="por", runner=runner_stderr_lang_error
    )
    with pytest.raises(TesseractLanguageError, match="falhou ao carregar o idioma 'por'"):
        ocr_stderr(png_bytes, "image/png")
    assert temp_files and not temp_files[0].parent.exists()


def test_timeout_and_nonzero_exit_code_raise_explicit_errors_and_cleanup_tempdir():
    w, h, px = raster("Titular: TESTE", seed=1, degradation=0, layout=0)
    png_bytes = png(w, h, px)
    temp_dirs: list[Path] = []

    def runner_timeout(args, **kwargs):
        if "--list-langs" in args:
            return subprocess.CompletedProcess(args, 0, "List of available languages:\npor\n", "")
        temp_dirs.append(Path(args[1]).parent)
        raise subprocess.TimeoutExpired(cmd=args, timeout=kwargs["timeout"])

    ocr_timeout = TesseractOCR(
        executable="C:/fake/tesseract.exe", timeout_seconds=1.5, runner=runner_timeout
    )
    with pytest.raises(TesseractTimeoutError, match="Timeout de 1.5s excedido"):
        ocr_timeout(png_bytes, "image/png")
    assert temp_dirs and not temp_dirs[0].exists()

    def runner_crash(args, **kwargs):
        if "--list-langs" in args:
            return subprocess.CompletedProcess(args, 0, "List of available languages:\npor\n", "")
        temp_dirs.append(Path(args[1]).parent)
        return subprocess.CompletedProcess(args, 2, stdout="", stderr="Leptonica internal error")

    ocr_crash = TesseractOCR(executable="C:/fake/tesseract.exe", runner=runner_crash)
    with pytest.raises(TesseractExecutionError, match="código 2"):
        ocr_crash(png_bytes, "image/png")
    assert not temp_dirs[-1].exists()
    assert (
        OCRRegex(ocr_crash).extract("doc-err", png_bytes, "image/png").extraction_status
        == "API_ERROR"
    )


def test_mime_validation_corrupt_bytes_and_parameter_bounds():
    w, h, px = raster("Titular: TESTE", seed=1, degradation=0, layout=0)
    png_bytes = png(w, h, px)

    def ok_runner(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, "List of available languages:\npor\n", "")

    ocr = TesseractOCR(executable="C:/fake/tesseract.exe", runner=ok_runner)

    with pytest.raises(ValueError, match="MIME type não suportado"):
        ocr(png_bytes, "text/plain")
    with pytest.raises(ValueError, match="MIME type não suportado"):
        ocr(png_bytes, "image/webp")
    with pytest.raises(ValueError, match="bytes não vazios"):
        ocr(b"", "image/png")

    # PNG enviado como image/jpeg deve ser rejeitado na validação de formato Pillow
    with pytest.raises(OCRRenderError, match="incompatível com MIME"):
        ocr(png_bytes, "image/jpeg")
    with pytest.raises(OCRRenderError):
        ocr(b"not-a-valid-png", "image/png")
    with pytest.raises(OCRRenderError):
        ocr(b"%PDF-corrupt", "application/pdf")

    ocr_tiny_pixels = TesseractOCR(
        executable="C:/fake/tesseract.exe", max_image_pixels=1024, runner=ok_runner
    )
    with pytest.raises(OCRRenderError, match="acima do limite"):
        ocr_tiny_pixels(png_bytes, "image/png")

    for bad_kwargs in (
        {"lang": "   "},
        {"dpi": 50},
        {"dpi": 900},
        {"dpi": True},
        {"timeout_seconds": 0},
        {"timeout_seconds": 500},
        {"timeout_seconds": False},
        {"max_pdf_pages": 0},
        {"max_image_pixels": 100},
    ):
        with pytest.raises(ValueError):
            TesseractOCR(**bad_kwargs)


def test_executable_discovery_and_missing_binary_handling(monkeypatch, tmp_path):
    fake_bin = tmp_path / "tesseract.exe"
    fake_bin.write_bytes(b"MZ")

    assert resolve_tesseract_executable(fake_bin) == fake_bin.resolve()
    monkeypatch.setenv("TESSERACT_CMD", str(fake_bin))
    assert resolve_tesseract_executable() == fake_bin.resolve()

    monkeypatch.setenv("TESSERACT_CMD", str(tmp_path / "inexistente.exe"))
    with pytest.raises(TesseractNotFoundError, match="TESSERACT_CMD"):
        resolve_tesseract_executable()

    monkeypatch.delenv("TESSERACT_CMD", raising=False)
    with pytest.raises(TesseractNotFoundError):
        resolve_tesseract_executable(tmp_path / "nao_existe.exe")


def test_real_tesseract_version_and_por_language_verified():
    meta = ocr_environment_metadata()
    assert meta["available"] is True, f"Tesseract real indisponível: {meta}"
    assert meta["tesseract_version"] and "tesseract" in meta["tesseract_version"].lower()
    assert "por" in meta["available_languages"]
    assert meta["language_available"] is True
    assert meta["pillow_version"]
    assert meta["pypdfium2_version"]
    assert meta["pdf_text_extraction"] == "disabled_raster_only"


def test_real_tesseract_smoke_png_jpeg_and_pdf_fixed_and_pilot_only(tmp_path, capsys):
    # Smoke real restrito a texto fixo de teste e amostra piloto sintética (nunca final).
    fixed_record = ExtractedDocumentRecord(
        document_id="smoke-fixed",
        holder_name="PESSOA FICTICIA TESTE",
        activity_title="CURSO SINTETICO TESTE",
        issuer_institution="INSTITUTO FICTICIO TESTE",
        start_year=2020,
        end_year=2024,
        activity_year=2024,
        workload_hours=Decimal(40),
    )
    fixed_text = document_text(fixed_record, layout=0)
    w, h, px = raster(fixed_text, seed=1, degradation=0, layout=0)
    fixed_png = png(w, h, px)
    fixed_pdf = pdf(w, h, px)
    with Image.open(io.BytesIO(fixed_png)) as pil_img:
        jpeg_buf = io.BytesIO()
        pil_img.convert("RGB").save(jpeg_buf, format="JPEG", quality=95)
        fixed_jpeg = jpeg_buf.getvalue()

    ocr_72 = TesseractOCR(dpi=72, lang="por", timeout_seconds=30.0)
    ocr_300 = TesseractOCR(dpi=300, lang="por", timeout_seconds=30.0)

    png_text_72 = ocr_72(fixed_png, "image/png")
    pdf_text_72 = ocr_72(fixed_pdf, "application/pdf")
    png_text_300 = ocr_300(fixed_png, "image/png")
    pdf_text_300 = ocr_300(fixed_pdf, "application/pdf")
    jpeg_text_300 = ocr_300(fixed_jpeg, "image/jpeg")

    # A 72 DPI (scale=1.0), o PDF de render.py preserva exatamente a matriz raster 1:1 do PNG
    assert pdf_text_72.strip() == png_text_72.strip()
    assert "CURSO SINTETICO TESTE" in png_text_300
    assert "INSTITUTO FICTICIO TESTE" in png_text_300
    assert "CURSO SINTETICO TESTE" in pdf_text_300
    assert "CURSO SINTETICO TESTE" in jpeg_text_300

    # Verifica extração via OCRRegex.from_tesseract sem acessar gabarito
    extracted_fixed = OCRRegex.from_tesseract(dpi=150).extract(
        "smoke-fixed", fixed_pdf, "application/pdf"
    )
    assert extracted_fixed.extraction_status == "OK"
    assert extracted_fixed.activity_title == "CURSO SINTETICO TESTE"
    assert extracted_fixed.issuer_institution == "INSTITUTO FICTICIO TESTE"
    assert extracted_fixed.workload_hours == Decimal(40)
    assert extracted_fixed.start_year == 2020
    assert extracted_fixed.end_year == 2024
    assert extracted_fixed.activity_year == 2024

    # Amostra estritamente da partição pilot (1 família piloto)
    pilot_cases = [
        c
        for c in generate(seed=42, pilot_families=1, final_families=1).select("pilot")
        if c.document is not None
    ]
    assert all(c.partition == "pilot" for c in pilot_cases)
    pilot_png_case = next(c for c in pilot_cases if c.mime_type == "image/png")
    pilot_pdf_case = next(c for c in pilot_cases if c.mime_type == "application/pdf")

    baseline = OCRRegex(ocr_300)
    rec_pilot_png = baseline.extract(
        pilot_png_case.case_id, pilot_png_case.document, pilot_png_case.mime_type
    )
    rec_pilot_pdf = baseline.extract(
        pilot_pdf_case.case_id, pilot_pdf_case.document, pilot_pdf_case.mime_type
    )
    assert rec_pilot_png.document_id == pilot_png_case.case_id
    assert rec_pilot_png.extraction_status in ("OK", "INVALID_JSON", "UNREADABLE")
    assert rec_pilot_pdf.document_id == pilot_pdf_case.case_id
    assert rec_pilot_pdf.extraction_status in ("OK", "INVALID_JSON", "UNREADABLE")

    # Smoke do comando operacional via módulo ocr (--check e --file)
    sample_png_path = tmp_path / "smoke.png"
    sample_png_path.write_bytes(fixed_png)
    assert ocr_cli_main(["--check"]) == 0
    assert ocr_cli_main(["--file", str(sample_png_path), "--dpi", "150"]) == 0
    cli_out = capsys.readouterr().out
    assert "CURSO SINTETICO TESTE" in cli_out


def test_tesseract_ocr_baseline_defaults_and_optional_quality_params(tmp_path):
    baseline = TesseractOCR()
    assert baseline.dpi == 300
    assert baseline.pdf_resampling == "pdfium"
    assert baseline.upscale_small_images is False
    assert baseline.psm is None

    with pytest.raises(ValueError, match="pdf_resampling"):
        TesseractOCR(pdf_resampling="bilinear")
    with pytest.raises(ValueError, match=r"(?i)psm"):
        TesseractOCR(psm=14)
    with pytest.raises(ValueError, match=r"(?i)psm"):
        TesseractOCR(psm=True)
    with pytest.raises(ValueError, match="upscale_small_images"):
        TesseractOCR(upscale_small_images="yes")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="small_image_upscale_max_dim"):
        TesseractOCR(small_image_upscale_max_dim=0)

    captured_cmds: list[list[str]] = []
    captured_sizes: list[tuple[int, int]] = []

    def fake_runner(cmd, **kwargs):
        if "--list-langs" in cmd:
            return subprocess.CompletedProcess(
                cmd, 0, stdout="List of available languages in \"C:\\tessdata\":\npor\n", stderr=""
            )
        if "--version" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="tesseract 5.4.0.20240606\n", stderr="")
        captured_cmds.append(list(cmd))
        with Image.open(cmd[1]) as sent_img:
            captured_sizes.append(sent_img.size)
        return subprocess.CompletedProcess(cmd, 0, stdout="Texto ok", stderr="")

    fixed_record = ExtractedDocumentRecord(
        document_id="unit-pdf",
        holder_name="Ana Teste",
        activity_title="Curso Teste",
        issuer_institution="Instituto Teste",
        start_year=2024,
        end_year=2024,
        activity_year=2024,
        workload_hours=Decimal(10),
    )
    w, h, px = raster(document_text(fixed_record, layout=0), seed=1, degradation=0, layout=0)
    sample_pdf = pdf(w, h, px)
    small_png = png(w, h, px)

    # Baseline does not emit --psm and keeps original PNG dimensions
    ocr_base = TesseractOCR(executable="tesseract", runner=fake_runner)
    assert ocr_base(small_png, "image/png") == "Texto ok"
    assert "--psm" not in captured_cmds[-1]
    assert captured_sizes[-1] == (w, h)
    meta_base = ocr_base.metadata()
    assert meta_base["pdf_resampling"] == "pdfium"
    assert meta_base["upscale_small_images"] is False
    assert meta_base["psm"] is None

    # Opt-in pillow_lanczos PDF resampling + small image upscale + psm
    ocr_opt = TesseractOCR(
        executable="tesseract",
        dpi=288,
        pdf_resampling="pillow_lanczos",
        upscale_small_images=True,
        small_image_upscale_max_dim=1400,
        psm=3,
        runner=fake_runner,
    )
    assert ocr_opt(sample_pdf, "application/pdf") == "Texto ok"
    assert "--psm" in captured_cmds[-1]
    psm_idx = captured_cmds[-1].index("--psm")
    assert captured_cmds[-1][psm_idx + 1] == "3"
    assert captured_sizes[-1] == (w * 4, h * 4)

    assert ocr_opt(small_png, "image/png") == "Texto ok"
    assert captured_sizes[-1] == (w * 4, h * 4)

    ocr_no_upscale_above_threshold = TesseractOCR(
        executable="tesseract",
        dpi=288,
        upscale_small_images=True,
        small_image_upscale_max_dim=max(w, h),
        runner=fake_runner,
    )
    assert ocr_no_upscale_above_threshold(small_png, "image/png") == "Texto ok"
    assert captured_sizes[-1] == (w, h)
    meta_opt = ocr_opt.metadata()
    assert meta_opt["pdf_resampling"] == "pillow_lanczos"
    assert meta_opt["upscale_small_images"] is True
    assert meta_opt["psm"] == 3

    # max_image_pixels guardrail still enforced after pillow_lanczos rescale
    ocr_tiny_limit = TesseractOCR(
        executable="tesseract",
        dpi=288,
        pdf_resampling="pillow_lanczos",
        max_image_pixels=w * h * 2,
        runner=fake_runner,
    )
    with pytest.raises(OCRRenderError, match="excede o limite"):
        ocr_tiny_limit(sample_pdf, "application/pdf")
