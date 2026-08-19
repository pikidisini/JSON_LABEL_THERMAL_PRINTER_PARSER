"""
Unit tests for Barcode (Code128-B) and QR Code generator and injector.
"""

from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from engine.barcode_generator import (
    generate_code128_pattern,
    generate_qr_matrix,
    create_barcode_svg_group,
    create_qr_svg_group,
    inject_barcodes_and_qr,
)
from engine.renderer import load_json_contract, load_svg_template, inject_data


class TestBarcodeGenerator(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).parent.parent
        self.sample_json_path = self.project_root / "data_samples" / "sample_roll.json"
        self.sample_template_path = self.project_root / "assets" / "templates" / "label_roll_80x200.svg"

    def test_generate_code128_pattern(self):
        pattern = generate_code128_pattern("0000909358")
        self.assertTrue(len(pattern) > 0)
        self.assertTrue(all(c in ("0", "1") for c in pattern))
        # Code128 always starts with 11 and ends with 11
        self.assertTrue(pattern.startswith("1"))
        self.assertTrue(pattern.endswith("11"))

    def test_generate_qr_matrix(self):
        payload = "MAT:SR01PFO3000810;BAT:0000909358"
        matrix = generate_qr_matrix(payload)
        self.assertTrue(len(matrix) >= 21)  # Version 1 QR code is 21x21
        self.assertEqual(len(matrix), len(matrix[0]))
        # QR finder pattern top-left must have black modules
        self.assertTrue(matrix[0][0])

    def test_create_barcode_svg_group(self):
        group = create_barcode_svg_group("TEST1234", x=10, y=20, width=50, height=15)
        rects = group.findall("rect")
        self.assertTrue(len(rects) > 0)
        first_rect = rects[0]
        self.assertEqual(first_rect.attrib["y"], "20.0000")
        self.assertEqual(first_rect.attrib["height"], "15.0000")
        self.assertEqual(first_rect.attrib["fill"], "#000000")

    def test_create_qr_svg_group(self):
        group = create_qr_svg_group("TEST_QR_PAYLOAD", x=5, y=5, width=20, height=20)
        rects = group.findall("rect")
        self.assertTrue(len(rects) > 0)

    def test_inject_barcodes_and_qr_full(self):
        contract_data = load_json_contract(self.sample_json_path)
        svg_template = load_svg_template(self.sample_template_path)
        injected_text = inject_data(svg_template, contract_data)

        complete_svg = inject_barcodes_and_qr(injected_text, contract_data)

        # Ensure placeholders <rect data-barcode=...> were replaced
        root = ET.fromstring(complete_svg)
        barcode_rects = root.findall(".//*[@data-barcode]")
        qr_rects = root.findall(".//*[@data-qr]")
        self.assertEqual(len(barcode_rects), 0)
        self.assertEqual(len(qr_rects), 0)

        # Ensure elements with IDs rect_batch_barcode and rect_roll_barcode now contain child rect bars
        # Note: In ET, elements with id might have namespace or be <g>
        batch_bg = None
        for elem in root.iter():
            if elem.attrib.get("id") == "rect_batch_barcode":
                batch_bg = elem
                break
        self.assertIsNotNone(batch_bg)
        self.assertTrue(len(list(batch_bg)) > 0)


if __name__ == "__main__":
    unittest.main()
