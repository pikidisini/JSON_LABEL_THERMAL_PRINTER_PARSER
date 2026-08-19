"""
SVG Data Binding & Bounding Box Extractor.
Extracts data-field/data-code/placeholder mappings from SVG templates and queries
exact vector element bounding boxes using resvg CLI query-all.
"""

from __future__ import annotations

import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from engine.rasterizer import get_resvg_executable_path


@dataclass
class BoundingBox:
    """Bounding box coordinates in image pixel space."""
    x: float
    y: float
    width: float
    height: float
    element_id: str
    json_path: str

    @property
    def x2(self) -> float:
        return self.x + self.width

    @property
    def y2(self) -> float:
        return self.y + self.height

    def contains_point(self, px: float, py: float) -> bool:
        """Checks if a point in pixel space falls inside this bounding box (with slight hit margin)."""
        margin = 3.0
        return (self.x - margin <= px <= self.x2 + margin) and (self.y - margin <= py <= self.y2 + margin)


class SVGInspectionEngine:
    """
    Parses SVG structure to map JSON contract paths (e.g., 'fields.brand', 'codes.batch_barcode')
    to SVG element IDs, queries element bounding boxes via resvg CLI, and scales them
    to match the output preview image coordinates.
    """

    PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_\-]+)\s*\}\}")

    def __init__(self, resvg_path: Optional[Union[str, Path]] = None):
        self.resvg_exe = Path(resvg_path) if resvg_path else get_resvg_executable_path()

    def extract_element_bindings(self, svg_content: str) -> Dict[str, List[str]]:
        """
        Parses SVG XML and returns a mapping from JSON path to list of target SVG element IDs.
        Handles data-json-key, data-field, data-code, data-barcode, data-qr, and {{token}} placeholders.
        """
        bindings: Dict[str, List[str]] = {}

        def add_binding(json_path: str, elem_id: str):
            if not json_path or not elem_id:
                return
            if json_path not in bindings:
                bindings[json_path] = []
            if elem_id not in bindings[json_path]:
                bindings[json_path].append(elem_id)

        try:
            root = ET.fromstring(svg_content)
        except Exception:
            return bindings

        ns = "{http://www.w3.org/2000/svg}"
        parent_map = {c: p for p in root.iter() for c in p}

        for elem in root.iter():
            elem_id = elem.get("id")

            # explicit full json key / bind
            data_json_key = elem.get("data-json-key") or elem.get("data-bind")
            if data_json_key:
                target_id = self._find_queryable_id(elem, parent_map, ns)
                if target_id:
                    add_binding(data_json_key, target_id)

            # data-field attribute
            data_field = elem.get("data-field")
            if data_field:
                target_id = self._find_queryable_id(elem, parent_map, ns)
                if target_id:
                    add_binding(f"fields.{data_field}", target_id)

            # data-code attribute
            data_code = elem.get("data-code")
            if data_code:
                target_id = self._find_queryable_id(elem, parent_map, ns)
                if target_id:
                    add_binding(f"codes.{data_code}", target_id)

            # data-barcode attribute
            data_bc = elem.get("data-barcode")
            if data_bc:
                target_id = self._find_queryable_id(elem, parent_map, ns)
                if target_id:
                    add_binding(f"codes.{data_bc}", target_id)

            # data-qr attribute
            data_qr = elem.get("data-qr")
            if data_qr:
                target_id = self._find_queryable_id(elem, parent_map, ns)
                if target_id:
                    add_binding(f"codes.{data_qr}", target_id)

            # Inspect element text & tspans for {{token}}
            text_val = (elem.text or "") + "".join(child.tail or "" for child in elem)
            matches = self.PLACEHOLDER_PATTERN.findall(text_val)
            for token in matches:
                target_id = self._find_queryable_id(elem, parent_map, ns)
                if target_id:
                    add_binding(f"fields.{token}", target_id)
                    add_binding(f"codes.{token}", target_id)
        return bindings

    def _find_queryable_id(
        self,
        elem: ET.Element,
        parent_map: Dict[ET.Element, ET.Element],
        ns: str
    ) -> Optional[str]:
        curr: Optional[ET.Element] = elem
        while curr is not None:
            elem_id = curr.get("id")
            tag_name = curr.tag.replace(ns, "")
            if elem_id and tag_name != "tspan":
                return elem_id
            curr = parent_map.get(curr)
        return None



    def query_all_element_boxes(
        self,
        svg_file_path: Union[str, Path],
        dpi: float = 203.2,
        target_width_px: int = 1600,
        target_height_px: int = 640,
    ) -> Dict[str, Tuple[float, float, float, float]]:
        """
        Runs resvg --dpi <dpi> --query-all to extract raw element bounding boxes,
        then scales them to match the exact target raster width/height.
        Returns: { element_id: (x, y, width, height) in px }
        """
        svg_path = Path(svg_file_path)
        if not svg_path.is_file():
            return {}

        cmd = [
            str(self.resvg_exe),
            "--dpi", str(int(round(dpi))),
            "--query-all",
            str(svg_path.resolve()),
        ]

        kwargs = {
            "capture_output": True,
            "text": True,
            "check": False,
            "stdin": subprocess.DEVNULL,
            "timeout": 15.0,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        try:
            res = subprocess.run(cmd, **kwargs)
            if res.returncode != 0:
                return {}
        except Exception:
            return {}

        boxes: Dict[str, Tuple[float, float, float, float]] = {}
        for line in res.stdout.strip().splitlines():
            parts = line.strip().split(",")
            if len(parts) >= 5:
                elem_id = parts[0].strip()
                try:
                    x = float(parts[1])
                    y = float(parts[2])
                    w = float(parts[3])
                    h = float(parts[4])
                    boxes[elem_id] = (x, y, w, h)
                except ValueError:
                    continue

        root_box = boxes.get("svg1") or boxes.get("root") or boxes.get("layer1")
        if root_box and root_box[2] > 0 and root_box[3] > 0:
            scale_x = target_width_px / (root_box[0] * 2 + root_box[2]) if root_box[0] > 0 else target_width_px / root_box[2]
            scale_y = target_height_px / (root_box[1] * 2 + root_box[3]) if root_box[1] > 0 else target_height_px / root_box[3]
        else:
            base_w = (200.0 / 25.4) * dpi
            base_h = (80.0 / 25.4) * dpi
            scale_x = target_width_px / base_w if base_w > 0 else 1.0
            scale_y = target_height_px / base_h if base_h > 0 else 1.0

        scaled_boxes: Dict[str, Tuple[float, float, float, float]] = {}
        for elem_id, (x, y, w, h) in boxes.items():
            scaled_boxes[elem_id] = (
                round(x * scale_x, 2),
                round(y * scale_y, 2),
                round(w * scale_x, 2),
                round(h * scale_y, 2),
            )

        return scaled_boxes

    def build_inspection_map(
        self,
        svg_content: str,
        rendered_svg_path: Union[str, Path],
        target_width_px: int = 1600,
        target_height_px: int = 640,
        dpi: float = 203.2,
    ) -> List[BoundingBox]:
        """
        Builds a complete list of BoundingBox objects mapping JSON paths to pixel coordinates.
        """
        key_to_elem_ids = self.extract_element_bindings(svg_content)
        elem_boxes = self.query_all_element_boxes(
            rendered_svg_path,
            dpi=dpi,
            target_width_px=target_width_px,
            target_height_px=target_height_px,
        )

        all_boxes: List[BoundingBox] = []
        for json_path, elem_ids in key_to_elem_ids.items():
            for elem_id in elem_ids:
                if elem_id in elem_boxes:
                    bx, by, bw, bh = elem_boxes[elem_id]
                    if bw >= target_width_px * 0.95 and bh >= target_height_px * 0.95:
                        continue
                    all_boxes.append(
                        BoundingBox(
                            x=bx,
                            y=by,
                            width=bw,
                            height=bh,
                            element_id=elem_id,
                            json_path=json_path,
                        )
                    )

        return all_boxes
        margin = 3.0
        return (self.x - margin <= px <= self.x2 + margin) and (self.y - margin <= py <= self.y2 + margin)
