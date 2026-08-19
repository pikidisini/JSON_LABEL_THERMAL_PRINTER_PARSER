"""
Unit tests for 1-bit rasterizer and bit-packer @ 203.2 DPI.
"""

from pathlib import Path
import unittest
from PIL import Image

from engine.renderer import load_json_contract, load_svg_template, inject_data
from engine.barcode_generator import inject_barcodes_and_qr
from engine.rasterizer import svg_to_png, png_to_1bit_monochrome, save_1bit_bmp
from engine.bit_packer import pack_bits_per_row, get_raw_bitmap_data


class TestRasterizer(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).parent.parent
        self.sample_json_path = self.project_root / "data_samples" / "sample_roll.json"
        self.sample_template_path = self.project_root / "assets" / "templates" / "label_roll_80x200.svg"
        self.out_dir = self.project_root / "out_test_raster"
        self.out_dir.mkdir(exist_ok=True)

    def test_end_to_end_rasterization_dimensions(self):
        contract_data = load_json_contract(self.sample_json_path)
        svg_template = load_svg_template(self.sample_template_path)
        injected_text = inject_data(svg_template, contract_data)
        complete_svg = inject_barcodes_and_qr(injected_text, contract_data)

        png_path = self.out_dir / "preview.png"
        svg_to_png(
            svg_source=complete_svg,
            output_png_path=png_path,
            width_px=1600,
            height_px=640,
            dpi=203.2,
        )

        self.assertTrue(png_path.is_file())
        with Image.open(png_path) as img:
            self.assertEqual(img.size, (1600, 640))

        # Test 1-bit conversion
        img_1bit = png_to_1bit_monochrome(png_path)
        self.assertEqual(img_1bit.mode, "1")
        self.assertEqual(img_1bit.size, (1600, 640))

        bmp_path = self.out_dir / "test_1bit.bmp"
        save_1bit_bmp(img_1bit, bmp_path)
        self.assertTrue(bmp_path.is_file())

        # Test Bit Packing
        raw_bytes, w, h, bytes_per_row = get_raw_bitmap_data(img_1bit)
        self.assertEqual(w, 1600)
        self.assertEqual(h, 640)
        self.assertEqual(bytes_per_row, 200)  # 1600 / 8 = 200 bytes per row
        self.assertEqual(len(raw_bytes), 200 * 640)  # 128,000 bytes


if __name__ == "__main__":
    unittest.main()
