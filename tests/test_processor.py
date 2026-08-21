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
        self.temp_out = self.project_root / "temp_test_artifacts" / "processor_tests"
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

    def test_format_pdf_generation_and_compression(self):
        """When format='pdf', verifies valid PDF file is generated and compressed (< 100 KB at 600 DPI)."""
        sub_out = self.temp_out / "pdf_test"
        sub_out.mkdir(parents=True, exist_ok=True)
        results = process_label(
            json_source=self.json_path,
            template_source=self.svg_path,
            out_dir=sub_out,
            formats="pdf",
            dpi=600.0,
        )
        self.assertIn("pdf", results)
        self.assertIn("png", results)
        self.assertTrue(results["pdf"].is_file())
        self.assertEqual(results["pdf"].name, "label.pdf")

        # Verify header is valid PDF
        with open(results["pdf"], "rb") as f:
            header = f.read(20)
            self.assertTrue(header.startswith(b"%PDF"))

        # Verify file size is significantly compressed (< 100 KB at 600 DPI)
        pdf_size_kb = results["pdf"].stat().st_size / 1024
        self.assertLess(pdf_size_kb, 100.0, f"PDF file size {pdf_size_kb:.2f} KB exceeds 100 KB limit")

    def test_format_all(self):
        """When format='all', all formats (svg, png, bmp, pdf, zpl, tspl, ipl) should be generated."""
        results = process_label(
            json_source=self.json_path,
            template_source=self.svg_path,
            out_dir=self.temp_out,
            formats="all",
        )
        for fmt in ["svg", "png", "bmp", "pdf", "zpl", "tspl", "ipl"]:
            self.assertIn(fmt, results)
            self.assertTrue(results[fmt].is_file(), f"Expected {fmt} file to exist")

    def test_dynamic_dpi_resolutions(self):
        """Verifies that preview.png dimensions scale up dynamically with selected DPI and 8-bit alignment."""
        from PIL import Image

        dpi_cases = [
            (203.2, 1600, 640),
            (300.0, 2368, 945),
            (600.0, 4728, 1890),
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
                # Width must be strictly divisible by 8 for printer byte alignment
                self.assertEqual(w % 8, 0, f"Width {w} at DPI {dpi} is not a multiple of 8")
                # Tolerances of +/- 2px due to integer rounding
                self.assertAlmostEqual(w, expected_w, delta=2)
                self.assertAlmostEqual(h, expected_h, delta=2)

    def test_600_dpi_all_formats_including_ipl(self):
        """Verifies that 600 DPI with formats='all' (including IPL & PDF) renders and encodes without byte-alignment error."""
        sub_out = self.temp_out / "dpi_600_all"
        sub_out.mkdir(parents=True, exist_ok=True)
        results = process_label(
            json_source=self.json_path,
            template_source=self.svg_path,
            out_dir=sub_out,
            formats="all",
            dpi=600.0,
        )
        for fmt in ["svg", "png", "bmp", "pdf", "zpl", "tspl", "ipl"]:
            self.assertIn(fmt, results)
            self.assertTrue(results[fmt].is_file(), f"Expected {fmt} file to exist for 600 DPI")
            self.assertTrue(results[fmt].stat().st_size > 0)

    def test_rotations_dimension_swapping(self):
        """Verifies that 90° and 270° rotations swap width and height while 0° and 180° keep original aspect ratio."""
        from PIL import Image

        rotation_cases = [
            (0, 1600, 640),
            (90, 640, 1600),
            (180, 1600, 640),
            (270, 640, 1600),
        ]
        for rot, exp_w, exp_h in rotation_cases:
            sub_out = self.temp_out / f"rot_{rot}"
            sub_out.mkdir(parents=True, exist_ok=True)
            results = process_label(
                json_source=self.json_path,
                template_source=self.svg_path,
                out_dir=sub_out,
                formats="png",
                dpi=203.2,
                rotation=rot,
            )
            with Image.open(results["png"]) as img:
                w, h = img.size
                self.assertEqual(w, exp_w)
                self.assertEqual(h, exp_h)

    def test_rotations_all_formats_including_encoders(self):
        """Verifies that all formats (PDF, ZPL, TSPL, IPL, BMP) encode cleanly under 90, 180, and 270 degrees."""
        for rot in [90, 180, 270]:
            sub_out = self.temp_out / f"rot_{rot}_all"
            sub_out.mkdir(parents=True, exist_ok=True)
            results = process_label(
                json_source=self.json_path,
                template_source=self.svg_path,
                out_dir=sub_out,
                formats="all",
                dpi=203.2,
                rotation=rot,
            )
            for fmt in ["svg", "png", "bmp", "pdf", "zpl", "tspl", "ipl"]:
                self.assertIn(fmt, results)
                self.assertTrue(results[fmt].is_file(), f"Expected {fmt} file to exist for rotation {rot}°")
                self.assertTrue(results[fmt].stat().st_size > 0)


if __name__ == "__main__":
    unittest.main()
