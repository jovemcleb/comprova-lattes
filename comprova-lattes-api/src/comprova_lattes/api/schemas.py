"""Entradas JSON; configuração científica sempre explícita."""

import base64
import binascii

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from comprova_lattes.extractor.gemini import SUPPORTED_MIME_TYPES
from comprova_lattes.matcher.models import MatcherConfig, MatchStatus
from comprova_lattes.schemas.lattes import NonEmptyStr


def decode_content(value: str) -> bytes:
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Base64 inválido") from exc
    if not data:
        raise ValueError("Conteúdo vazio")
    return data


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentUploadInput(InputModel):
    document_id: NonEmptyStr
    filename: NonEmptyStr
    mime_type: str
    content_base64: str = Field(max_length=28_000_000)

    @field_validator("mime_type")
    @classmethod
    def supported_mime(cls, value: str) -> str:
        if value not in SUPPORTED_MIME_TYPES:
            raise ValueError("Formato não suportado")
        return value

    @field_validator("content_base64")
    @classmethod
    def valid_content(cls, value: str) -> str:
        decode_content(value)
        return value


class ValidationCreateRequest(InputModel):
    xml_content: str | None = Field(default=None, max_length=10_485_760)
    xml_base64: str | None = Field(default=None, max_length=14_000_000)
    documents: list[DocumentUploadInput] = Field(default_factory=list, max_length=100)
    matcher_config: MatcherConfig

    @model_validator(mode="after")
    def validate_payload(self) -> "ValidationCreateRequest":
        if (self.xml_content is None) == (self.xml_base64 is None):
            raise ValueError("Informe exatamente um de xml_content ou xml_base64")
        self.xml_bytes()
        ids = [doc.document_id for doc in self.documents]
        if len(ids) != len(set(ids)):
            raise ValueError("document_id duplicado")
        return self

    def xml_bytes(self) -> bytes:
        if self.xml_base64 is not None:
            return decode_content(self.xml_base64)
        return self.xml_content.encode("utf-8")


class HumanReviewRequest(InputModel):
    reviewer: NonEmptyStr
    status: MatchStatus
    justification: NonEmptyStr
    matched_document_id: NonEmptyStr | None = None
    rejected_document_ids: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent_decision(self) -> "HumanReviewRequest":
        if len(set(self.rejected_document_ids)) != len(self.rejected_document_ids):
            raise ValueError("Candidatos rejeitados duplicados")
        if self.matched_document_id in self.rejected_document_ids:
            raise ValueError("Documento associado também rejeitado")
        return self
