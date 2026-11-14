"""PDF raster e PNG em stdlib. Pixels degradados são os mesmos nos dois formatos."""

import random
import struct
import zlib

# Fonte bitmap 5x7 embarcada; evita dependência de fontes/renderer do host.
_GLYPHS = {
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
}


def raster(text: str, *, seed: int, degradation: int, layout: int) -> tuple[int, int, bytes]:
    if degradation not in (0, 1, 2):
        raise ValueError("Degradação deve ser 0, 1 ou 2")
    lines = text.upper().splitlines()
    scale = 2 + layout % 2
    width = max(600, (max(map(len, lines), default=0) * 6 + 30) * scale)
    height = (len(lines) * 11 + 40) * scale
    pixels = bytearray([255]) * (width * height)
    for row, line in enumerate(lines):
        for col, char in enumerate(line):
            glyph = _GLYPHS.get(char, "0" * 35)
            for i, bit in enumerate(glyph):
                if bit == "1":
                    for dy in range(scale):
                        y = (row * 11 + 20 + i // 5) * scale + dy
                        for dx in range(scale):
                            x = (col * 6 + 12 + i % 5) * scale + dx
                            pixels[y * width + x] = 0
    if degradation:
        rng = random.Random(seed)
        original = bytes(pixels)
        # Inclinação leve, resolução horizontal reduzida e ruído sal/pimenta.
        for y in range(height):
            shift = int((y - height / 2) * 0.008 * degradation)
            for x in range(width):
                source = ((x - shift) // degradation) * degradation
                pixels[y * width + x] = original[y * width + source] if 0 <= source < width else 255
        for _ in range(width * height * degradation // 300):
            pixels[rng.randrange(len(pixels))] = rng.choice((0, 210, 255))
    return width, height, bytes(pixels)


def png(width: int, height: int, pixels: bytes) -> bytes:
    def chunk(kind, data):
        return (
            struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data))
        )

    scan = b"".join(b"\0" + pixels[y * width : (y + 1) * width] for y in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!2I5B", width, height, 8, 0, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(scan))
        + chunk(b"IEND", b"")
    )


def pdf(width: int, height: int, pixels: bytes) -> bytes:
    image = zlib.compress(pixels)
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
