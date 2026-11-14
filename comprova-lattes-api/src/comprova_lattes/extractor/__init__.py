"""Extração de entidades multimodais; decisões pertencem ao motor determinístico."""

from .gemini import GeminiExtractor
from .models import ExtractionPayload

__all__ = ["ExtractionPayload", "GeminiExtractor"]
