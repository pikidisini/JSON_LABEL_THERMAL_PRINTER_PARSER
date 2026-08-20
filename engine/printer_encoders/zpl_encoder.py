"""
Zebra ZPL II Printer Protocol Encoder.
Converts 1-bit raw monochrome bitmap bytes to ZPL ^GFA (Graphic Field ASCII Hex) format.
"""

from __future__ import annotations
from typing import Optional


def encode_zpl(
    raw_bytes: bytes,
    width_px: int,
    height_px: int,
    x: int = 0,
    y: int = 0,
    width_mm: Optional[float] = None,
    height_mm: Optional[float] = None,
) -> str:
    """
    Encodes raw 1-bit monochrome bytes into Zebra ZPL format.
    
    ZPL Graphics Format:
    ^XA
    ^PW<width_in_dots>
    ^LL<height_in_dots>
    ^FO<x>,<y>^GFA,<binary_byte_count>,<graphic_field_count>,<bytes_per_row>,<hex_data>^FS
    ^XZ
    
    - ^PW: Sets print width in dots (matching the active rotated media width)
    - ^LL: Sets label length in dots (matching the active rotated media height)
    - binary_byte_count: total bytes of graphic data (len(raw_bytes))
    - graphic_field_count: total bytes of graphic data
    - bytes_per_row: width_px // 8
    - hex_data: uppercase hex string of raw_bytes
    """
    bytes_per_row = (width_px + 7) // 8
    total_bytes = len(raw_bytes)
    hex_data = raw_bytes.hex().upper()

    zpl = (
        "^XA\n"
        f"^PW{width_px}\n"
        f"^LL{height_px}\n"
        f"^FO{x},{y}^GFA,{total_bytes},{total_bytes},{bytes_per_row},{hex_data}^FS\n"
        "^XZ\n"
    )
    return zpl

