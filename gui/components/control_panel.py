"""
Control Panel Component.
Contains selectors for JSON, Template SVG, output format, actions (Render, Dry-Run, Send to Printer, Export).
"""

from pathlib import Path
from typing import Callable, Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class _ToolTip:
    """Lightweight tooltip helper: shows a small borderless popup on widget hover."""

    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self._tip_window: Optional[tk.Toplevel] = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None):
        if self._tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self._tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#FFFFE0",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 8, "normal"),
            padx=6,
            pady=3,
        )
        label.pack()

    def _hide(self, _event=None):
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None


class ControlPanelWidget(ttk.Frame):
    """Action bar & control panel for label inspection operations."""

    def __init__(
        self,
        parent: tk.Widget,
        on_render_clicked: Optional[Callable[[], None]] = None,
        on_dry_run_clicked: Optional[Callable[[], None]] = None,
        on_print_clicked: Optional[Callable[[], None]] = None,
        on_export_clicked: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.on_render_clicked = on_render_clicked
        self.on_dry_run_clicked = on_dry_run_clicked
        self.on_print_clicked = on_print_clicked
        self.on_export_clicked = on_export_clicked

        self.var_json_path = tk.StringVar()
        self.var_template_path = tk.StringVar()
        self.var_format = tk.StringVar(value="all")

        self._build_ui()

    def _build_ui(self):
        # Frame 1: File Pickers
        files_frame = ttk.LabelFrame(self, text="Source Inputs", padding=6)
        files_frame.pack(side="left", fill="both", expand=True, padx=4, pady=2)

        # JSON Selector
        ttk.Label(files_frame, text="SAP JSON File:").grid(row=0, column=0, sticky="w", padx=2, pady=2)
        ttk.Entry(files_frame, textvariable=self.var_json_path, width=36).grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        ttk.Button(files_frame, text="Browse...", width=10, command=self._browse_json).grid(row=0, column=2, padx=2, pady=2)

        # SVG Selector
        ttk.Label(files_frame, text="SVG Template:").grid(row=1, column=0, sticky="w", padx=2, pady=2)
        ttk.Entry(files_frame, textvariable=self.var_template_path, width=36).grid(row=1, column=1, sticky="ew", padx=2, pady=2)
        ttk.Button(files_frame, text="Browse...", width=10, command=self._browse_svg).grid(row=1, column=2, padx=2, pady=2)

        files_frame.columnconfigure(1, weight=1)

        # Frame 2: Options & Format
        opts_frame = ttk.LabelFrame(self, text="Target Format", padding=6)
        opts_frame.pack(side="left", fill="y", padx=4, pady=2)

        ttk.Label(opts_frame, text="Format:").pack(side="top", anchor="w")
        cb_format = ttk.Combobox(
            opts_frame,
            textvariable=self.var_format,
            values=["all", "zpl", "tspl", "ipl", "png", "bmp"],
            state="readonly",
            width=12,
        )
        cb_format.pack(side="top", pady=2, fill="x")

        # Frame 3: Action Buttons
        actions_frame = ttk.LabelFrame(self, text="Engine Actions", padding=6)
        actions_frame.pack(side="left", fill="y", padx=4, pady=2)

        # "Render & Inspect" -> Primary action button (Blue accent)
        btn_render = tk.Button(
            actions_frame,
            text=" Render & Inspect ",
            command=self._handle_render,
            bg="#0078D4",
            fg="white",
            activebackground="#005A9E",
            activeforeground="white",
            disabledforeground="#CCCCCC",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
        )
        btn_render.pack(side="left", padx=4, pady=2)

        # "Template Dry-Run" -> Neutral (default ttk style)
        btn_dry_run = ttk.Button(
            actions_frame,
            text=" Template Dry-Run ",
            command=self._handle_dry_run,
        )
        btn_dry_run.pack(side="left", padx=4, pady=2)

        # "Send RAW to Printer" -> Print/accent action button (Dark green)
        btn_print = tk.Button(
            actions_frame,
            text=" Send RAW to Printer ",
            command=self._handle_print,
            bg="#107C10",
            fg="white",
            activebackground="#0B5A0B",
            activeforeground="white",
            disabledforeground="#CCCCCC",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
        )
        btn_print.pack(side="left", padx=4, pady=2)

        # "Save Export As..." -> Neutral blue accent action button
        btn_export = tk.Button(
            actions_frame,
            text=" Save Export As... ",
            command=self._handle_export,
            bg="#008CBA",
            fg="white",
            activebackground="#00688F",
            activeforeground="white",
            disabledforeground="#CCCCCC",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
        )
        btn_export.pack(side="left", padx=4, pady=2)
        _ToolTip(btn_export, "Simpan file hasil render (SVG/PNG/BMP/ZPL/TSPL/IPL) ke folder tujuan")

    def _browse_json(self):
        filename = filedialog.askopenfilename(
            title="Select SAP JSON Contract File",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if filename:
            self.var_json_path.set(filename)

    def _browse_svg(self):
        filename = filedialog.askopenfilename(
            title="Select Label SVG Template",
            filetypes=[("SVG Files", "*.svg"), ("All Files", "*.*")],
        )
        if filename:
            self.var_template_path.set(filename)

    def _handle_render(self):
        if not self.var_json_path.get() or not self.var_template_path.get():
            messagebox.showwarning(
                "Missing Input",
                "Please select both a SAP JSON file and an SVG Template file.",
            )
            return
        if self.on_render_clicked:
            self.on_render_clicked()

    def _handle_dry_run(self):
        if not self.var_template_path.get():
            messagebox.showwarning(
                "Missing Template",
                "Please select an SVG Template file for Dry-Run testing.",
            )
            return
        if self.on_dry_run_clicked:
            self.on_dry_run_clicked()

    def _handle_print(self):
        if self.on_print_clicked:
            self.on_print_clicked()

    def _handle_export(self):
        if self.on_export_clicked:
            self.on_export_clicked()
