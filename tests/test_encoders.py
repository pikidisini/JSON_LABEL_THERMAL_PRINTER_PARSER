"""
Unit tests for Native Printer Encoders (ZPL, TSPL, IPL).
"""

from pathlib import Path
import unittest

from engine.printer_encoders import encode_zpl, encode_tspl, encode_ipl
from engine.processor import process_label


class TestPrinterEncoders(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).parent.parent
        self.sample_json_path = self.project_root / "data_samples" / "sample_roll.json"
        self.sample_template_path = self.project_root / "assets" / "templates" / "label_roll_80x200.svg"
        self.out_dir = self.project_root / "out_test_encoders"
        self.out_dir.mkdir(exist_ok=True)

    def test_zpl_encoder_format(self):
        # 16 pixels width (2 bytes/row), 2 pixels height = 4 bytes total
        dummy_bytes = b"\xFF\x00\xAA\x55"
        zpl = encode_zpl(dummy_bytes, width_px=16, height_px=2)
        self.assertTrue(zpl.startswith("^XA\n"))
        self.assertTrue(zpl.endswith("^XZ\n"))
        self.assertIn("^FO0,0^GFA,4,4,2,FF00AA55^FS", zpl)

    def test_tspl_encoder_format(self):
        dummy_bytes = b"\xFF\x00"
        tspl = encode_tspl(dummy_bytes, width_px=16, height_px=1, width_mm=200.0, height_mm=80.0)
        self.assertTrue(tspl.startswith(b"SIZE 200.0 mm,80.0 mm\r\n"))
        self.assertIn(b"BITMAP 0,0,2,1,0,", tspl)
        self.assertTrue(tspl.endswith(b"\r\nPRINT 1,1\r\n"))

    def test_ipl_encoder_format(self):
        # 16 pixels width (2 bytes/row), 1 pixel height = 2 bytes total
        dummy_bytes = b"\xAB\xCD"
        # 1 copy test
        ipl = encode_ipl(dummy_bytes, width_px=16, height_px=1)
        self.assertIsInstance(ipl, bytes)

        # 1. Pastikan TIDAK ADA \r\n atau \n di dalam byte stream (pure continuous bytes)
        self.assertNotIn(b"\r\n", ipl)
        self.assertNotIn(b"\n", ipl)

        # 2. Reset, Layout, & Define sequence: <STX>C<ETX><STX>L<ETX><STX>D<ETX>
        self.assertIn(b"\x02C\x03\x02L\x03\x02D\x03", ipl)

        # 3. Graphic Field definition dengan d0002
        self.assertIn(b"\x02G1;o0,0;w16;h1;d0002;\x03", ipl)

        # 4. Bitmap upload dalam SATU frame utuh (tanpa prefix 0002 pada data)
        self.assertIn(b"\x02uABCD\x03", ipl)

        # 5. Trailer urutan akhir: Return from Define (<STX>R<ETX>) + Select/Execute Print (<STX>E1;F1;<ETX>)
        expected_trailer = b"\x02R\x03\x02E1;F1;\x03"
        self.assertTrue(ipl.endswith(expected_trailer))

        # Multi-copies test (misal 3 copies -> 3x <STX>E1;F1;<ETX>)
        ipl_multi = encode_ipl(dummy_bytes, width_px=16, height_px=1, copies=3)
        expected_multi_trailer = b"\x02R\x03\x02E1;F1;\x03\x02E1;F1;\x03\x02E1;F1;\x03"
        self.assertTrue(ipl_multi.endswith(expected_multi_trailer))

    def test_ipl_encoder_validation_guards(self):
        dummy_bytes = b"\xAB\xCD"
        # Width not divisible by 8 must raise ValueError
        with self.assertRaises(ValueError):
            encode_ipl(dummy_bytes, width_px=15, height_px=1)

        # Byte size mismatch must raise ValueError
        with self.assertRaises(ValueError):
            encode_ipl(dummy_bytes, width_px=16, height_px=2)  # expects 4 bytes, got 2

    def test_full_pipeline_process_label(self):
        results = process_label(
            json_source=self.sample_json_path,
            template_source=self.sample_template_path,
            out_dir=self.out_dir,
            formats="all",
            dpi=203.2,
        )

        expected_keys = ["svg", "png", "bmp", "zpl", "tspl", "ipl"]
        for key in expected_keys:
            self.assertIn(key, results)
            self.assertTrue(results[key].is_file())
            self.assertTrue(results[key].stat().st_size > 0)


if __name__ == "__main__":
    unittest.main()
