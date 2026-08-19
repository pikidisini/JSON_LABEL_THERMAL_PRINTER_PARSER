"""
Unit tests for GUI data structures and JSON inspector widget (headless execution).
"""

from pathlib import Path
import unittest
import tkinter as tk

from gui.components import JSONInspectorWidget, RasterCanvasWidget


class TestGUIComponents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).parent.parent
        cls.sample_json = cls.project_root / "data_samples" / "sample_roll.json"
        cls.sample_png = cls.project_root / "out" / "preview.png"
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()  # Headless mode without displaying window
        except Exception:
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        if cls.root is not None:
            try:
                cls.root.destroy()
            except Exception:
                pass

    def setUp(self):
        if self.root is None:
            self.skipTest("Tkinter is not available or graphical display failed to initialize")

    def test_json_inspector_population(self):
        inspector = JSONInspectorWidget(self.root)
        inspector.load_json(self.sample_json)

        children = inspector.tree.get_children()
        self.assertTrue(len(children) > 0)
        # Check that 'fields' or 'codes' nodes exist
        item_texts = [inspector.tree.item(c, "text") for c in children]
        self.assertIn("contract_version", item_texts)
        self.assertIn("codes", item_texts)
        self.assertIn("fields", item_texts)


    def test_raster_canvas_load_image(self):
        if self.sample_png.is_file():
            canvas_widget = RasterCanvasWidget(self.root)
            canvas_widget.load_image(self.sample_png)
            self.assertIsNotNone(canvas_widget._pil_image)
            self.assertEqual(canvas_widget._pil_image.size, (1600, 640))


    def test_json_inspector_search_filter(self):
        inspector = JSONInspectorWidget(self.root)
        inspector.load_json(self.sample_json)

        # Filter for a specific field e.g. "MATNR"
        inspector.var_search.set("MATNR")
        children = inspector.tree.get_children()
        self.assertTrue(len(children) > 0)

        # Filter for non-existent text
        inspector.var_search.set("NON_EXISTENT_KEY_12345")
        children = inspector.tree.get_children()
        self.assertEqual(len(children), 0)

        # Reset search filter
        inspector.var_search.set("")
        children = inspector.tree.get_children()
        self.assertTrue(len(children) > 0)

    def test_raster_canvas_show_error(self):
        """Tests that RasterCanvasWidget displays visual error messages gracefully."""
        canvas_widget = RasterCanvasWidget(self.root)
        canvas_widget.pack()
        self.root.update()

        canvas_widget.show_error("❌ Test Error Message")
        self.root.update()

        self.assertIsNone(canvas_widget._pil_image)
        self.assertIsNone(canvas_widget._tk_image)
        self.assertEqual(canvas_widget.lbl_zoom.cget("text"), "--")
        items = canvas_widget.canvas.find_all()
        self.assertTrue(len(items) >= 1)

    def test_binding_map_and_interactive_selection(self):
        """Tests SVGInspectionEngine building boxes and JSONInspector two-way selection."""
        from engine.binding_map import SVGInspectionEngine, BoundingBox

        engine = SVGInspectionEngine()
        template_svg = self.project_root / "assets" / "templates" / "label_roll_80x200.svg"
        rendered_svg = self.project_root / "out" / "label.svg"

        if template_svg.is_file() and rendered_svg.is_file():
            boxes = engine.build_inspection_map(
                template_svg.read_text(encoding="utf-8"),
                rendered_svg,
            )
            self.assertTrue(len(boxes) > 0)
            paths = [b.json_path for b in boxes]
            self.assertIn("fields.brand", paths)

        inspector = JSONInspectorWidget(self.root)
        inspector.load_json(self.sample_json)

        # Test selecting a path programmatically
        matched = inspector.select_path("fields.brand")
        self.assertTrue(matched)
        selected = inspector.tree.selection()
        self.assertTrue(len(selected) > 0)

        # Test inline dict update
        inspector._update_raw_data_at_path("fields.brand", "NEW_TEST_BRAND")
        data = inspector.get_data()
        self.assertEqual(data["fields"]["brand"], "NEW_TEST_BRAND")

        # Test RasterCanvas bounding box setup and highlight
        canvas = RasterCanvasWidget(self.root)
        canvas.set_bounding_boxes([BoundingBox(x=10, y=10, width=50, height=20, element_id="t1", json_path="fields.brand")])
        canvas.highlight_path("fields.brand")
        self.assertEqual(canvas._highlighted_path, "fields.brand")
        box = canvas._find_box_at(20, 20)
        self.assertIsNotNone(box)
        self.assertEqual(box.json_path, "fields.brand")


if __name__ == "__main__":
    unittest.main()
