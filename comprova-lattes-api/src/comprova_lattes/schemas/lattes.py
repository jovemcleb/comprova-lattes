"""Schemas Pydantic v2 canônicos para representação do XML do Currículo Lattes."""

from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints
from pydantic_core import PydanticCustomError

_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")


def _normalize_optional_str(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _validate_strict_int(value: Any) -> Any:
    if isinstance(value, bool):
        raise PydanticCustomError("int_type", "Boolean is not a valid integer.")
    if isinstance(value, float):
        raise PydanticCustomError(
            "int_from_float",
            "Float is not accepted for integer fields; avoid silent truncation.",
        )
    if isinstance(value, Decimal) and (not value.is_finite() or value != value.to_integral_value()):
        raise PydanticCustomError(
            "int_from_decimal",
            "Non-integral Decimal cannot be coerced to integer.",
        )
    if isinstance(value, str):
        stripped = value.strip()
        if not _INTEGER_PATTERN.fullmatch(stripped):
            raise PydanticCustomError("int_parsing", "Input should be a valid integer string.")
        return int(stripped)
    return value


def _validate_finite_decimal(value: Any) -> Any:
    if isinstance(value, bool):
        raise PydanticCustomError("decimal_type", "Boolean is not a valid decimal.")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PydanticCustomError("finite_number", "Non-finite float is not allowed.")
        return Decimal(str(value))
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise PydanticCustomError("finite_number", "Non-finite Decimal is not allowed.")
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise PydanticCustomError("decimal_parsing", "Empty string is not a valid decimal.")
        try:
            parsed = Decimal(stripped)
        except InvalidOperation as exc:
            raise PydanticCustomError("decimal_parsing", "Invalid decimal representation.") from exc
        if not parsed.is_finite():
            raise PydanticCustomError("finite_number", "Non-finite Decimal is not allowed.")
        return parsed
    return value


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
OptionalCleanStr = Annotated[str | None, BeforeValidator(_normalize_optional_str)]
StrictXmlInt = Annotated[int, BeforeValidator(_validate_strict_int)]
FiniteDecimal = Annotated[Decimal, BeforeValidator(_validate_finite_decimal)]


class LattesCategory(str, Enum):
    """Categorias-alvo do XML Lattes no escopo do sistema (3 seções iniciais + AD-012)."""

    FORMACAO_ACADEMICA = "FORMACAO_ACADEMICA"
    FORMACAO_COMPLEMENTAR = "FORMACAO_COMPLEMENTAR"
    PARTICIPACAO_EVENTO = "PARTICIPACAO_EVENTO"
    APRESENTACAO_TRABALHO = "APRESENTACAO_TRABALHO"
    ORGANIZACAO_EVENTO = "ORGANIZACAO_EVENTO"


class ActivityStatus(str, Enum):
    """Situação declarada para formação ou participação em evento no XML."""

    CONCLUIDO = "CONCLUIDO"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    INCOMPLETO = "INCOMPLETO"
    PARTICIPOU = "PARTICIPOU"
    INDEFINIDO = "INDEFINIDO"


class XmlProvenance(BaseModel):
    """Rastreabilidade de origem do registro dentro da árvore XML do Lattes."""

    model_config = ConfigDict(extra="forbid")

    parent_tag: OptionalCleanStr = None
    section_tag: NonEmptyStr
    record_tag: NonEmptyStr
    sequence_attribute: OptionalCleanStr = None
    raw_attributes: dict[str, str] = Field(default_factory=dict)


class LattesRecord(BaseModel):
    """Registro curricular auditável extraído das seções-alvo do XML Lattes."""

    model_config = ConfigDict(extra="forbid")

    record_id: OptionalCleanStr = None
    category: LattesCategory
    subtype: OptionalCleanStr = None
    sequence: OptionalCleanStr = None
    provenance: XmlProvenance
    holder_name: OptionalCleanStr = None
    institution: OptionalCleanStr = None
    institution_acronym: OptionalCleanStr = None
    title: OptionalCleanStr = None
    event_name: OptionalCleanStr = None
    city: OptionalCleanStr = None
    location: OptionalCleanStr = None
    start_year: StrictXmlInt | None = None
    end_year: StrictXmlInt | None = None
    workload_hours: FiniteDecimal | None = None
    status: ActivityStatus | None = None
    validation_code: OptionalCleanStr = None
    nature_raw: OptionalCleanStr = None
    participation_type_raw: OptionalCleanStr = None
    participation_form_raw: OptionalCleanStr = None
    participation_role: OptionalCleanStr = None


class LattesCurriculum(BaseModel):
    """Representação canônica mínima de um Currículo Lattes extraído do XML."""

    model_config = ConfigDict(extra="forbid")

    lattes_id: OptionalCleanStr = None
    updated_at: OptionalCleanStr = None
    full_name: OptionalCleanStr = None
    citation_names: list[NonEmptyStr] = Field(default_factory=list)
    summary: OptionalCleanStr = None
    records: list[LattesRecord] = Field(default_factory=list)
