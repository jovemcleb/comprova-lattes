"""OCR injetável: recebe exclusivamente bytes/MIME, nunca gabarito ou manifesto."""

import re
import subprocess
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from comprova_lattes.matcher.models import ExtractedDocumentRecord

FIELDS = tuple(
    k
    for k in ExtractedDocumentRecord.model_fields
    if k
    not in {
        "document_id",
        "raw_metadata",
        "extraction_status",
        "confianca_extracao",
        "categoria_sugerida",
    }
)

FIELD_LABELS_PT: dict[str, str] = {
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

_LABEL_REGEX: dict[str, str] = {
    "holder_name": r"(?:holder_name|Titular)",
    "activity_title": r"(?:activity_title|Atividade)",
    "event_name": r"(?:event_name|Evento)",
    "participation_role_raw": r"(?:participation_role_raw|Papel)",
    "issuer_institution": r"(?:issuer_institution|Institui[çc][ãa]o[ \t]+emissora)",
    "issuer_acronym": r"(?:issuer_acronym|Sigla[ \t]+da[ \t]+institui[çc][ãa]o)",
    "issuer_name_acronym_evidence": (
        r"(?:issuer_name_acronym_evidence|Identifica[çc][ãa]o[ \t]+da[ \t]+institui[çc][ãa]o)"
    ),
    "start_year": r"(?:start_year|Ano[ \t]+de[ \t]+in[íi]cio)",
    "end_year": r"(?:end_year|Ano[ \t]+de[ \t]+conclus[ãa]o)",
    "activity_year": r"(?:activity_year|Ano[ \t]+da[ \t]+atividade)",
    "workload_hours": r"(?:workload_hours|Carga[ \t]+hor[áa]ria)",
}

PATTERNS: dict[str, str] = {
    k: rf"^[ \t]*{_LABEL_REGEX[k]}[ \t]*:[ \t]*([^\r\n]+?)[ \t\r]*$" for k in FIELDS
}


class OCRRegex:
    def __init__(
        self,
        ocr: Callable[[bytes, str], str] | None = None,
        patterns: dict[str, str] | None = None,
    ):
        if ocr is None:
            from .ocr import TesseractOCR

            ocr = TesseractOCR()
        self.ocr = ocr
        self.patterns = PATTERNS if patterns is None else patterns
        if set(self.patterns) - set(FIELDS):
            raise ValueError("Regex de campo desconhecido")

    @classmethod
    def from_tesseract(
        cls,
        *,
        patterns: dict[str, str] | None = None,
        **ocr_kwargs: Any,
    ) -> "OCRRegex":
        from .ocr import TesseractOCR

        return cls(ocr=TesseractOCR(**ocr_kwargs), patterns=patterns)

    def extract(self, document_id: str, data: bytes, mime_type: str) -> ExtractedDocumentRecord:
        try:
            text = self.ocr(data, mime_type)
        except (OSError, subprocess.SubprocessError):
            return ExtractedDocumentRecord(document_id=document_id, extraction_status="API_ERROR")
        if not text or not text.strip():
            return ExtractedDocumentRecord(document_id=document_id, extraction_status="UNREADABLE")
        values = {}
        for field, pattern in self.patterns.items():
            found = re.search(pattern, text, flags=re.MULTILINE | re.IGNORECASE)
            if found:
                values[field] = found.group(1).strip()
        try:
            return ExtractedDocumentRecord(document_id=document_id, **values)
        except ValidationError:
            return ExtractedDocumentRecord(
                document_id=document_id, extraction_status="INVALID_JSON"
            )
