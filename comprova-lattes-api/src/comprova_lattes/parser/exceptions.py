"""Exceções tipadas do módulo de parsing XML do Currículo Lattes."""

from __future__ import annotations


class LattesParserError(Exception):
    """Erro base para falhas no parsing seguro do XML Lattes."""


class LattesEncodingError(LattesParserError):
    """Codificação declarada inválida, ausente/incompatível ou não suportada."""


class LattesXmlSecurityError(LattesParserError):
    """Violação de segurança XML (DTD, entidades internas/externas ou referências externas)."""


class LattesResourceLimitError(LattesParserError):
    """Violação de limite operacional de recursos no payload XML (bytes ou profundidade)."""


class LattesMalformedXmlError(LattesParserError):
    """Documento XML vazio, truncado ou sintaticamente malformado."""


class LattesInvalidRootError(LattesParserError):
    """Elemento raiz diferente de CURRICULO-VITAE ou com namespace inesperado."""


class LattesNumericValueError(LattesParserError):
    """Atributo numérico inválido que exigiria truncamento ou coerção silenciosa."""


class LattesSchemaValidationError(LattesParserError):
    """Falha de validação ao instanciar os schemas canônicos Pydantic."""


class LattesParserWarning(UserWarning):
    """Aviso emitido quando o parsing simplificado descarta atributo inválido recuperável."""
