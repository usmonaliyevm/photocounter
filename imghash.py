"""Rasm "barmoq izi" (dHash, 16x16 = 256 bit) va ikki iz orasidagi farq.

Bir xil rasm qayta yuklansa (Telegram qayta siqsa, o'lcham o'zgarsa ham) farq
juda kichik bo'ladi; boshqa rasm bo'lsa farq katta bo'ladi.
"""
import io

from PIL import Image, ImageOps

HASH_SIZE = 16  # 16x16 bit = 256 bit, hex ko'rinishida 64 belgi


def dhash(data: bytes, size: int = HASH_SIZE) -> str:
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img).convert("L").resize((size + 1, size), Image.LANCZOS)
    px = img.load()
    bits = 0
    for y in range(size):
        for x in range(size):
            bits = (bits << 1) | (1 if px[x, y] < px[x + 1, y] else 0)
    return f"{bits:0{size * size // 4}x}"


def distance(h1: str, h2: str) -> int:
    """Hamming masofasi: nechta bit farq qiladi (0 = bir xil)."""
    return bin(int(h1, 16) ^ int(h2, 16)).count("1")
