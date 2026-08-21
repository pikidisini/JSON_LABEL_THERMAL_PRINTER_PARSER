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

    DPI_PRESETS = [
        "203.2 DPI (8 dpmm)",
        "300 DPI (12 dpmm)",
        "600 DPI (24 dpmm)",
    ]

    ROTATION_PRESETS = [
        "0°",
        "90°",
        "180°",
        "270°",
    ]

    def __init__(
        self,
        parent: tk.Widget,
        on_render_clicked: Optional[Callable[[], None]] = None,
        on_dry_run_clicked: Optional[Callable[[], None]] = None,
        on_print_clicked: Optional[Callable[[], None]] = None,
        on_export_clicked: Optional[Callable[[], None]] = None,
        on_dpi_changed: Optional[Callable[[float], None]] = None,
        on_rotation_changed: Optional[Callable[[int], None]] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.on_render_clicked = on_render_clicked
        self.on_dry_run_clicked = on_dry_run_clicked
        self.on_print_clicked = on_print_clicked
        self.on_export_clicked = on_export_clicked
        self.on_dpi_changed = on_dpi_changed
        self.on_rotation_changed = on_rotation_changed

        self.var_json_path = tk.StringVar()
        self.var_template_path = tk.StringVar()
        self.var_format = tk.StringVar(value="all")
        self.var_dpi = tk.StringVar(value=self.DPI_PRESETS[0])
        self.var_rotation = tk.StringVar(value=self.ROTATION_PRESETS[0])
        self.var_threshold = tk.IntVar(value=128)
        self.var_super_sample = tk.BooleanVar(value=True)

        self._build_ui()

    def get_dpi(self) -> float:
        """Parses and returns the currently selected DPI resolution as a float."""
        val = self.var_dpi.get().strip()
        try:
            # Extract leading numeric part (e.g. '203.2' from '203.2 DPI (8 dpmm)')
            dpi_str = val.split()[0] if val else "203.2"
            return float(dpi_str)
        except (ValueError, IndexError):
            return 203.2

    def get_rotation(self) -> int:
        """Parses and returns the currently selected rotation angle as an integer (0, 90, 180, 270)."""
        val = self.var_rotation.get().strip()
        try:
            rot_str = val.replace("°", "").strip()
            return int(rot_str) if rot_str else 0
        except (ValueError, IndexError):
            return 0

    def get_binarization_threshold(self) -> int:
        """Returns the current monochrome binarization threshold [0..255]."""
        try:
            val = int(self.var_threshold.get())
            return max(0, min(255, val))
        except (ValueError, tk.TclError):
            return 128

    def get_super_sample_factor(self) -> int:
        """Returns super-sampling factor (2 if enabled, 1 if disabled)."""
        return 2 if self.var_super_sample.get() else 1

    def set_binarization_threshold(self, value: int) -> None:
        """Sets the binarization threshold value."""
        clamped = max(0, min(255, int(value)))
        self.var_threshold.set(clamped)

    def _build_ui(self):
        # Configure responsive grid for the 3 control groups
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=0)
        self.rowconfigure(0, weight=1)

        # Frame 1: File Pickers (compact width=24, expanding column 1)
        files_frame = ttk.LabelFrame(self, text="Source Inputs", padding=4)
        files_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=1)

        # JSON Selector
        ttk.Label(files_frame, text="SAP JSON:").grid(row=0, column=0, sticky="w", padx=2, pady=1)
        ttk.Entry(files_frame, textvariable=self.var_json_path, width=24).grid(row=0, column=1, sticky="ew", padx=2, pady=1)
        ttk.Button(files_frame, text="Browse...", width=8, command=self._browse_json).grid(row=0, column=2, padx=2, pady=1)

        # SVG Selector
        ttk.Label(files_frame, text="SVG Tpl:").grid(row=1, column=0, sticky="w", padx=2, pady=1)
        ttk.Entry(files_frame, textvariable=self.var_template_path, width=24).grid(row=1, column=1, sticky="ew", padx=2, pady=1)
        ttk.Button(files_frame, text="Browse...", width=8, command=self._browse_svg).grid(row=1, column=2, padx=2, pady=1)

        files_frame.columnconfigure(1, weight=1)

        # Frame 2: Format, DPI, Rotation & Binarization Quality Settings
        opts_frame = ttk.LabelFrame(self, text="Output, DPI, Rotation & Quality", padding=4)
        opts_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=1)

        # Format Combobox
        fmt_container = ttk.Frame(opts_frame)
        fmt_container.pack(side="left", padx=2, pady=0)
        ttk.Label(fmt_container, text="Format:").pack(side="top", anchor="w")
        cb_format = ttk.Combobox(
            fmt_container,
            textvariable=self.var_format,
            values=["all", "zpl", "tspl", "ipl", "pdf", "svg", "png", "bmp"],
            state="readonly",
            width=7,
        )
        cb_format.pack(side="top", pady=1, fill="x")

        # DPI Combobox
        dpi_container = ttk.Frame(opts_frame)
        dpi_container.pack(side="left", padx=2, pady=0)
        ttk.Label(dpi_container, text="Printer DPI:").pack(side="top", anchor="w")
        cb_dpi = ttk.Combobox(
            dpi_container,
            textvariable=self.var_dpi,
            values=self.DPI_PRESETS,
            state="readonly",
            width=15,
        )
        cb_dpi.pack(side="top", pady=1, fill="x")
        cb_dpi.bind("<<ComboboxSelected>>", self._handle_dpi_selected)
        _ToolTip(cb_dpi, "Select thermal printhead resolution (203.2 / 300 / 600 DPI)")

        # Rotation Combobox
        rot_container = ttk.Frame(opts_frame)
        rot_container.pack(side="left", padx=2, pady=0)
        ttk.Label(rot_container, text="Rotation:").pack(side="top", anchor="w")
        cb_rot = ttk.Combobox(
            rot_container,
            textvariable=self.var_rotation,
            values=self.ROTATION_PRESETS,
            state="readonly",
            width=6,
        )
        cb_rot.pack(side="top", pady=1, fill="x")
        cb_rot.bind("<<ComboboxSelected>>", self._handle_rotation_selected)
        _ToolTip(cb_rot, "Rotate image (0°, 90°, 180°, 270° CW) before 1-bit & printer encoding")

        # Threshold Spinbox + Auto Otsu Button
        thresh_container = ttk.Frame(opts_frame)
        thresh_container.pack(side="left", padx=2, pady=0)
        ttk.Label(thresh_container, text="Threshold:").pack(side="top", anchor="w")
        thresh_sub = ttk.Frame(thresh_container)
        thresh_sub.pack(side="top", pady=1, fill="x")
        sp_thresh = ttk.Spinbox(
            thresh_sub,
            from_=0,
            to=255,
            increment=1,
            textvariable=self.var_threshold,
            width=4,
        )
        sp_thresh.pack(side="left", padx=(0, 2))
        _ToolTip(sp_thresh, "Monochrome binarization threshold (0-255). Lower = thinner strokes, Higher = bolder text")

        btn_otsu = ttk.Button(
            thresh_sub,
            text="Auto",
            width=4,
            command=self._handle_auto_otsu,
        )
        btn_otsu.pack(side="left")
        _ToolTip(btn_otsu, "Auto-detect optimal threshold using Otsu algorithm from rendered preview")

        # Super-Sampling 2x Checkbox
        ss_container = ttk.Frame(opts_frame)
        ss_container.pack(side="left", padx=2, pady=0)
        ttk.Label(ss_container, text="Anti-Aliasing:").pack(side="top", anchor="w")
        chk_ss = ttk.Checkbutton(
            ss_container,
            text="2x SuperSample",
            variable=self.var_super_sample,
        )
        chk_ss.pack(side="top", pady=2)
        _ToolTip(chk_ss, "Render at 2x resolution and downscale with LANCZOS to smooth text outlines and borders")

        # Frame 3: Action Buttons
        actions_frame = ttk.LabelFrame(self, text="Engine Actions", padding=4)
        actions_frame.grid(row=0, column=2, sticky="nsew", padx=2, pady=1)

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
            padx=8,
            pady=3,
            cursor="hand2",
        )
        btn_render.pack(side="left", padx=3, pady=2)

        # "Template Dry-Run" -> Neutral (default ttk style)
        btn_dry_run = ttk.Button(
            actions_frame,
            text=" Dry-Run ",
            command=self._handle_dry_run,
        )
        btn_dry_run.pack(side="left", padx=3, pady=2)

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
            padx=8,
            pady=3,
            cursor="hand2",
        )
        btn_print.pack(side="left", padx=3, pady=2)

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
            padx=8,
            pady=3,
            cursor="hand2",
        )
        btn_export.pack(side="left", padx=3, pady=2)
        _ToolTip(btn_export, "Simpan file hasil render (SVG/PNG/BMP/ZPL/TSPL/IPL) ke folder tujuan")

    def _handle_dpi_selected(self, _event=None):
        if self.on_dpi_changed:
            self.on_dpi_changed(self.get_dpi())

    def _handle_rotation_selected(self, _event=None):
        if self.on_rotation_changed:
            self.on_rotation_changed(self.get_rotation())

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

    def _handle_auto_otsu(self):
        """Calculates and sets Otsu threshold using preview.png from out/ directory or triggers render if missing."""
        out_preview = Path("out") / "preview.png"
        if out_preview.is_file():
            try:
                from engine.rasterizer import calculate_otsu_threshold
                optimal_t = calculate_otsu_threshold(out_preview)
                self.set_binarization_threshold(optimal_t)
                messagebox.showinfo("Auto Threshold", f"Optimal Otsu Threshold detected: {optimal_t}")
                if self.on_render_clicked:
                    self.on_render_clicked()
                return
            except Exception as e:
                messagebox.showwarning("Auto Threshold", f"Could not calculate Otsu threshold: {e}")
        else:
            messagebox.showinfo("Auto Threshold", "Please click 'Render & Inspect' first to generate preview.")

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
