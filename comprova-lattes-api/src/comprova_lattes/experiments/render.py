"""Renderização documental grayscale determinística via Pillow (PNG e PDF com mesmos pixels)."""

import random
import struct
import unicodedata
import zlib
from functools import lru_cache

RASTERIZER_VERSION = "pillow-aileron-gray-v1"
PILLOW_DEPENDENCY = "pillow>=11.0.0"

_COMBINING_MARKS = frozenset({"\u0300", "\u0301", "\u0302", "\u0303", "\u0308", "\u0327"})
_NATIVE_EXTRA = frozenset("©«°±´·»")
_SYNTHETIC_SYMBOLS = frozenset("ºª–—§")
_PT_BR_ACCENTED = (
    "ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑÝ"
    "áàâãäéèêëíìîïóòôõöúùûüçñýÿŸ"
)

# Mantido por compatibilidade com testes de alfabeto existentes na suíte experimental.
_BASE_GLYPHS = {
    "A": "01110100011000111111100011000110001",
    "B": "11110100011000111110100011000111110",
    "C": "01111100001000010000100001000001111",
    "D": "11110100011000110001100011000111110",
    "E": "11111100001000011110100001000011111",
    "F": "11111100001000011110100001000010000",
    "G": "01111100001000010111100011000101111",
    "H": "10001100011000111111100011000110001",
    "I": "11111001000010000100001000010011111",
    "J": "00111000100001000010100101001001100",
    "K": "10001100101010011000101001001010001",
    "L": "10000100001000010000100001000011111",
    "M": "10001110111010110101100011000110001",
    "N": "10001110011010110011100011000110001",
    "O": "01110100011000110001100011000101110",
    "P": "11110100011000111110100001000010000",
    "Q": "01110100011000110001101011001001101",
    "R": "11110100011000111110101001001010001",
    "S": "01111100001000001110000010000111110",
    "T": "11111001000010000100001000010000100",
    "U": "10001100011000110001100011000101110",
    "V": "10001100011000110001100010101000100",
    "W": "10001100011000110101101011010101010",
    "X": "10001100010101000100010101000110001",
    "Y": "10001100010101000100001000010000100",
    "Z": "11111000010001000100010001000011111",
    "0": "01110100011001110101110011000101110",
    "1": "00100011000010000100001000010001110",
    "2": "01110100010000100010001000100011111",
    "3": "11110000010000101110000010000111110",
    "4": "00010001100101010010111110001000010",
    "5": "11111100001000011110000010000111110",
    "6": "01110100001000011110100011000101110",
    "7": "11111000010001000100010000100001000",
    "8": "01110100011000101110100011000101110",
    "9": "01110100011000101111000010000101110",
    ":": "00000001000010000000001000010000000",
    ".": "00000000000000000000000000010000100",
    "_": "00000000000000000000000000000011111",
    "-": "00000000000000011111000000000000000",
    "(": "00010001000100001000010000010000010",
    ")": "01000001000001000010000100010001000",
}

_ASCII_PRINTABLE = tuple(chr(code) for code in range(33, 127))
_ALL_GLYPH_CHARS = (*_ASCII_PRINTABLE, *_PT_BR_ACCENTED, *_NATIVE_EXTRA, *_SYNTHETIC_SYMBOLS)
_GLYPHS: dict[str, str] = {
    **dict.fromkeys(_ALL_GLYPH_CHARS, "1" * 35),
    **_BASE_GLYPHS,
}
SUPPORTED_CHARS = frozenset(_GLYPHS) | frozenset({" ", "\n", "\r", "\t", "\u00a0"})


@lru_cache(maxsize=1)
def _load_pillow():
    try:
        import PIL
        from PIL import Image, ImageDraw, ImageFont, features
    except ImportError as exc:
        raise RuntimeError(
            "Pillow é obrigatório para a bancada de renderização documental "
            "(instale a dependência opcional .[experiments])."
        ) from exc
    return PIL, Image, ImageDraw, ImageFont, features


@lru_cache(maxsize=32)
def _font(size: int):
    _, _, _, image_font, _ = _load_pillow()
    return image_font.load_default(size=size)


@lru_cache(maxsize=512)
def _glyph_metrics(size: int, char: str) -> tuple[int, int, int, int, int]:
    font = _font(size)
    bbox = font.getbbox(char)
    advance = max(1, round(font.getlength(char)))
    if bbox is None:
        return 0, 0, advance, size, advance
    left, top, right, bottom = (int(v) for v in bbox)
    return left, top, right, bottom, advance


@lru_cache(maxsize=32)
def _x_height_top(size: int) -> int:
    return _glyph_metrics(size, "a")[1]


def rasterizer_metadata() -> dict[str, object]:
    """Metadados da implementação de rasterização e do ambiente Pillow/FreeType."""
    pil_mod, _, _, _, features = _load_pillow()
    ft_available = bool(features.check("freetype2"))
    ft_version = features.version_module("freetype2") if ft_available else None
    font = _font(18)
    font_name = getattr(font, "getname", lambda: ("default", "bitmap"))()
    return {
        "rasterizer": RASTERIZER_VERSION,
        "pillow_dependency": PILLOW_DEPENDENCY,
        "pillow_version": getattr(pil_mod, "__version__", None),
        "freetype_available": ft_available,
        "freetype_version": ft_version,
        "font_family": f"{font_name[0]} {font_name[1]}".strip(),
        "color_mode": "L",
        "determinism_scope": "same_pillow_freetype_build",
    }


def _decompose_char(ch: str) -> tuple[str, str | None]:
    if ch == " " or (33 <= ord(ch) <= 126) or ch in _NATIVE_EXTRA or ch in _SYNTHETIC_SYMBOLS:
        return ch, None
    nfd = unicodedata.normalize("NFD", ch)
    if (
        len(nfd) == 2
        and ("A" <= nfd[0] <= "Z" or "a" <= nfd[0] <= "z")
        and nfd[1] in _COMBINING_MARKS
    ):
        return nfd[0], nfd[1]
    raise ValueError(f"Caractere não suportado pelo rasterizador: {ch!r}")


def _tokenize_line(line: str) -> list[tuple[str, str | None]]:
    normalized = unicodedata.normalize("NFC", line.replace("\u00a0", " ").expandtabs(4))
    tokens: list[tuple[str, str | None]] = []
    idx = 0
    length = len(normalized)
    while idx < length:
        ch = normalized[idx]
        if idx + 1 < length and normalized[idx + 1] in _COMBINING_MARKS:
            mark = normalized[idx + 1]
            if not ("A" <= ch <= "Z" or "a" <= ch <= "z"):
                raise ValueError(f"Marca combinante em base não suportada: {ch!r}")
            tokens.append((ch, mark))
            idx += 2
            continue
        if ch in _COMBINING_MARKS:
            raise ValueError(f"Marca combinante isolada não suportada: {ch!r}")
        tokens.append(_decompose_char(ch))
        idx += 1
    return tokens


def _prepare_lines(text: str) -> list[list[tuple[str, str | None]]]:
    if type(text) is not str:
        raise ValueError("Texto para rasterização deve ser str")
    for ch in text:
        if ord(ch) < 32 and ch not in ("\n", "\r", "\t"):
            raise ValueError(f"Caractere de controle não suportado: {ch!r}")
        if 127 <= ord(ch) <= 159:
            raise ValueError(f"Caractere de controle C1 não suportado: {ch!r}")
    raw_lines = text.splitlines()
    if not raw_lines:
        return [[]]
    return [_tokenize_line(line) for line in raw_lines]


def _layout_spec(layout: int) -> dict[str, int | bool]:
    if type(layout) is not int or layout < 0:
        raise ValueError("Layout deve ser inteiro não negativo")
    font_size = 16 + (layout % 4) * 2
    header_size = font_size + 2 + ((layout // 4) % 3) * 2
    margin_x = 24 + (layout % 7) * 6
    margin_y = 22 + ((layout // 7) % 5) * 5
    line_gap = 8 + ((layout // 35) % 4) * 3
    body_indent = 0 if layout == 0 else ((layout // 11) % 3) * 10
    header_centered = bool((layout // 5) % 2)
    header_rule = bool((layout // 3) % 2)
    frame_style = (layout // 2) % 4
    ink = (0, 14, 28)[(layout // 29) % 3]
    tracking = (layout // 17) % 2
    return {
        "font_size": font_size,
        "header_size": header_size,
        "margin_x": margin_x,
        "margin_y": margin_y,
        "line_gap": line_gap,
        "body_indent": body_indent,
        "header_centered": header_centered,
        "header_rule": header_rule,
        "frame_style": frame_style,
        "ink": ink,
        "tracking": tracking,
    }


def _token_advance(size: int, base: str, tracking: int) -> int:
    if base in ("º", "ª"):
        small = max(10, round(size * 0.65))
        return _glyph_metrics(small, "o" if base == "º" else "a")[4] + 2 + tracking
    if base == "–":
        return max(6, round(size * 0.55)) + tracking
    if base == "—":
        return max(10, round(size * 0.85)) + tracking
    if base == "§":
        small = max(10, round(size * 0.7))
        return _glyph_metrics(small, "S")[4] + 2 + tracking
    return _glyph_metrics(size, base)[4] + tracking


def _line_width(tokens: list[tuple[str, str | None]], size: int, tracking: int) -> int:
    if not tokens:
        return 0
    total = sum(_token_advance(size, base, tracking) for base, _ in tokens)
    return max(0, total - tracking)


def _draw_diacritic(
    draw,
    *,
    mark: str,
    x: int,
    y: int,
    size: int,
    base: str,
    ink: int,
) -> None:
    left, top, right, bottom, _ = _glyph_metrics(size, base)
    stroke = 1 if size < 20 else 2
    if base == "i" and mark != "\u0327":
        x_top = _x_height_top(size)
        draw.rectangle(
            [x + left - 1, y + top - 1, x + right + 1, y + x_top - 1],
            fill=255,
        )
        top = x_top
    cx = round(x + (left + right) / 2.0)
    span = max(2, round((right - left) * 0.30))
    rise = max(3, round(size * 0.18))
    top_y = y + top
    bot_y = y + bottom
    if mark == "\u0301":  # agudo
        draw.line(
            [(cx - span + 1, top_y - 2), (cx + span, top_y - 2 - rise)],
            fill=ink,
            width=stroke,
        )
    elif mark == "\u0300":  # grave
        draw.line(
            [(cx - span, top_y - 2 - rise), (cx + span - 1, top_y - 2)],
            fill=ink,
            width=stroke,
        )
    elif mark == "\u0302":  # circunflexo
        draw.line(
            [(cx - span, top_y - 2), (cx, top_y - 2 - rise), (cx + span, top_y - 2)],
            fill=ink,
            width=stroke,
        )
    elif mark == "\u0303":  # til
        half = max(1, rise // 2)
        draw.line(
            [
                (cx - span - 1, top_y - 2),
                (cx - 1, top_y - 2 - half - 1),
                (cx + 1, top_y - 2),
                (cx + span + 1, top_y - 2 - half - 1),
            ],
            fill=ink,
            width=1,
        )
    elif mark == "\u0308":  # trema
        dot_y = top_y - 3 - stroke
        draw.rectangle([cx - span, dot_y, cx - span + stroke - 1, dot_y + stroke - 1], fill=ink)
        draw.rectangle([cx + span - stroke + 1, dot_y, cx + span, dot_y + stroke - 1], fill=ink)
    elif mark == "\u0327":  # cedilha
        draw.line(
            [(cx, bot_y - 1), (cx + 1, bot_y + 2), (cx - span, bot_y + 3)],
            fill=ink,
            width=1,
        )


def _draw_synthetic_symbol(draw, *, symbol: str, x: int, y: int, size: int, ink: int) -> None:
    if symbol in ("º", "ª"):
        small_size = max(10, round(size * 0.65))
        letter = "o" if symbol == "º" else "a"
        draw.text((x + 1, y + 1), letter, fill=ink, font=_font(small_size))
        left, _, right, bottom, _ = _glyph_metrics(small_size, letter)
        draw.line(
            [(x + left + 1, y + bottom + 2), (x + right + 1, y + bottom + 2)],
            fill=ink,
            width=1,
        )
    elif symbol in ("–", "—"):
        adv = _token_advance(size, symbol, 0)
        mid_y = y + round(size * 0.62)
        draw.line([(x + 1, mid_y), (x + adv - 2, mid_y)], fill=ink, width=1 if size < 20 else 2)
    elif symbol == "§":
        small_size = max(10, round(size * 0.7))
        small_font = _font(small_size)
        draw.text((x + 1, y + 1), "S", fill=ink, font=small_font)
        draw.text((x + 1, y + round(size * 0.28)), "S", fill=ink, font=small_font)


def _draw_line(
    draw,
    tokens: list[tuple[str, str | None]],
    *,
    x: int,
    y: int,
    size: int,
    tracking: int,
    ink: int,
) -> None:
    font = _font(size)
    cursor_x = x
    plain_start = cursor_x
    plain_chars: list[str] = []

    def flush_plain() -> None:
        nonlocal plain_chars
        if plain_chars:
            draw.text((plain_start, y), "".join(plain_chars), fill=ink, font=font)
            plain_chars = []

    for base, mark in tokens:
        adv = _token_advance(size, base, tracking)
        if mark is None and base not in _SYNTHETIC_SYMBOLS and tracking == 0:
            if not plain_chars:
                plain_start = cursor_x
            plain_chars.append(base)
        else:
            flush_plain()
            if base in _SYNTHETIC_SYMBOLS:
                _draw_synthetic_symbol(draw, symbol=base, x=cursor_x, y=y, size=size, ink=ink)
            else:
                draw.text((cursor_x, y), base, fill=ink, font=font)
                if mark is not None:
                    _draw_diacritic(
                        draw,
                        mark=mark,
                        x=cursor_x,
                        y=y,
                        size=size,
                        base=base,
                        ink=ink,
                    )
        cursor_x += adv
    flush_plain()


def _draw_frame(draw, *, width: int, height: int, frame_style: int, ink: int) -> None:
    if frame_style == 0:
        return
    inset = 8
    if frame_style == 1:
        draw.rectangle([inset, inset, width - 1 - inset, height - 1 - inset], outline=ink, width=1)
    elif frame_style == 2:
        draw.rectangle([inset, inset, width - 1 - inset, height - 1 - inset], outline=ink, width=2)
    elif frame_style == 3:
        draw.rectangle([inset, inset, width - 1 - inset, height - 1 - inset], outline=ink, width=1)
        inner = inset + 4
        draw.rectangle([inner, inner, width - 1 - inner, height - 1 - inner], outline=ink, width=1)


def raster(text: str, *, seed: int, degradation: int, layout: int) -> tuple[int, int, bytes]:
    if type(degradation) is not int or degradation not in (0, 1, 2):
        raise ValueError("Degradação deve ser 0, 1 ou 2")
    if type(seed) is not int:
        raise ValueError("Seed deve ser inteiro")
    lines = _prepare_lines(text)
    spec = _layout_spec(layout)
    _, image_cls, draw_cls, _, _ = _load_pillow()

    font_size = int(spec["font_size"])
    header_size = int(spec["header_size"])
    margin_x = int(spec["margin_x"])
    margin_y = int(spec["margin_y"])
    line_gap = int(spec["line_gap"])
    body_indent = int(spec["body_indent"])
    tracking = int(spec["tracking"])
    ink = int(spec["ink"])
    header_centered = bool(spec["header_centered"])
    header_rule = bool(spec["header_rule"])
    frame_style = int(spec["frame_style"])

    line_sizes = [header_size if idx == 0 else font_size for idx in range(len(lines))]
    line_indents = [0 if idx == 0 else body_indent for idx in range(len(lines))]
    line_widths = [
        _line_width(tokens, size, tracking) + indent
        for tokens, size, indent in zip(lines, line_sizes, line_indents, strict=True)
    ]

    top_accent_pad = max(8, round(header_size * 0.40))
    bottom_pad = max(8, round(font_size * 0.35))
    rule_extra = 6 if (header_rule and len(lines) > 1) else 0

    raw_width = max(600, max(line_widths, default=0) + 2 * margin_x + 16)
    width = raw_width + (raw_width % 2)
    total_text_height = sum(line_sizes) + max(0, len(lines) - 1) * line_gap + rule_extra
    height = max(120, 2 * margin_y + top_accent_pad + total_text_height + bottom_pad)

    image = image_cls.new("L", (width, height), color=255)
    draw = draw_cls.Draw(image)
    _draw_frame(draw, width=width, height=height, frame_style=frame_style, ink=ink)

    cursor_y = margin_y + top_accent_pad
    for idx, (tokens, size, indent) in enumerate(
        zip(lines, line_sizes, line_indents, strict=True)
    ):
        lw = _line_width(tokens, size, tracking)
        if idx == 0 and header_centered and lw > 0:
            x = max(margin_x, (width - lw) // 2)
        else:
            x = margin_x + indent
        _draw_line(draw, tokens, x=x, y=cursor_y, size=size, tracking=tracking, ink=ink)
        cursor_y += size
        if idx == 0 and rule_extra:
            rule_y = cursor_y + 3
            draw.line([(margin_x, rule_y), (width - margin_x, rule_y)], fill=ink, width=1)
            cursor_y += rule_extra
        cursor_y += line_gap

    raw_bytes = image.tobytes()
    if not degradation:
        return width, height, raw_bytes

    rng = random.Random(seed)
    pixels = bytearray([255]) * (width * height)
    # Inclinação leve, resolução horizontal reduzida e ruído sal/pimenta determinísticos.
    for y in range(height):
        shift = int((y - height / 2) * 0.008 * degradation)
        row_start = y * width
        row = raw_bytes[row_start : row_start + width]
        if shift >= width or shift <= -width:
            continue
        if degradation == 2:
            half = row[0::2]
            quantized = bytearray(width)
            quantized[0::2] = half
            quantized[1::2] = half
            row = quantized
        if shift >= 0:
            pixels[row_start + shift : row_start + width] = row[: width - shift]
        else:
            s = -shift
            pixels[row_start : row_start + width - s] = row[s:]
    for _ in range(width * height * degradation // 300):
        pixels[rng.randrange(len(pixels))] = rng.choice((0, 210, 255))
    return width, height, bytes(pixels)


def _validate_raster_buffer(width: int, height: int, pixels: bytes) -> None:
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        raise ValueError("Dimensões devem ser inteiros positivos")
    if not isinstance(pixels, (bytes, bytearray, memoryview)) or len(pixels) != width * height:
        raise ValueError("Buffer de pixels grayscale incompatível com width * height")


def png(width: int, height: int, pixels: bytes) -> bytes:
    _validate_raster_buffer(width, height, pixels)
    raw = bytes(pixels)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data))
        )

    scan = b"".join(b"\0" + raw[y * width : (y + 1) * width] for y in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!2I5B", width, height, 8, 0, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(scan))
        + chunk(b"IEND", b"")
    )


def pdf(width: int, height: int, pixels: bytes) -> bytes:
    _validate_raster_buffer(width, height, pixels)
    raw = bytes(pixels)
    image = zlib.compress(raw)
    content = f"q {width} 0 0 {height} 0 0 cm /Im0 Do Q".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
        "/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>".encode(),
        f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} "
        f"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode "
        f"/Length {len(image)} >>\nstream\n".encode()
        + image
        + b"\nendstream",
        f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream",
    ]
    result, offsets = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"), [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    start = len(result)
    result.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        result.extend(f"{offset:010} 00000 n \n".encode())
    result.extend(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode())
    return bytes(result)
