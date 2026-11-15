"""Adaptador OCR real via Tesseract (por) para PNG, JPEG e PDF rasterizado."""

import argparse
import io
import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

SUPPORTED_OCR_MIME_TYPES: frozenset[str] = frozenset(
    {"image/png", "image/jpeg", "application/pdf"}
)
DEFAULT_OCR_LANG = "por"
DEFAULT_OCR_DPI = 300
DEFAULT_OCR_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_PDF_PAGES = 10
DEFAULT_MAX_IMAGE_PIXELS = 25_000_000
DEFAULT_PDF_RESAMPLING = "pdfium"
SUPPORTED_PDF_RESAMPLING_MODES: frozenset[str] = frozenset({"pdfium", "pillow_lanczos"})
DEFAULT_SMALL_IMAGE_UPSCALE_MAX_DIM = 1200
MIN_OCR_DPI = 72
MAX_OCR_DPI = 600
MIN_OCR_PSM = 0
MAX_OCR_PSM = 13
MIN_OCR_TIMEOUT_SECONDS = 0.1
MAX_OCR_TIMEOUT_SECONDS = 300.0
TESSERACT_CMD_ENV = "TESSERACT_CMD"
TESSDATA_PREFIX_ENV = "TESSDATA_PREFIX"


class OCRError(OSError):
    """Erro operacional de OCR ou de preparação de imagem/PDF raster."""


class TesseractNotFoundError(OCRError):
    """Executável do Tesseract não encontrado no caminho configurado ou no sistema."""


class TesseractLanguageError(OCRError):
    """Idioma solicitado (ex.: 'por' / por.traineddata) ausente no Tesseract."""


class TesseractTimeoutError(OCRError):
    """Tempo limite excedido na execução do subprocesso Tesseract."""


class TesseractExecutionError(OCRError):
    """Subprocesso do Tesseract encerrou com código de saída diferente de zero."""


class OCRRenderError(OCRError):
    """Falha ao decodificar PNG/JPEG ou ao rasterizar páginas PDF via pypdfium2/Pillow."""


SubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


def _candidate_windows_paths() -> list[Path]:
    candidates: list[Path] = [
        Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe",
    ]
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Programs" / "Tesseract-OCR" / "tesseract.exe")
    candidates.extend(
        [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        ]
    )
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        norm = os.path.normcase(str(path))
        if norm not in seen:
            seen.add(norm)
            unique.append(path)
    return unique


def resolve_tesseract_executable(executable: str | Path | None = None) -> Path:
    """Localiza o binário do Tesseract por caminho explícito, TESSERACT_CMD, PATH ou local."""
    if executable is not None:
        raw = str(executable).strip()
        if not raw:
            raise ValueError("Caminho do executável Tesseract não pode ser vazio.")
        direct = Path(raw)
        if direct.is_file():
            return direct.resolve()
        found = shutil.which(raw)
        if found and Path(found).is_file():
            return Path(found).resolve()
        raise TesseractNotFoundError(
            f"Executável Tesseract configurado não encontrado: {raw!r}."
        )

    env_cmd = os.environ.get(TESSERACT_CMD_ENV, "").strip()
    if env_cmd:
        env_path = Path(env_cmd)
        if env_path.is_file():
            return env_path.resolve()
        found_env = shutil.which(env_cmd)
        if found_env and Path(found_env).is_file():
            return Path(found_env).resolve()
        raise TesseractNotFoundError(
            f"Executável definido em {TESSERACT_CMD_ENV}={env_cmd!r} não encontrado."
        )

    which_path = shutil.which("tesseract")
    if which_path and Path(which_path).is_file():
        return Path(which_path).resolve()

    for candidate in _candidate_windows_paths():
        if candidate.is_file():
            return candidate.resolve()

    raise TesseractNotFoundError(
        "Executável 'tesseract' não encontrado no PATH nem nos diretórios locais padrão "
        "(%LOCALAPPDATA%\\Programs\\Tesseract-OCR\\tesseract.exe ou C:\\Program Files\\Tesseract-OCR)."
    )


def _load_pillow():
    try:
        import PIL
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        raise OCRRenderError(
            "Pillow é obrigatório para preparar imagens de OCR (instale .[ocr])."
        ) from exc
    return PIL, Image, UnidentifiedImageError


def _load_pdfium():
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise OCRRenderError(
            "pypdfium2 é obrigatório para rasterizar PDFs no OCR (instale .[ocr])."
        ) from exc
    return pdfium


def _parse_languages_output(output: str) -> tuple[str, ...]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    langs: list[str] = []
    header_seen = False
    for line in lines:
        lower = line.lower()
        if lower.startswith("list of available languages"):
            header_seen = True
            continue
        if not header_seen and (":" in line or " " in line):
            continue
        langs.append(line)
    return tuple(sorted(set(langs)))


def _is_language_failure_stderr(stderr: str, lang: str) -> bool:
    lower = stderr.lower()
    markers = (
        "failed loading language",
        "error opening data file",
        f"{lang.lower()}.traineddata",
        "tessdata",
        "could not initialize tesseract",
    )
    return any(marker in lower for marker in markers)


class TesseractOCR:
    """Callable `(data: bytes, mime_type: str) -> str` via subprocesso Tesseract sem shell.

    Converte PDFs exclusivamente por rasterização de página (`pypdfium2` -> `Pillow` PNG),
    sem extrair texto embutido do PDF, e nunca acessa gabarito, corpus ou manifesto.
    """

    def __init__(
        self,
        *,
        executable: str | Path | None = None,
        lang: str = DEFAULT_OCR_LANG,
        dpi: int = DEFAULT_OCR_DPI,
        timeout_seconds: float = DEFAULT_OCR_TIMEOUT_SECONDS,
        max_pdf_pages: int = DEFAULT_MAX_PDF_PAGES,
        max_image_pixels: int = DEFAULT_MAX_IMAGE_PIXELS,
        tessdata_dir: str | Path | None = None,
        psm: int | None = None,
        pdf_resampling: str = DEFAULT_PDF_RESAMPLING,
        upscale_small_images: bool = False,
        small_image_upscale_max_dim: int = DEFAULT_SMALL_IMAGE_UPSCALE_MAX_DIM,
        runner: SubprocessRunner = subprocess.run,
    ) -> None:
        if not isinstance(lang, str) or not lang.strip():
            raise ValueError("Idioma OCR deve ser string não vazia (ex.: 'por').")
        if type(dpi) is not int or not (MIN_OCR_DPI <= dpi <= MAX_OCR_DPI):
            raise ValueError(f"DPI deve ser inteiro entre {MIN_OCR_DPI} e {MAX_OCR_DPI}.")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not (MIN_OCR_TIMEOUT_SECONDS <= float(timeout_seconds) <= MAX_OCR_TIMEOUT_SECONDS)
        ):
            raise ValueError(
                f"Timeout deve estar entre {MIN_OCR_TIMEOUT_SECONDS} e {MAX_OCR_TIMEOUT_SECONDS} s."
            )
        if type(max_pdf_pages) is not int or max_pdf_pages < 1:
            raise ValueError("max_pdf_pages deve ser inteiro positivo.")
        if type(max_image_pixels) is not int or max_image_pixels < 1024:
            raise ValueError("max_image_pixels deve ser inteiro >= 1024.")
        if psm is not None and (type(psm) is not int or not (MIN_OCR_PSM <= psm <= MAX_OCR_PSM)):
            raise ValueError(f"PSM deve ser inteiro entre {MIN_OCR_PSM} e {MAX_OCR_PSM}.")
        if pdf_resampling not in SUPPORTED_PDF_RESAMPLING_MODES:
            raise ValueError(
                f"pdf_resampling inválido: {pdf_resampling!r}. "
                f"Permitidos: {sorted(SUPPORTED_PDF_RESAMPLING_MODES)}."
            )
        if type(upscale_small_images) is not bool:
            raise ValueError("upscale_small_images deve ser booleano.")
        if type(small_image_upscale_max_dim) is not int or small_image_upscale_max_dim < 64:
            raise ValueError("small_image_upscale_max_dim deve ser inteiro >= 64.")

        self.executable = executable
        self.lang = lang.strip()
        self.dpi = dpi
        self.timeout_seconds = float(timeout_seconds)
        self.max_pdf_pages = max_pdf_pages
        self.max_image_pixels = max_image_pixels
        env_tessdata = os.environ.get(TESSDATA_PREFIX_ENV, "").strip()
        self.tessdata_dir = (
            Path(tessdata_dir)
            if tessdata_dir is not None
            else (Path(env_tessdata) if env_tessdata else None)
        )
        self.psm = psm
        self.pdf_resampling = pdf_resampling
        self.upscale_small_images = upscale_small_images
        self.small_image_upscale_max_dim = small_image_upscale_max_dim
        self.runner = runner
        self._verified_languages: tuple[str, ...] | None = None

    def _resolve_executable(self) -> Path:
        if self.executable is not None and self.runner is not subprocess.run:
            raw = str(self.executable).strip()
            if not raw:
                raise ValueError("Caminho do executável Tesseract não pode ser vazio.")
            return Path(raw)
        return resolve_tesseract_executable(self.executable)

    def _tessdata_args(self) -> list[str]:
        if self.tessdata_dir is None:
            return []
        return ["--tessdata-dir", str(self.tessdata_dir)]

    def _run_command(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return self.runner(
                args,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TesseractTimeoutError(
                f"Timeout de {self.timeout_seconds}s excedido na execução do Tesseract."
            ) from exc
        except FileNotFoundError as exc:
            raise TesseractNotFoundError(
                f"Executável Tesseract não encontrado ao iniciar subprocesso: {args[0]!r}."
            ) from exc
        except (OSError, subprocess.SubprocessError) as exc:
            raise TesseractExecutionError(
                f"Falha operacional ao invocar subprocesso do Tesseract: {exc}"
            ) from exc

    def version(self) -> str:
        """Retorna a saída completa de `tesseract --version`."""
        exe = self._resolve_executable()
        completed = self._run_command([str(exe), "--version"])
        output = (completed.stdout or completed.stderr or "").strip()
        if completed.returncode != 0 or not output:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise TesseractExecutionError(
                f"Falha ao consultar versão do Tesseract (código {completed.returncode}): {detail}"
            )
        return output

    def list_languages(self) -> tuple[str, ...]:
        """Lista os idiomas instalados reportados por `tesseract --list-langs`."""
        exe = self._resolve_executable()
        completed = self._run_command([str(exe), *self._tessdata_args(), "--list-langs"])
        combined = "\n".join(
            part for part in (completed.stdout, completed.stderr) if part
        ).strip()
        if completed.returncode != 0:
            raise TesseractExecutionError(
                f"Falha ao listar idiomas do Tesseract (código {completed.returncode}): {combined}"
            )
        langs = _parse_languages_output(combined)
        if not langs:
            raise TesseractExecutionError(
                f"Saída de --list-langs sem idiomas reconhecidos: {combined!r}"
            )
        return langs

    def ensure_language_available(self) -> tuple[str, ...]:
        """Verifica se o idioma configurado (ex.: 'por') está instalado no Tesseract."""
        if self._verified_languages is not None:
            return self._verified_languages
        langs = self.list_languages()
        required = [part.strip() for part in self.lang.split("+") if part.strip()]
        missing = [part for part in required if part not in langs]
        if missing:
            missing_str = ", ".join(f"'{m}' ({m}.traineddata)" for m in missing)
            raise TesseractLanguageError(
                f"Idioma OCR obrigatório ausente no Tesseract: {missing_str}. "
                f"Idiomas instalados: {list(langs)}. "
                "Instale o arquivo oficial por.traineddata (tesseract-ocr/tessdata, Apache-2.0) "
                "no diretório tessdata."
            )
        self._verified_languages = langs
        return langs

    def _prepare_image_page(self, data: bytes, mime_type: str, target_path: Path) -> None:
        _, image_cls, unidentified_cls = _load_pillow()
        expected_formats = {"image/png": ("PNG",), "image/jpeg": ("JPEG", "MPO")}[mime_type]
        try:
            with image_cls.open(io.BytesIO(data)) as img:
                actual_format = (img.format or "").upper()
                if actual_format not in expected_formats:
                    raise OCRRenderError(
                        f"Formato de imagem {actual_format!r} incompatível com MIME {mime_type!r}."
                    )
                width, height = img.size
                if width <= 0 or height <= 0 or width * height > self.max_image_pixels:
                    raise OCRRenderError(
                        f"Dimensões da imagem ({width}x{height}) inválidas ou acima do limite "
                        f"de {self.max_image_pixels} pixels."
                    )
                img.load()
                converted = img if img.mode in ("L", "RGB", "1") else img.convert("RGB")
                if (
                    self.upscale_small_images
                    and max(width, height) < self.small_image_upscale_max_dim
                    and self.dpi > MIN_OCR_DPI
                ):
                    scale = self.dpi / 72.0
                    target_w = max(1, round(width * scale))
                    target_h = max(1, round(height * scale))
                    if target_w * target_h > self.max_image_pixels:
                        raise OCRRenderError(
                            f"Imagem reamostrada ({target_w}x{target_h}) excede o limite de "
                            f"{self.max_image_pixels} pixels."
                        )
                    if converted.mode == "1":
                        converted = converted.convert("L")
                    converted = converted.resize(
                        (target_w, target_h), image_cls.Resampling.LANCZOS
                    )
                converted.save(target_path, format="PNG", dpi=(self.dpi, self.dpi))
        except OCRRenderError:
            raise
        except (unidentified_cls, OSError, ValueError, SyntaxError) as exc:
            raise OCRRenderError(
                f"Imagem ({mime_type}) inválida ou corrompida para OCR: {exc}"
            ) from exc

    def _prepare_pdf_pages(self, data: bytes, tmp_dir: Path) -> list[Path]:
        """Rasteriza páginas do PDF via pypdfium2 -> Pillow sem extrair texto embutido."""
        _, image_cls, _ = _load_pillow()
        pdfium = _load_pdfium()
        scale = self.dpi / 72.0
        render_scale = 1.0 if self.pdf_resampling == "pillow_lanczos" else scale
        pdf_doc = None
        try:
            pdf_doc = pdfium.PdfDocument(data)
            page_count = len(pdf_doc)
            if page_count < 1:
                raise OCRRenderError("PDF não contém páginas para rasterização OCR.")
            if page_count > self.max_pdf_pages:
                raise OCRRenderError(
                    f"PDF contém {page_count} páginas, excedendo o limite configurado "
                    f"de {self.max_pdf_pages} páginas."
                )
            paths: list[Path] = []
            for idx in range(page_count):
                page = pdf_doc[idx]
                bitmap = None
                try:
                    bitmap = page.render(scale=render_scale)
                    pil_image = bitmap.to_pil()
                    width, height = pil_image.size
                    if width <= 0 or height <= 0 or width * height > self.max_image_pixels:
                        raise OCRRenderError(
                            f"Página PDF {idx + 1} rasterizada ({width}x{height}) excede o limite "
                            f"de {self.max_image_pixels} pixels."
                        )
                    if self.pdf_resampling == "pillow_lanczos" and abs(scale - 1.0) > 1e-6:
                        target_w = max(1, round(width * scale))
                        target_h = max(1, round(height * scale))
                        if target_w * target_h > self.max_image_pixels:
                            raise OCRRenderError(
                                f"Página PDF {idx + 1} reamostrada ({target_w}x{target_h}) excede "
                                f"o limite de {self.max_image_pixels} pixels."
                            )
                        pil_image = pil_image.resize(
                            (target_w, target_h), image_cls.Resampling.LANCZOS
                        )
                    out_path = tmp_dir / f"page_{idx + 1:04d}.png"
                    pil_image.save(out_path, format="PNG", dpi=(self.dpi, self.dpi))
                    paths.append(out_path)
                finally:
                    if bitmap is not None and hasattr(bitmap, "close"):
                        bitmap.close()
                    if hasattr(page, "close"):
                        page.close()
            return paths
        except OCRRenderError:
            raise
        except Exception as exc:
            raise OCRRenderError(
                f"Falha ao rasterizar PDF via pypdfium2 (sem extração de texto): {exc}"
            ) from exc
        finally:
            if pdf_doc is not None and hasattr(pdf_doc, "close"):
                pdf_doc.close()

    def _prepare_pages(self, data: bytes, mime_type: str, tmp_dir: Path) -> list[Path]:
        if mime_type == "application/pdf":
            return self._prepare_pdf_pages(data, tmp_dir)
        out_path = tmp_dir / "page_0001.png"
        self._prepare_image_page(data, mime_type, out_path)
        return [out_path]

    def __call__(self, data: bytes, mime_type: str) -> str:
        if mime_type not in SUPPORTED_OCR_MIME_TYPES:
            raise ValueError(
                f"MIME type não suportado para OCR: {mime_type!r}. "
                f"Use um de: {sorted(SUPPORTED_OCR_MIME_TYPES)}."
            )
        if not isinstance(data, (bytes, bytearray)) or not data:
            raise ValueError("Documento para OCR deve conter bytes não vazios.")

        exe = self._resolve_executable()
        self.ensure_language_available()

        raw_bytes = bytes(data)
        with tempfile.TemporaryDirectory(prefix="comprova_lattes_ocr_") as tmp_name:
            tmp_dir = Path(tmp_name)
            page_paths = self._prepare_pages(raw_bytes, mime_type, tmp_dir)
            texts: list[str] = []
            for page_path in page_paths:
                cmd = [
                    str(exe),
                    *self._tessdata_args(),
                    str(page_path),
                    "stdout",
                    "-l",
                    self.lang,
                    "--dpi",
                    str(self.dpi),
                ]
                if self.psm is not None:
                    cmd.extend(["--psm", str(self.psm)])
                completed = self._run_command(cmd)
                if completed.returncode != 0:
                    stderr = (completed.stderr or "").strip()
                    if _is_language_failure_stderr(stderr, self.lang):
                        raise TesseractLanguageError(
                            f"Tesseract falhou ao carregar o idioma {self.lang!r}: {stderr}"
                        )
                    raise TesseractExecutionError(
                        f"Tesseract encerrou com erro (código {completed.returncode}): "
                        f"{stderr or 'sem mensagem em stderr'}"
                    )
                texts.append(completed.stdout or "")
        return "\n".join(texts)

    def metadata(self) -> dict[str, Any]:
        """Retorna metadados auditáveis de versão, DPI, idioma, timeout e limites do OCR."""
        pil_version: str | None = None
        pdfium_py_version: str | None = None
        pdfium_native_version: str | None = None
        try:
            pil_mod, _, _ = _load_pillow()
            pil_version = getattr(pil_mod, "__version__", None)
        except OCRRenderError:
            pass
        try:
            pdfium_mod = _load_pdfium()
            ver = getattr(pdfium_mod, "version", None)
            pdfium_py_version = getattr(ver, "PYPDFIUM_INFO", None) or getattr(
                pdfium_mod, "__version__", None
            )
            pdfium_native_version = getattr(ver, "PDFIUM_INFO", None)
        except OCRRenderError:
            pass

        exe_str: str | None = None
        version_first_line: str | None = None
        version_raw: str | None = None
        languages: list[str] = []
        lang_available = False
        error_msg: str | None = None
        try:
            exe = self._resolve_executable()
            exe_str = str(exe)
            version_raw = self.version()
            version_first_line = version_raw.splitlines()[0].strip() if version_raw else None
            languages = list(self.list_languages())
            required = [part.strip() for part in self.lang.split("+") if part.strip()]
            lang_available = bool(required) and all(part in languages for part in required)
        except OCRError as exc:
            error_msg = str(exc)

        return {
            "engine": "tesseract",
            "available": bool(
                exe_str
                and version_first_line
                and lang_available
                and pil_version
                and pdfium_py_version
            ),
            "executable": exe_str,
            "tesseract_version": version_first_line,
            "tesseract_version_raw": version_raw,
            "language": self.lang,
            "language_available": lang_available,
            "available_languages": languages,
            "tessdata_dir": str(self.tessdata_dir) if self.tessdata_dir else None,
            "dpi": self.dpi,
            "pdf_render_scale": self.dpi / 72.0,
            "pdf_resampling": self.pdf_resampling,
            "upscale_small_images": self.upscale_small_images,
            "psm": self.psm,
            "timeout_seconds": self.timeout_seconds,
            "max_pdf_pages": self.max_pdf_pages,
            "max_image_pixels": self.max_image_pixels,
            "supported_mime_types": sorted(SUPPORTED_OCR_MIME_TYPES),
            "pdf_conversion_library": "pypdfium2",
            "pypdfium2_version": str(pdfium_py_version) if pdfium_py_version else None,
            "pdfium_version": str(pdfium_native_version) if pdfium_native_version else None,
            "pillow_version": pil_version,
            "pdf_text_extraction": "disabled_raster_only",
            "error": error_msg,
            "limitations": [
                (
                    "PDF é convertido exclusivamente em imagem raster via pypdfium2 "
                    "(scale = dpi / 72.0), sem extrair camadas de texto embutido."
                ),
                (
                    "Em PDFs gerados por render.py (/MediaBox em dimensões de pixel), "
                    "dpi=72 (scale=1.0) preserva a matriz 1:1 do PNG, enquanto dpi=300 "
                    "(scale=300/72) reamostra a imagem."
                ),
                (
                    "Erros de reconhecimento de caracteres pelo Tesseract ou nas marcações "
                    "de rótulo propagam-se sem ajuste ad-hoc de RegEx ao conjunto de avaliação."
                ),
            ],
        }


def ocr_environment_metadata(**kwargs: Any) -> dict[str, Any]:
    """Atalho funcional para inspecionar o ambiente OCR sem executar estudo."""
    return TesseractOCR(**kwargs).metadata()


def _detect_mime_from_suffix(path: Path) -> str:
    suffix = path.suffix.lower()
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".pdf": "application/pdf",
    }
    if suffix not in mapping:
        raise ValueError(
            f"Não foi possível inferir MIME de {path.name!r}; informe --mime explicitamente."
        )
    return mapping[suffix]


def main(argv: list[str] | None = None) -> int:
    """CLI utilitária de verificação do ambiente OCR e extração avulsa/lote."""
    parser = argparse.ArgumentParser(
        description="Inspeção e execução operacional do baseline OCR (Tesseract + pypdfium2)."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifica instalação do Tesseract, idioma 'por', Pillow e pypdfium2.",
    )
    parser.add_argument("--file", type=Path, help="Arquivo PNG, JPEG ou PDF para OCR avulso.")
    parser.add_argument(
        "--mime",
        choices=sorted(SUPPORTED_OCR_MIME_TYPES),
        help="MIME type do arquivo (inferido pela extensão quando omitido).",
    )
    parser.add_argument("--executable", type=Path, help="Caminho explícito do binário tesseract.")
    parser.add_argument("--lang", default=DEFAULT_OCR_LANG, help="Idioma do Tesseract (padrão: por).")
    parser.add_argument(
        "--dpi", type=int, default=DEFAULT_OCR_DPI, help="DPI de rasterização e OCR (padrão: 300)."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_OCR_TIMEOUT_SECONDS,
        help="Timeout por execução do subprocesso em segundos (padrão: 30).",
    )
    args = parser.parse_args(argv)

    ocr = TesseractOCR(
        executable=args.executable,
        lang=args.lang,
        dpi=args.dpi,
        timeout_seconds=args.timeout,
    )

    if args.check or args.file is None:
        meta = ocr.metadata()
        print(json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if meta["available"] else 1

    mime = args.mime or _detect_mime_from_suffix(args.file)
    data = args.file.read_bytes()
    from .baseline import OCRRegex

    text = ocr(data, mime)
    record = OCRRegex(lambda *_: text).extract(args.file.name, data, mime)
    payload = {
        "file": str(args.file),
        "mime_type": mime,
        "dpi": ocr.dpi,
        "lang": ocr.lang,
        "ocr_text": text,
        "record": record.model_dump(mode="json"),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
