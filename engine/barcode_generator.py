"""
Barcode and QR Code generator and SVG bounding box injector.
Supports Code128-B (via python-barcode) and QR Code 2D Matrix (via qrcode).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from barcode import Code128
import qrcode
from qrcode.constants import ERROR_CORRECT_M


def generate_code128_pattern(code: str) -> str:
    """Generates a 1D bit string ('1' for bar, '0' for space) for Code128."""
    if not code:
        return ""
    bc = Code128(code, writer=None)
    built_pattern = bc.build()
    if not built_pattern or not isinstance(built_pattern, list):
        raise ValueError(f"Failed to generate Code128 pattern for code: '{code}'")
    return built_pattern[0]


def generate_qr_matrix(payload: str, error_correction=ERROR_CORRECT_M) -> List[List[bool]]:
    """Generates a 2D boolean matrix for QR code payload. True = black module."""
    if not payload:
        return []
    qr = qrcode.QRCode(
        error_correction=error_correction,
        box_size=1,
        border=0,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    return qr.get_matrix()

def create_barcode_svg_group(
    code_value: str,
    x: float,
    y: float,
    width: float,
    height: float,
    group_id: Optional[str] = None,
) -> ET.Element:
    """Creates an SVG <g> containing consolidated <path> for 1D barcode with crispEdges."""
    group = ET.Element("g")
    if group_id:
        group.set("id", group_id)

    pattern = generate_code128_pattern(code_value)
    if not pattern:
        return group

    total_modules = len(pattern)
    module_width = width / float(total_modules)

    path_d = []
    idx = 0
    while idx < total_modules:
        if pattern[idx] == "1":
            start_idx = idx
            while idx < total_modules and pattern[idx] == "1":
                idx += 1
            run_length = idx - start_idx
            x0 = x + (start_idx * module_width)
            x1 = x + ((start_idx + run_length) * module_width)
            y0 = y
            y1 = y + height
            path_d.append(f"M{x0:.4f},{y0:.4f}H{x1:.4f}V{y1:.4f}H{x0:.4f}Z")
        else:
            idx += 1

    if path_d:
        path_elem = ET.Element("path")
        path_elem.set("d", " ".join(path_d))
        path_elem.set("fill", "#000000")
        path_elem.set("stroke", "none")
        path_elem.set("shape-rendering", "crispEdges")
        group.append(path_elem)

    return group


def create_qr_svg_group(
    payload: str,
    x: float,
    y: float,
    width: float,
    height: float,
    group_id: Optional[str] = None,
) -> ET.Element:
    """Creates an SVG <g> containing consolidated horizontal run-length <path> for 2D QR Code with crispEdges."""
    group = ET.Element("g")
    if group_id:
        group.set("id", group_id)

    matrix = generate_qr_matrix(payload)
    if not matrix:
        return group

    rows = len(matrix)
    cols = len(matrix[0]) if rows > 0 else 0
    if rows == 0 or cols == 0:
        return group

    box_size = min(width / cols, height / rows)
    offset_x = x + (width - (cols * box_size)) / 2.0
    offset_y = y + (height - (rows * box_size)) / 2.0

    path_d = []
    for r in range(rows):
        c = 0
        while c < cols:
            if matrix[r][c]:
                start_c = c
                while c < cols and matrix[r][c]:
                    c += 1
                span = c - start_c
                x0 = offset_x + (start_c * box_size)
                x1 = offset_x + ((start_c + span) * box_size)
                y0 = offset_y + (r * box_size)
                y1 = offset_y + ((r + 1) * box_size)
                path_d.append(f"M{x0:.4f},{y0:.4f}H{x1:.4f}V{y1:.4f}H{x0:.4f}Z")
            else:
                c += 1

    if path_d:
        path_elem = ET.Element("path")
        path_elem.set("d", " ".join(path_d))
        path_elem.set("fill", "#000000")
        path_elem.set("stroke", "none")
        path_elem.set("shape-rendering", "crispEdges")
        group.append(path_elem)

    return group


def inject_barcodes_and_qr(svg_content: str, contract_data: Dict[str, Any]) -> str:
    """
    Parses SVG XML, replaces <rect data-barcode="..."> and <rect data-qr="...">
    with generated vector barcode groups.
    """
    codes = contract_data.get("codes", {})
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    root = ET.fromstring(svg_content)

    def process_element(parent: ET.Element) -> None:
        children = list(parent)
        for i, child in enumerate(children):
            barcode_key = child.attrib.get("data-barcode")
            qr_key = child.attrib.get("data-qr")

            if barcode_key:
                code_val = codes.get(barcode_key, "")
                if code_val:
                    x = float(child.attrib.get("x", 0))
                    y = float(child.attrib.get("y", 0))
                    w = float(child.attrib.get("width", 0))
                    h = float(child.attrib.get("height", 0))
                    elem_id = child.attrib.get("id")

                    barcode_group = create_barcode_svg_group(
                        code_value=code_val,
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        group_id=elem_id,
                    )
                    parent.remove(child)
                    parent.insert(i, barcode_group)
                    continue

            elif qr_key:
                payload = codes.get(qr_key, "")
                if payload:
                    x = float(child.attrib.get("x", 0))
                    y = float(child.attrib.get("y", 0))
                    w = float(child.attrib.get("width", 0))
                    h = float(child.attrib.get("height", 0))
                    elem_id = child.attrib.get("id")

                    qr_group = create_qr_svg_group(
                        payload=payload,
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        group_id=elem_id,
                    )
                    parent.remove(child)
                    parent.insert(i, qr_group)
                    continue

            process_element(child)

    process_element(root)
    xml_decl = '<?xml version="1.0" encoding="UTF-8"?>\n'
    return xml_decl + ET.tostring(root, encoding="utf-8").decode("utf-8")

