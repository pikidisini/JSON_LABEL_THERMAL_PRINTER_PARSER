"""
Unit tests for 1-bit rasterizer and bit-packer @ 203.2 DPI.
"""

from pathlib import Path
import unittest
from PIL import Image

from engine.renderer import load_json_contract, load_svg_template, inject_data
from engine.barcode_generator import inject_barcodes_and_qr
from engine.rasterizer import svg_to_png, png_to_1bit_monochrome, save_1bit_bmp, rotate_image_cw
from engine.bit_packer import pack_bits_per_row, get_raw_bitmap_data


class TestRasterizer(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).parent.parent
        self.sample_json_path = self.project_root / "data_samples" / "sample_roll.json"
        self.sample_template_path = self.project_root / "assets" / "templates" / "label_roll_80x200.svg"
        self.out_dir = self.project_root / "temp_test_artifacts" / "rasterizer_tests"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def test_rotate_image_cw_dimensions(self):
        """Tests clockwise rotation of PIL images across 0°, 90°, 180°, and 270°."""
        test_img = Image.new("RGB", (1600, 640), color="white")
        
        # 0°
        rot0 = rotate_image_cw(test_img, 0)
        self.assertEqual(rot0.size, (1600, 640))

        # 90° CW
        rot90 = rotate_image_cw(test_img, 90)
        self.assertEqual(rot90.size, (640, 1600))

        # 180° CW
        rot180 = rotate_image_cw(test_img, 180)
        self.assertEqual(rot180.size, (1600, 640))

        # 270° CW
        rot270 = rotate_image_cw(test_img, 270)
        self.assertEqual(rot270.size, (640, 1600))

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


    def test_super_sampling_and_otsu_threshold(self):
        """Tests super-sampling factor 2 and Otsu threshold calculation."""
        from engine.rasterizer import calculate_otsu_threshold

        contract_data = load_json_contract(self.sample_json_path)
        svg_template = load_svg_template(self.sample_template_path)
        injected_text = inject_data(svg_template, contract_data)
        complete_svg = inject_barcodes_and_qr(injected_text, contract_data)

        png_path = self.out_dir / "preview_supersampled.png"
        svg_to_png(
            svg_source=complete_svg,
            output_png_path=png_path,
            width_px=1600,
            height_px=640,
            dpi=203.2,
            super_sample_factor=2,
        )

        self.assertTrue(png_path.is_file())
        with Image.open(png_path) as img:
            self.assertEqual(img.size, (1600, 640))

        # Test Otsu threshold calculation
        otsu_val = calculate_otsu_threshold(png_path)
        self.assertGreaterEqual(otsu_val, 0)
        self.assertLessEqual(otsu_val, 255)

        # Test 1-bit monochrome with Otsu threshold
        img_1bit = png_to_1bit_monochrome(png_path, threshold=otsu_val)
        self.assertEqual(img_1bit.mode, "1")
        self.assertEqual(img_1bit.size, (1600, 640))

        # Check pure monochrome (only 0 and 255)
        extrema = img_1bit.getextrema()
        self.assertEqual(extrema, (0, 255))

    def test_downsampling_filter_options(self):
        """Tests that different downsampling filters (BOX, LANCZOS, NEAREST) render properly."""
        contract_data = load_json_contract(self.sample_json_path)
        svg_template = load_svg_template(self.sample_template_path)
        injected_text = inject_data(svg_template, contract_data)
        complete_svg = inject_barcodes_and_qr(injected_text, contract_data)

        for filter_name in ["BOX", "LANCZOS", "NEAREST"]:
            png_path = self.out_dir / f"preview_{filter_name}.png"
            svg_to_png(
                svg_source=complete_svg,
                output_png_path=png_path,
                width_px=1600,
                height_px=640,
                dpi=203.2,
                super_sample_factor=2,
                downsampling_filter=filter_name,
            )
            self.assertTrue(png_path.is_file())
            with Image.open(png_path) as img:
                self.assertEqual(img.size, (1600, 640))
            img_1bit = png_to_1bit_monochrome(png_path)
            self.assertEqual(img_1bit.mode, "1")
            self.assertEqual(img_1bit.getextrema(), (0, 255))


if __name__ == "__main__":
    unittest.main()
