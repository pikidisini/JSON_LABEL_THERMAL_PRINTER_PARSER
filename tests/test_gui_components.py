"""
Unit tests for GUI data structures and JSON inspector widget (headless execution).
"""

from pathlib import Path
import unittest
import tkinter as tk

from gui.components import JSONInspectorWidget, RasterCanvasWidget


class TestGUIComponents(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).parent.parent
        self.sample_json = self.project_root / "data_samples" / "sample_roll.json"
        self.sample_png = self.project_root / "out" / "preview.png"
        self.root = tk.Tk()
        self.root.withdraw()  # Headless mode without displaying window

    def tearDown(self):
        self.root.destroy()

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

if __name__ == "__main__":
    unittest.main()
