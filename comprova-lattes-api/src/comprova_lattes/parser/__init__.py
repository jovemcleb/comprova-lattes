"""Módulo P0-A: Parsing determinístico e seguro do XML Lattes (defusedxml)."""

from comprova_lattes.parser.exceptions import (
    LattesEncodingError,
    LattesInvalidRootError,
    LattesMalformedXmlError,
    LattesNumericValueError,
    LattesParserError,
    LattesParserWarning,
    LattesResourceLimitError,
    LattesSchemaValidationError,
    LattesXmlSecurityError,
)
from comprova_lattes.parser.xml_parser import (
    DEFAULT_MAX_XML_BYTES,
    DEFAULT_MAX_XML_DEPTH,
    DIAGNOSTIC_INVALID_WORKLOAD_HOURS,
    LattesParseDiagnostic,
    LattesParseResult,
    parse_lattes_xml,
    parse_lattes_xml_with_report,
)

__all__ = [
    "DEFAULT_MAX_XML_BYTES",
    "DEFAULT_MAX_XML_DEPTH",
    "DIAGNOSTIC_INVALID_WORKLOAD_HOURS",
    "LattesEncodingError",
    "LattesInvalidRootError",
    "LattesMalformedXmlError",
    "LattesNumericValueError",
    "LattesParseDiagnostic",
    "LattesParseResult",
    "LattesParserError",
    "LattesParserWarning",
    "LattesResourceLimitError",
    "LattesSchemaValidationError",
    "LattesXmlSecurityError",
    "parse_lattes_xml",
    "parse_lattes_xml_with_report",
]
