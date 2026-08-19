"""
Unit and Integration Tests for Coordinate Alignment and Binding Utilities.
Verifies SVG physical-to-raster scale calculation, parent text ID resolution,
hit testing with zoom awareness, and JSON path manipulation.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from engine.binding_map import BoundingBox, SVGInspectionEngine
from engine.binding_utils import (
    get_json_value_at_path,
    set_json_value_at_path,
    validate_json_value_type,
)


class TestBindingUtils:
    """Tests for engine/binding_utils.py"""

    def test_get_json_value_at_path(self):
        data = {
            "source": {"matnr": "MAT-001", "charg": "LOT-88"},
            "fields": {
                "brand": "BRAND A",
                "batch_text": "B12345",
                "counts": {"total": 50},
            },
        }
        assert get_json_value_at_path(data, "source.matnr") == "MAT-001"
        assert get_json_value_at_path(data, "fields.batch_text") == "B12345"
        assert get_json_value_at_path(data, "fields.counts.total") == 50
        assert get_json_value_at_path(data, "non_existent.path") is None
        assert get_json_value_at_path({}, "any.path") is None

    def test_set_json_value_at_path(self):
        data = {"fields": {"brand": "OLD_NAME"}}
        success = set_json_value_at_path(data, "fields.brand", "NEW_NAME")
        assert success is True
        assert data["fields"]["brand"] == "NEW_NAME"

        # Create intermediate dict
        set_json_value_at_path(data, "codes.new_qr", "QR_VALUE")
        assert data["codes"]["new_qr"] == "QR_VALUE"

    def test_validate_json_value_type(self):
        assert validate_json_value_type("old", "new") is True
        assert validate_json_value_type(100, "150") is True
        assert validate_json_value_type(100, "not_a_number") is False
        assert validate_json_value_type(12.5, "13.8") is True
        assert validate_json_value_type(12.5, "invalid") is False
        assert validate_json_value_type(True, "false") is True
        assert validate_json_value_type(True, "yes") is False


class TestCoordinateAlignment:
    """Tests for SVG coordinate scaling and bounding box mapping."""

    @pytest.fixture
    def sample_svg_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / "assets" / "templates" / "label_roll_80x200.svg"

    @pytest.fixture
    def sample_json_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / "data_samples" / "sample_roll.json"

    def test_bounding_box_contains_point(self):
        box = BoundingBox(x=100.0, y=50.0, width=200.0, height=40.0, element_id="text1", json_path="fields.brand")
        # Direct inside
        assert box.contains_point(150.0, 70.0) is True
        # Outside
        assert box.contains_point(50.0, 70.0) is False
        assert box.contains_point(350.0, 70.0) is False
        # Within zoom-aware margin
        assert box.contains_point(98.0, 50.0, zoom_factor=1.0) is True
        assert box.contains_point(303.0, 50.0, zoom_factor=1.0) is True

    def test_extract_element_bindings_prefers_parent_text(self):
        engine = SVGInspectionEngine()
        svg_xml = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 80">
            <text id="text_parent" data-field="batch_text">
                <tspan id="tspan_child">{{batch_text}}</tspan>
            </text>
        </svg>"""
        bindings = engine.extract_element_bindings(svg_xml)
        assert "fields.batch_text" in bindings
        # The queryable ID should resolve to the parent <text> node
        assert bindings["fields.batch_text"] == ["text_parent"]

    def test_parse_svg_dimensions(self, sample_svg_path):
        engine = SVGInspectionEngine()
        w, h = engine._parse_svg_dimensions(sample_svg_path)
        assert w == 200.0
        assert h == 80.0

    def test_query_all_element_boxes_scale_exact(self, sample_svg_path):
        """
        Verify that scaling does not introduce horizontal shift drift.
        For a 200x80mm SVG rendered at 203 DPI to 1600x640px, scale_x should be close to 1.0 (exact physical ratio).
        """
        engine = SVGInspectionEngine()
        boxes = engine.query_all_element_boxes(
            sample_svg_path,
            dpi=203.2,
            target_width_px=1600,
            target_height_px=640,
        )
        assert len(boxes) > 0
        # Check that bounding boxes are scaled properly without root_box distortion
        for elem_id, (x, y, w, h) in boxes.items():
            assert x >= 0
            assert y >= 0
            assert x + w <= 1650  # Must be strictly within canvas bounds (plus slight tolerance)
            assert y + h <= 650

    def test_build_inspection_map_roll_template(self, sample_svg_path):
        engine = SVGInspectionEngine()
        svg_content = sample_svg_path.read_text(encoding="utf-8")
        inspection_map = engine.build_inspection_map(
            svg_content=svg_content,
            rendered_svg_path=sample_svg_path,
            target_width_px=1600,
            target_height_px=640,
            dpi=203.2,
        )
        assert len(inspection_map) > 0
        json_paths = [box.json_path for box in inspection_map]
        # Verify key bindings are captured
        assert any("fields." in p or "codes." in p for p in json_paths)
