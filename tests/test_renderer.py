"""
Unit tests for Pure Data Injection Renderer.
Supports execution via pytest (if installed) or standard python -m unittest.
"""

from pathlib import Path
import unittest

from engine.renderer import (
    render_svg,
    load_json_contract,
    inject_data,
    validate_no_orphan_tokens,
    OrphanTokenError,
    MissingContractFieldError,
)


class TestRenderer(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).parent.parent
        self.sample_json_path = self.project_root / "data_samples" / "sample_roll.json"
        self.sample_template_path = self.project_root / "assets" / "templates" / "label_roll_80x200.svg"

    def test_load_valid_contract(self):
        data = load_json_contract(self.sample_json_path)
        self.assertEqual(data["contract_version"], "1.1")
        self.assertEqual(data["fields"]["brand"], "ASTRIA")
        self.assertEqual(data["codes"]["batch_barcode"], "0000909358")

    def test_load_invalid_contract_missing_fields(self):
        invalid_data = {"contract_version": "1.1", "codes": {}}
        with self.assertRaises(MissingContractFieldError):
            load_json_contract(invalid_data)

    def test_load_invalid_contract_missing_codes(self):
        invalid_data = {"contract_version": "1.1", "fields": {}}
        with self.assertRaises(MissingContractFieldError):
            load_json_contract(invalid_data)

    def test_render_sample_roll_success(self):
        out_dir = self.project_root / "temp_test_artifacts" / "renderer_tests"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "out_test_output.svg"
        result = render_svg(self.sample_json_path, self.sample_template_path, out_file)

        self.assertTrue(out_file.is_file())
        self.assertIn("ASTRIA", result)
        self.assertIn("BOPET", result)
        self.assertIn("PFO-30", result)
        self.assertIn("0000909358", result)
        self.assertIn("1 AGB 063 058 9F 01 05", result)
        self.assertIn("466,56", result)
        self.assertNotIn("{{", result)
        self.assertNotIn("}}", result)

    def test_fail_fast_orphan_tokens(self):
        template_with_unknown_token = "<svg><text>{{unknown_field}}</text><text>{{brand}}</text></svg>"
        data = {
            "fields": {"brand": "ASTRIA"},
            "codes": {},
        }
        injected = inject_data(template_with_unknown_token, data)
        with self.assertRaises(OrphanTokenError) as ctx:
            validate_no_orphan_tokens(injected)
        self.assertIn("unknown_field", ctx.exception.orphan_tokens)

    def test_xml_escaping(self):
        template = "<svg><text>{{notes}}</text></svg>"
        data = {
            "fields": {"notes": "Length < 100 & Width > 50"},
            "codes": {},
        }
        rendered = inject_data(template, data)
        self.assertIn("Length &lt; 100 &amp; Width &gt; 50", rendered)


if __name__ == "__main__":
    unittest.main()

