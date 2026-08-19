"""
Tests for processor pipeline and target format handling.
Ensures preview.png and label.svg are always generated and returned in results dictionary
regardless of whether the target format is 'svg', 'zpl', 'ipl', 'tspl', 'bmp', or 'all'.
"""

import os
from pathlib import Path
import unittest

from engine.processor import process_label


class TestProcessorFormats(unittest.TestCase):
    """Test suite for verifying processor output generation across different target formats."""

    def setUp(self):
        self.project_root = Path(__file__).parent.parent
        self.json_path = self.project_root / "data_samples" / "sample_roll.json"
        self.svg_path = self.project_root / "assets" / "templates" / "label_roll_80x200.svg"
        self.temp_out = self.project_root / "out_test_processor"
        self.temp_out.mkdir(parents=True, exist_ok=True)

    def test_format_svg_includes_preview_png(self):
        """When format='svg', results must still include 'png' (preview.png) for UI display."""
        results = process_label(
            json_source=self.json_path,
            template_source=self.svg_path,
            out_dir=self.temp_out,
            formats="svg",
        )
        self.assertIn("svg", results)
        self.assertIn("png", results)
        self.assertTrue(results["png"].is_file())
        self.assertTrue(results["svg"].is_file())
        self.assertEqual(results["png"].name, "preview.png")

    def test_format_zpl_includes_preview_png(self):
        """When format='zpl', results must still include 'png' (preview.png) for UI display."""
        results = process_label(
            json_source=self.json_path,
            template_source=self.svg_path,
            out_dir=self.temp_out,
            formats="zpl",
        )
        self.assertIn("zpl", results)
        self.assertIn("png", results)
        self.assertTrue(results["png"].is_file())
        self.assertTrue(results["zpl"].is_file())

    def test_format_all(self):
        """When format='all', all formats (svg, png, bmp, zpl, tspl, ipl) should be generated."""
        results = process_label(
            json_source=self.json_path,
            template_source=self.svg_path,
            out_dir=self.temp_out,
            formats="all",
        )
        for fmt in ["svg", "png", "bmp", "zpl", "tspl", "ipl"]:
            self.assertIn(fmt, results)
            self.assertTrue(results[fmt].is_file(), f"Expected {fmt} file to exist")

    def test_dynamic_dpi_resolutions(self):
        """Verifies that preview.png dimensions scale up dynamically with selected DPI."""
        from PIL import Image

        dpi_cases = [
            (203.2, 1600, 640),
            (300.0, 2362, 945),
            (600.0, 4724, 1890),
        ]
        for dpi, expected_w, expected_h in dpi_cases:
            sub_out = self.temp_out / f"dpi_{int(dpi)}"
            sub_out.mkdir(parents=True, exist_ok=True)
            results = process_label(
                json_source=self.json_path,
                template_source=self.svg_path,
                out_dir=sub_out,
                formats="png",
                dpi=dpi,
            )
            with Image.open(results["png"]) as img:
                w, h = img.size
                # Tolerances of +/- 2px due to integer rounding
                self.assertAlmostEqual(w, expected_w, delta=2)
                self.assertAlmostEqual(h, expected_h, delta=2)


if __name__ == "__main__":
    unittest.main()
