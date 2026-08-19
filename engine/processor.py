"""
Processor pipeline orchestrator for label rendering and printer encoding.

Pipeline:
1. Load & validate JSON contract (Pure Data v1.1)
2. Inject string fields & codes into SVG template placeholders
3. Generate vector Code128 and QR Code modules into bounding box rects
4. Rasterize SVG to PNG preview using resvg
5. Binarize to 1-Bit monochrome bitmap & pack bits per row
6. Encode to target printer instructions (ZPL, TSPL, IPL, PNG preview)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .renderer import load_json_contract, load_svg_template, inject_data, validate_no_orphan_tokens
from .barcode_generator import inject_barcodes_and_qr
from .rasterizer import svg_to_png, png_to_1bit_monochrome, save_1bit_bmp
from .bit_packer import get_raw_bitmap_data
from .printer_encoders import encode_zpl, encode_tspl, encode_ipl


def align_to_byte_boundary(pixels: int, alignment: int = 8) -> int:
    """
    Aligns pixel dimension (width) up to the nearest multiple of alignment (default 8 dots / 1 byte).
    Ensures bitmap row-padding and byte-stream alignment for thermal printer encoders (IPL, ZPL, TSPL).
    """
    return ((pixels + alignment - 1) // alignment) * alignment


def process_label(
    json_source: Union[str, Path, dict],
    template_source: Union[str, Path],
    out_dir: Union[str, Path],
    formats: Union[str, List[str]] = "all",
    dpi: float = 203.2,
    width_px: Optional[int] = None,
    height_px: Optional[int] = None,
    width_mm: float = 200.0,
    height_mm: float = 80.0,
) -> Dict[str, Path]:
    """
    Executes the full end-to-end rendering and encoding pipeline.
    
    Returns a dictionary mapping format names ('svg', 'png', 'bmp', 'zpl', 'tspl', 'ipl')
    to their generated file paths.
    """
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Calculate dynamic pixel resolution if not explicitly specified (aligned to 8-dot byte boundary)
    raw_w_px = int(round((width_mm / 25.4) * dpi)) if width_px is None else width_px
    target_w_px = align_to_byte_boundary(raw_w_px, alignment=8)
    target_h_px = int(round((height_mm / 25.4) * dpi)) if height_px is None else height_px

    if isinstance(formats, str):
        if formats.lower() == "all":
            selected_formats = ["svg", "png", "bmp", "zpl", "tspl", "ipl"]
        else:
            selected_formats = [f.strip().lower() for f in formats.split(",")]
    else:
        selected_formats = [f.lower() for f in formats]

    results: Dict[str, Path] = {}

    # Step 1: Load Contract & SVG Template
    contract_data = load_json_contract(json_source)
    svg_template = load_svg_template(template_source)

    # Step 2: Inject Pure Data fields & codes
    injected_svg = inject_data(svg_template, contract_data)
    validate_no_orphan_tokens(injected_svg)

    # Step 3: Inject vector Barcode & QR Code into bounding boxes
    complete_svg = inject_barcodes_and_qr(injected_svg, contract_data)

    # Save SVG if requested or always save intermediate
    svg_path = output_dir / "label.svg"
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(complete_svg)
    # Always include svg and png in results as they are core visual/inspection artifacts
    results["svg"] = svg_path

    # Step 4: Rasterize SVG to PNG preview with dynamic DPI and dimensions
    png_path = output_dir / "preview.png"
    svg_to_png(
        svg_source=complete_svg,
        output_png_path=png_path,
        width_px=target_w_px,
        height_px=target_h_px,
        dpi=dpi,
    )
    # Always include preview PNG in results (essential for UI canvas rendering)
    results["png"] = png_path

    # Step 5: Convert PNG to 1-Bit Monochrome & Save BMP
    image_1bit = png_to_1bit_monochrome(png_path)
    bmp_path = output_dir / "label_1bit.bmp"
    save_1bit_bmp(image_1bit, bmp_path)
    if "bmp" in selected_formats:
        results["bmp"] = bmp_path

    # Step 6: Bit packing
    raw_bytes, w, h, bytes_per_row = get_raw_bitmap_data(image_1bit)

    # Step 7: Encoders
    if "zpl" in selected_formats or "all" in selected_formats:
        zpl_str = encode_zpl(raw_bytes, width_px=w, height_px=h)
        zpl_path = output_dir / "label.zpl"
        with open(zpl_path, "w", encoding="ascii") as f:
            f.write(zpl_str)
        results["zpl"] = zpl_path

    if "tspl" in selected_formats or "all" in selected_formats:
        tspl_bytes = encode_tspl(
            raw_bytes,
            width_px=w,
            height_px=h,
            width_mm=width_mm,
            height_mm=height_mm,
        )
        tspl_path = output_dir / "label.tspl"
        with open(tspl_path, "wb") as f:
            f.write(tspl_bytes)
        results["tspl"] = tspl_path

    if "ipl" in selected_formats or "all" in selected_formats:
        ipl_bytes = encode_ipl(raw_bytes, width_px=w, height_px=h)
        ipl_path = output_dir / "label.ipl"
        with open(ipl_path, "wb") as f:
            f.write(ipl_bytes)
        results["ipl"] = ipl_path

    return results

