"""
Zebra ZPL II Printer Protocol Encoder.
Converts 1-bit raw monochrome bitmap bytes to ZPL ^GFA (Graphic Field ASCII Hex) format.
"""

from __future__ import annotations


def encode_zpl(
    raw_bytes: bytes,
    width_px: int,
    height_px: int,
    x: int = 0,
    y: int = 0,
) -> str:
    """
    Encodes raw 1-bit monochrome bytes into Zebra ZPL format.
    
    ZPL Graphics Format:
    ^XA
    ^FO<x>,<y>^GFA,<binary_byte_count>,<graphic_field_count>,<bytes_per_row>,<hex_data>^FS
    ^XZ
    
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
        f"^FO{x},{y}^GFA,{total_bytes},{total_bytes},{bytes_per_row},{hex_data}^FS\n"
        "^XZ\n"
    )
    return zpl
