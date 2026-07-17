"""Generate minimal solid-color PNG icons for PWA scaffolding."""
import struct
import zlib


def make_png(size: int, rgb: tuple[int, int, int]) -> bytes:
    w = h = size
    r, g, b = rgb
    # One row: filter byte (0) + RGB pixels
    row = bytes([0] + [r, g, b] * w)
    raw = row * h
    compressed = zlib.compress(raw)

    def chunk(tag: bytes, data: bytes) -> bytes:
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)

    signature = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    return (
        signature
        + chunk(b'IHDR', ihdr_data)
        + chunk(b'IDAT', compressed)
        + chunk(b'IEND', b'')
    )


# Dark zinc background (#09090b ≈ oklch(0.145 0 0))
color = (9, 9, 11)

icons_dir = __import__('pathlib').Path(__file__).parent / 'public' / 'icons'
icons_dir.mkdir(parents=True, exist_ok=True)

for size, name in [(192, 'icon-192'), (512, 'icon-512'), (180, 'icon-180')]:
    (icons_dir / f'{name}.png').write_bytes(make_png(size, color))
    print(f'  {name}.png ({size}x{size})')

print('Icons generated.')
