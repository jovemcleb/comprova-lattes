"""Testes focais da renderização documental grayscale com Pillow."""

import io
import struct
import sys
import unicodedata
import zlib

import pytest
from PIL import Image

from comprova_lattes.experiments.render import (
    _GLYPHS,
    PILLOW_DEPENDENCY,
    RASTERIZER_VERSION,
    SUPPORTED_CHARS,
    pdf,
    png,
    raster,
    rasterizer_metadata,
)


def _extract_pdf_stream(pdf_bytes: bytes) -> bytes:
    assert pdf_bytes.startswith(b"%PDF-1.4") and pdf_bytes.endswith(b"%%EOF\n")
    assert b"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode" in pdf_bytes
    start = int(pdf_bytes.split(b"startxref\n")[1].splitlines()[0])
    assert pdf_bytes[start : start + 4] == b"xref"
    entries = pdf_bytes[start:].splitlines()[3:8]
    for idx, entry in enumerate(entries, 1):
        assert pdf_bytes[int(entry[:10]) :].startswith(f"{idx} 0 obj".encode())
    compressed = pdf_bytes.split(b"stream\n", 1)[1].split(b"\nendstream")[0]
    return zlib.decompress(compressed)


def _extract_png_scanlines(png_bytes: bytes, width: int, height: int) -> bytes:
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    offset = 8
    idat = bytearray()
    while offset < len(png_bytes):
        size = struct.unpack("!I", png_bytes[offset : offset + 4])[0]
        kind = png_bytes[offset + 4 : offset + 8]
        data = png_bytes[offset + 8 : offset + 8 + size]
        crc_expected = struct.unpack("!I", png_bytes[offset + 8 + size : offset + 12 + size])[0]
        assert zlib.crc32(kind + data) == crc_expected
        if kind == b"IHDR":
            w, h, depth, color_type, comp, flt, interlace = struct.unpack("!2I5B", data)
            assert (w, h, depth, color_type, comp, flt, interlace) == (
                width,
                height,
                8,
                0,
                0,
                0,
                0,
            )
        elif kind == b"IDAT":
            idat.extend(data)
        offset += 12 + size
    raw_scan = zlib.decompress(bytes(idat))
    stride = width + 1
    assert len(raw_scan) == stride * height
    rows = []
    for y in range(height):
        row = raw_scan[y * stride : (y + 1) * stride]
        assert row[0] == 0
        rows.append(row[1:])
    return b"".join(rows)


def test_rasterizer_metadata_and_legacy_glyphs_export():
    meta = rasterizer_metadata()
    assert meta["rasterizer"] == RASTERIZER_VERSION
    assert meta["pillow_dependency"] == PILLOW_DEPENDENCY
    assert isinstance(meta["pillow_version"], str) and meta["pillow_version"]
    assert meta["freetype_available"] is True
    assert isinstance(meta["freetype_version"], str) and meta["freetype_version"]
    assert "Aileron" in str(meta["font_family"])
    assert meta["color_mode"] == "L"
    assert meta["determinism_scope"] == "same_pillow_freetype_build"
    for required in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:._-()ÁÀÂÃÉÊÍÓÔÕÚÜÇáàâãéêíóôõúüç":
        assert required in _GLYPHS
        assert required in SUPPORTED_CHARS


def test_pt_br_accents_and_parentheses_are_rendered_and_distinct():
    groups = [
        ("A", "Á", "À", "Â", "Ã", "Ä"),
        ("a", "á", "à", "â", "ã", "ä"),
        ("E", "É", "È", "Ê", "Ë"),
        ("e", "é", "è", "ê", "ë"),
        ("I", "Í", "Ì", "Î", "Ï"),
        ("i", "í", "ì", "î", "ï"),
        ("O", "Ó", "Ò", "Ô", "Õ", "Ö"),
        ("o", "ó", "ò", "ô", "õ", "ö"),
        ("U", "Ú", "Ù", "Û", "Ü"),
        ("u", "ú", "ù", "û", "ü"),
        ("C", "Ç"),
        ("c", "ç"),
        ("(", ")"),
    ]
    blank = raster("", seed=1, degradation=0, layout=0)[2]
    for group in groups:
        rendered = {}
        for token in group:
            w, h, pixels = raster(token, seed=1, degradation=0, layout=0)
            assert len(pixels) == w * h
            assert any(b < 255 for b in pixels), f"Caractere sem tinta: {token!r}"
            assert pixels != blank
            rendered[token] = pixels
        assert len(set(rendered.values())) == len(group), f"Colisão de glifos no grupo: {group}"


def test_nfc_and_nfd_equivalence_and_no_silent_character_erasure():
    sample = (
        "CERTIFICADO DE FORMAÇÃO ACADÊMICA (PÓS-GRADUAÇÃO)\n"
        "Instituição: Instituto Fictício de Educação, Ciência e Tecnologia (IF-PA)\n"
        "Participação: Apresentação de Lições Práticas — 1º Semestre / 2ª Edição"
    )
    nfd_sample = unicodedata.normalize("NFD", sample)
    out_nfc = raster(sample, seed=10, degradation=0, layout=3)
    out_nfd = raster(nfd_sample, seed=10, degradation=0, layout=3)
    assert out_nfc == out_nfd

    without_parens = sample.replace("(", "").replace(")", "")
    assert raster(without_parens, seed=10, degradation=0, layout=3)[2] != out_nfc[2]

    base_prefix = "TITULAR: JOAO "
    prev_pixels = raster(base_prefix, seed=1, degradation=0, layout=0)[2]
    for ch in ("(", ")", "Á", "Ã", "Ç", "É", "Ê", "Í", "Ó", "Õ", "Ú", "ç", "ã", "º", "ª", "—"):
        cur_pixels = raster(base_prefix + ch, seed=1, degradation=0, layout=0)[2]
        assert cur_pixels != prev_pixels, f"Caractere apagado silenciosamente: {ch!r}"


def test_determinism_by_seed_degradation_and_layout_variation():
    text = "CERTIFICADO FICTÍCIO\nholder_name: PESSOA SINTÉTICA (UFRA)\nworkload_hours: 40"
    clean_a = raster(text, seed=7, degradation=0, layout=4)
    clean_b = raster(text, seed=999, degradation=0, layout=4)
    assert clean_a == clean_b

    deg1_a = raster(text, seed=7, degradation=1, layout=4)
    deg1_b = raster(text, seed=7, degradation=1, layout=4)
    deg1_other_seed = raster(text, seed=8, degradation=1, layout=4)
    deg2 = raster(text, seed=7, degradation=2, layout=4)
    assert deg1_a == deg1_b
    assert deg1_a[2] != clean_a[2]
    assert deg1_a[2] != deg1_other_seed[2]
    assert deg2[2] != deg1_a[2]

    layouts = [raster(text, seed=7, degradation=0, layout=k) for k in range(12)]
    assert len({item[2] for item in layouts}) == 12
    assert len({(item[0], item[1]) for item in layouts}) >= 4


def test_png_and_pdf_wrap_identical_grayscale_raster_matrix():
    text = "DECLARAÇÃO INSTITUCIONAL (IF01)\nTitular: Conceição Araújo\nCarga Horária: 45h"
    for level in (0, 1, 2):
        width, height, pixels = raster(text, seed=42, degradation=level, layout=9)
        assert isinstance(pixels, bytes)
        assert len(pixels) == width * height

        png_bytes = png(width, height, pixels)
        pdf_bytes = pdf(width, height, pixels)

        scanline_pixels = _extract_png_scanlines(png_bytes, width, height)
        pdf_pixels = _extract_pdf_stream(pdf_bytes)
        with Image.open(io.BytesIO(png_bytes)) as decoded_img:
            assert decoded_img.mode == "L"
            assert decoded_img.size == (width, height)
            pil_pixels = decoded_img.tobytes()

        assert scanline_pixels == pixels
        assert pdf_pixels == pixels
        assert pil_pixels == pixels


@pytest.mark.parametrize(
    "call",
    [
        lambda: raster("ABC", seed=1, degradation=-1, layout=0),
        lambda: raster("ABC", seed=1, degradation=3, layout=0),
        lambda: raster("ABC", seed=1, degradation=True, layout=0),
        lambda: raster("ABC", seed=True, degradation=0, layout=0),
        lambda: raster("ABC", seed=1, degradation=0, layout=-1),
        lambda: raster("ABC", seed=1, degradation=0, layout=False),
        lambda: raster("ABC\x00DEF", seed=1, degradation=0, layout=0),
        lambda: raster("ABC\x7fDEF", seed=1, degradation=0, layout=0),
        lambda: raster("ABC\u2603DEF", seed=1, degradation=0, layout=0),
        lambda: raster("\u0301ABC", seed=1, degradation=0, layout=0),
        lambda: raster("1\u0301", seed=1, degradation=0, layout=0),
        lambda: png(0, 10, b""),
        lambda: png(10, 0, b""),
        lambda: png(True, 1, b"\xff"),
        lambda: png(4, 4, b"\xff" * 15),
        lambda: pdf(0, 10, b""),
        lambda: pdf(4, 4, b"\xff" * 17),
    ],
)
def test_invalid_inputs_and_boundaries_raise_value_error(call):
    with pytest.raises(ValueError):
        call()


def test_core_parser_and_matcher_import_without_pillow(monkeypatch):
    prefixes = ("PIL.", "comprova_lattes.parser", "comprova_lattes.matcher")
    for mod_name in list(sys.modules):
        if mod_name == "PIL" or mod_name.startswith(prefixes):
            monkeypatch.delitem(sys.modules, mod_name, raising=False)
    monkeypatch.setitem(sys.modules, "PIL", None)
    import importlib

    parser_mod = importlib.import_module("comprova_lattes.parser")
    matcher_mod = importlib.import_module("comprova_lattes.matcher")
    assert callable(parser_mod.parse_lattes_xml)
    assert callable(matcher_mod.match_curriculum)
