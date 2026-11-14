"""OCR injetável: recebe exclusivamente bytes/MIME, nunca gabarito ou manifesto."""

import re
from collections.abc import Callable

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
PATTERNS = {k: rf"^\s*{k}\s*:\s*(.+?)\s*$" for k in FIELDS}


class OCRRegex:
    def __init__(self, ocr: Callable[[bytes, str], str], patterns: dict[str, str] | None = None):
        self.ocr = ocr
        self.patterns = PATTERNS if patterns is None else patterns
        if set(self.patterns) - set(FIELDS):
            raise ValueError("Regex de campo desconhecido")

    def extract(self, document_id: str, data: bytes, mime_type: str) -> ExtractedDocumentRecord:
        try:
            text = self.ocr(data, mime_type)
        except OSError:
            return ExtractedDocumentRecord(document_id=document_id, extraction_status="API_ERROR")
        if not text.strip():
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
