"""
Main Window for Label Preview & Inspector Desktop Application.
"""

from pathlib import Path
import shutil
from typing import Dict, Optional
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from gui.worker import RenderWorker
from gui.components import JSONInspectorWidget, RasterCanvasWidget, ControlPanelWidget, PrintSenderDialog


class MainWindow(tk.Tk):
    """Main Application Window with 3-panel layout: Inspector, Canvas, Controls & Logs."""

    def __init__(self):
        super().__init__()
        self.title("Factory Label Preview & Inspector (3-Layer Architecture)")
        self.geometry("1300x820")
        self.minsize(1024, 680)

        # Default sample paths
        self.app_root = Path(__file__).parent.parent
        self.default_sample_json = self.app_root / "data_samples" / "sample_roll.json"
        self.default_sample_svg = self.app_root / "assets" / "templates" / "label_roll_80x200.svg"
        self.temp_out_dir = self.app_root / "out"

        self.last_results: Dict[str, Path] = {}

        self._build_ui()
        self._set_defaults()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # 1. Top Control Panel
        self.ctrl_panel = ControlPanelWidget(
            self,
            on_render_clicked=self.execute_render,
            on_dry_run_clicked=self.execute_dry_run,
            on_print_clicked=self.open_print_dialog,
            on_export_clicked=self.export_files,
        )
        self.ctrl_panel.grid(row=0, column=0, sticky="ew", padx=6, pady=4)

        # 2. Main Content (Horizontal PanedWindow)
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.grid(row=1, column=0, sticky="nsew", padx=6, pady=2)

        # Left Panel: JSON Inspector
        self.json_inspector = JSONInspectorWidget(paned)
        paned.add(self.json_inspector, weight=1)

        # Middle Panel: Visual Raster Canvas
        self.raster_canvas = RasterCanvasWidget(paned)
        paned.add(self.raster_canvas, weight=3)

        # 3. Bottom Status & Log Bar
        status_bar = ttk.Frame(self)
        status_bar.grid(row=2, column=0, sticky="ew", padx=6, pady=4)
        status_bar.columnconfigure(1, weight=1)

        self.lbl_status = ttk.Label(
            status_bar,
            text="Ready. Select JSON and SVG template then click 'Render & Inspect'.",
            font=("Segoe UI", 9),
        )
        self.lbl_status.grid(row=0, column=0, sticky="w")

        self.progress_bar = ttk.Progressbar(status_bar, mode="indeterminate", length=160)
    def execute_render(self):
        json_path = Path(self.ctrl_panel.var_json_path.get())
        template_path = Path(self.ctrl_panel.var_template_path.get())
        target_format = self.ctrl_panel.var_format.get()

        if not json_path.is_file():
            messagebox.showerror("Error", f"JSON file does not exist: {json_path}")
            return
        if not template_path.is_file():
            messagebox.showerror("Error", f"SVG template file does not exist: {template_path}")
            return

        self._start_render_thread(json_path, template_path, target_format)

    def execute_dry_run(self):
        template_path = Path(self.ctrl_panel.var_template_path.get())
        if not template_path.is_file():
            messagebox.showerror("Error", f"SVG template does not exist: {template_path}")
            return
        if not self.default_sample_json.is_file():
            messagebox.showerror("Error", f"Default test JSON does not exist: {self.default_sample_json}")
            return

        self.ctrl_panel.var_json_path.set(str(self.default_sample_json.resolve()))
        self._start_render_thread(self.default_sample_json, template_path, "all")

    def _start_render_thread(self, json_path: Path, template_path: Path, fmt: str):
        self.progress_bar.start(10)
        self.set_status("Rendering label & generating 1-bit bitmap...")

        worker = RenderWorker(
            parent=self,
            json_path=json_path,
            template_path=template_path,
            out_dir=self.temp_out_dir,
            fmt=fmt,
            on_success=self._on_render_success,
            on_error=self._on_render_error,
        )
        worker.start()

    def _on_render_success(self, json_path: Path, results: Dict[str, Path]):
        self.progress_bar.stop()
        self.last_results = results

        try:
            self.json_inspector.load_json(json_path)
        except Exception as e:
            print(f"Warning: failed to load JSON into inspector: {e}")

        png_path = results.get("png")
        if png_path and png_path.is_file():
            self.raster_canvas.load_image(png_path)
        else:
            self.raster_canvas.show_error("❌ Failed to render preview image (preview.png not found)")

        fmt_list = ", ".join([f.upper() for f in results.keys()])
        self.set_status(f"[OK] Label rendered successfully! Generated: {fmt_list}")

    def _on_render_error(self, err_msg: str):
        self.progress_bar.stop()
        self.set_status(err_msg, is_error=True)
        messagebox.showerror("Rendering Failed", err_msg)

    def open_print_dialog(self):
        if not self.last_results:
            messagebox.showwarning(
                "No Rendered Output",
                "Please click 'Render & Inspect' first before sending RAW stream to printer.",
            )
            return

        PrintSenderDialog(self, self.last_results)

        self.progress_bar.grid(row=0, column=2, sticky="e", padx=4)

    def export_files(self):
        """Exports currently rendered output file(s) to a user-selected destination."""
        if not self.last_results:
            messagebox.showwarning(
                "No Rendered Output",
                "Please click 'Render & Inspect' first before exporting output files.",
            )
            return

        target_format = self.ctrl_panel.var_format.get().lower()

        # Format map for specific extensions
        format_filetypes = {
            "png": ("PNG Image", "*.png"),
            "bmp": ("1-Bit Monochrome Bitmap", "*.bmp"),
            "svg": ("SVG Scalable Vector", "*.svg"),
            "zpl": ("Zebra ZPL Command Stream", "*.zpl"),
            "tspl": ("TSC TSPL Binary Stream", "*.tspl"),
            "ipl": ("Intermec IPL Command Stream", "*.ipl"),
        }

        try:
            # Case 1: Specific format selected and available
            if target_format != "all" and target_format in self.last_results:
                src_path = self.last_results[target_format]
                if not src_path.is_file():
                    messagebox.showerror("Error", f"Source file does not exist: {src_path}")
                    return

                desc, ext_pattern = format_filetypes.get(
                    target_format, (f"{target_format.upper()} File", f"*.{target_format}")
                )
                ext = f".{target_format}"

                dest_path_str = filedialog.asksaveasfilename(
                    title=f"Save Export As ({target_format.upper()})",
                    initialfile=src_path.name,
                    defaultextension=ext,
                    filetypes=[(desc, ext_pattern), ("All Files", "*.*")],
                )
                if not dest_path_str:
                    return  # User cancelled

                dest_path = Path(dest_path_str)
                shutil.copy2(src_path, dest_path)
                self.set_status(f"[OK] File exported successfully to {dest_path}")
                messagebox.showinfo("Export Successful", f"Saved: {dest_path}")

            # Case 2: 'all' selected or all files export
            else:
                dest_dir_str = filedialog.askdirectory(
                    title="Select Folder to Export All Rendered Files",
                )
                if not dest_dir_str:
                    return  # User cancelled

                dest_dir = Path(dest_dir_str)
                exported_count = 0
                for fmt_name, src_path in self.last_results.items():
                    if src_path.is_file():
                        shutil.copy2(src_path, dest_dir / src_path.name)
                        exported_count += 1

                self.set_status(f"[OK] {exported_count} file(s) exported successfully to {dest_dir}")
                messagebox.showinfo(
                    "Export Successful",
                    f"Successfully exported {exported_count} file(s) to:\n{dest_dir}",
                )

        except OSError as e:
            err_msg = f"Failed to export file(s): {e}"
            self.set_status(err_msg, is_error=True)
            messagebox.showerror("Export Failed", err_msg)

    def _set_defaults(self):
        if self.default_sample_json.is_file():
            self.ctrl_panel.var_json_path.set(str(self.default_sample_json.resolve()))
        if self.default_sample_svg.is_file():
            self.ctrl_panel.var_template_path.set(str(self.default_sample_svg.resolve()))

    def set_status(self, text: str, is_error: bool = False):
        color = "#CC0000" if is_error else "#007700"
        self.lbl_status.config(text=text, foreground=color)
