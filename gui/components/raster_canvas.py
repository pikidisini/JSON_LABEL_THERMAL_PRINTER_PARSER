"""
Visual Raster Canvas Component.
Displays the exact 1-bit / preview raster label (1600x640 px @ 203.2 DPI) with interactive
drag-to-pan, MouseWheel zoom-at-cursor, and a Fit Window auto-scale default view.
"""

from pathlib import Path
from typing import Optional, Union
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


class RasterCanvasWidget(ttk.Frame):
    """Interactive, pannable & zoomable canvas for viewing high-resolution 1600x640 label renders."""

    MIN_ZOOM = 0.1
    MAX_ZOOM = 4.0
    DEFAULT_FALLBACK_WIDTH = 800
    DEFAULT_FALLBACK_HEIGHT = 400

    def __init__(self, parent: tk.Widget, **kwargs):
        super().__init__(parent, **kwargs)
        self._pil_image: Optional[Image.Image] = None
        self._tk_image: Optional[ImageTk.PhotoImage] = None
        self._zoom_factor: float = 0.5
        self._image_item = None
        self._pan_start = None
        self.on_canvas_element_clicked = None
        self._bounding_boxes = []  # List[BoundingBox]
        self._highlighted_path: Optional[str] = None
        self._highlight_items = []
        self._drag_threshold_passed = False
        self._dpi: float = 203.2
        self._width_mm: float = 200.0
        self._height_mm: float = 80.0

        self._user_has_zoomed = False
        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Header Container Frame (2 Rows for full responsiveness on resize)
        header_frame = ttk.Frame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        header_frame.columnconfigure(0, weight=1)

        # --- Top Row: Title & Resolution ---
        top_row = ttk.Frame(header_frame)
        top_row.pack(fill="x", expand=True, pady=(0, 2))

        self.lbl_title = ttk.Label(
            top_row,
            text=f"Visual Thermal Print Preview ({self._dpi:.1f} DPI)",
            font=("Segoe UI", 10, "bold"),
        )
        self.lbl_title.pack(side="left", padx=4)

        self.lbl_dims = ttk.Label(top_row, text="Dimensions: 0 x 0 px", foreground="gray")
        self.lbl_dims.pack(side="left", padx=8)

        # --- Bottom Row: Instructions (Left) & Zoom Toolbar (Right) ---
        bottom_row = ttk.Frame(header_frame)
        bottom_row.pack(fill="x", expand=True)

        ttk.Label(
            bottom_row,
            text="(Drag = Pan  |  Scroll = Zoom)",
            foreground="#888888",
            font=("Segoe UI", 8, "italic"),
        ).pack(side="left", padx=4)

        # Zoom Controls
        btn_zoom_out = ttk.Button(bottom_row, text=" Zoom Out - ", width=11, command=self._zoom_out)
        btn_zoom_out.pack(side="right", padx=2)

        self.lbl_zoom = ttk.Label(bottom_row, text="50%", width=5, anchor="center")
        self.lbl_zoom.pack(side="right", padx=2)

        btn_zoom_in = ttk.Button(bottom_row, text=" Zoom In + ", width=11, command=self._zoom_in)
        btn_zoom_in.pack(side="right", padx=2)

        btn_actual = ttk.Button(bottom_row, text="100% Actual", width=11, command=self._zoom_100)
        btn_actual.pack(side="right", padx=2)

        btn_fit = ttk.Button(bottom_row, text="Fit Window", width=10, command=self._fit_window)
        btn_fit.pack(side="right", padx=2)

        # Scrollable Canvas
        canvas_frame = ttk.Frame(self)
        canvas_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=2)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_frame, bg="#333333", highlightthickness=0, cursor="hand2")
        vsb = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        hsb = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # --- Interactivity bindings ---
        self.canvas.bind("<ButtonPress-1>", self._on_pan_start)
        self.canvas.bind("<B1-Motion>", self._on_pan_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_pan_end)
        self.canvas.bind("<Motion>", self._on_mouse_move)

        # Direct MouseWheel Zoom (no Ctrl required)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel_zoom)
        self.canvas.bind("<Button-4>", lambda e: self._zoom_at(e, 1.1))
        self.canvas.bind("<Button-5>", lambda e: self._zoom_at(e, 0.9))
        self.canvas.bind("<Configure>", self._on_canvas_resize)

    def set_canvas_metadata(
        self,
        dpi: float = 203.2,
        width_mm: float = 200.0,
        height_mm: float = 80.0,
    ) -> None:
        """Updates canvas resolution info and header title dynamically."""
        self._dpi = dpi
        self._width_mm = width_mm
        self._height_mm = height_mm
        self.lbl_title.config(text=f"Visual Thermal Print Preview ({dpi:.1f} DPI)")
        if self._pil_image:
            w, h = self._pil_image.size
            mm_w = (w / dpi) * 25.4
            mm_h = (h / dpi) * 25.4
            self.lbl_dims.config(
                text=f"Resolution: {w} x {h} px ({mm_w:.1f} x {mm_h:.1f} mm @ {dpi:.1f} DPI)"
            )

    def load_image(
        self,
        image_source: Union[str, Path, Image.Image],
        dpi: Optional[float] = None,
        width_mm: float = 200.0,
        height_mm: float = 80.0,
    ) -> None:
        """Loads a raster image file or PIL Image object and auto-fits it to the window (default view)."""
        try:
            if dpi is not None:
                self._dpi = dpi
            self._width_mm = width_mm
            self._height_mm = height_mm

            if isinstance(image_source, (str, Path)):
                img_path = Path(image_source)
                if not img_path.is_file():
                    self.show_error(f"❌ Preview image file not found: {img_path.name}")
                    return
                self._pil_image = Image.open(str(img_path))
            elif isinstance(image_source, Image.Image):
                self._pil_image = image_source
            else:
                self.show_error(f"❌ Unsupported image format: {type(image_source).__name__}")
                return

            w, h = self._pil_image.size
            mm_w = (w / self._dpi) * 25.4
            mm_h = (h / self._dpi) * 25.4
            self.lbl_title.config(text=f"Visual Thermal Print Preview ({self._dpi:.1f} DPI)")
            self.lbl_dims.config(
                text=f"Resolution: {w} x {h} px ({mm_w:.1f} x {mm_h:.1f} mm @ {self._dpi:.1f} DPI)"
            )
            self._user_has_zoomed = False
            self.canvas.update_idletasks()
            self._fit_window()
        except Exception as e:
            self.show_error(f"❌ Failed to load preview image: {e}")

    def show_error(self, message: str) -> None:
        """Displays a centered visual error message on the canvas."""
        self._pil_image = None
        self._tk_image = None
        self._image_item = None
        self.canvas.delete("all")
        self.lbl_dims.config(text="Resolution: 0 x 0 px")
        self.lbl_zoom.config(text="--")

        self.canvas.update_idletasks()
        cw = max(self.canvas.winfo_width(), self.DEFAULT_FALLBACK_WIDTH)
        ch = max(self.canvas.winfo_height(), self.DEFAULT_FALLBACK_HEIGHT)
        self.canvas.create_text(
            cw // 2,
            ch // 2,
            text=message,
            fill="#FF6B6B",
            font=("Segoe UI", 12, "bold"),
            anchor="center",
            justify="center",
        )
        self.canvas.config(scrollregion=(0, 0, cw, ch))

    def _update_view(self) -> None:
        if not self._pil_image:
            return

        w, h = self._pil_image.size
        new_w = max(10, int(w * self._zoom_factor))
        new_h = max(10, int(h * self._zoom_factor))

        resized = self._pil_image.resize((new_w, new_h), Image.Resampling.NEAREST)
        self._tk_image = ImageTk.PhotoImage(resized)

        self.canvas.delete("all")
        margin = 20
        self._image_item = self.canvas.create_image(margin, margin, anchor="nw", image=self._tk_image)
        self.canvas.config(scrollregion=(0, 0, new_w + margin * 2, new_h + margin * 2))
        self.lbl_zoom.config(text=f"{int(self._zoom_factor * 100)}%")
        self._redraw_highlights()


    def _center_image(self):
        """Centers the image within the visible canvas area so it is never clipped."""
        if not self._pil_image or self._image_item is None:
            return
        self.canvas.update_idletasks()
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        w, h = self._pil_image.size
        img_w = int(w * self._zoom_factor)
        img_h = int(h * self._zoom_factor)

        region_w = max(canvas_w, img_w + 40)
        region_h = max(canvas_h, img_h + 40)
        offset_x = max(20, (canvas_w - img_w) // 2)
        offset_y = max(20, (canvas_h - img_h) // 2)

        self.canvas.coords(self._image_item, offset_x, offset_y)
        self.canvas.config(scrollregion=(0, 0, region_w, region_h))

    def _zoom_in(self):
        self._user_has_zoomed = True
        self._zoom_factor = min(self.MAX_ZOOM, round(self._zoom_factor + 0.1, 2))
        self._update_view()
        self._center_image()

    def _zoom_out(self):
        self._user_has_zoomed = True
        self._zoom_factor = max(self.MIN_ZOOM, round(self._zoom_factor - 0.1, 2))
        self._update_view()
        self._center_image()

    def _zoom_100(self):
        self._user_has_zoomed = True
        self._zoom_factor = 1.0
        self._update_view()
        self._center_image()

    def _fit_width(self):
        """Legacy helper retained for compatibility - fits image width only."""
        if not self._pil_image:
            return
        canvas_width = self.canvas.winfo_width() - 40
        if canvas_width <= 50:
            canvas_width = self.DEFAULT_FALLBACK_WIDTH - 40
        img_width = self._pil_image.size[0]
        self._zoom_factor = max(self.MIN_ZOOM, min(self.MAX_ZOOM, canvas_width / img_width))
        self._update_view()
        self._center_image()

    def _fit_window(self):
        """Auto-scales the image so it fits entirely within the visible canvas viewport.
        Uses fallback dimensions if the window has not completed its initial render."""
        if not self._pil_image:
            return
        self.canvas.update_idletasks()
        canvas_w = self.canvas.winfo_width() - 40
        canvas_h = self.canvas.winfo_height() - 40
        img_w, img_h = self._pil_image.size

        # Use robust fallback size if canvas is unmapped/collapsed
        if canvas_w <= 50:
            canvas_w = self.DEFAULT_FALLBACK_WIDTH - 40
        if canvas_h <= 50:
            canvas_h = self.DEFAULT_FALLBACK_HEIGHT - 40

        ratio_w = canvas_w / img_w
        ratio_h = canvas_h / img_h
        self._zoom_factor = max(self.MIN_ZOOM, min(self.MAX_ZOOM, min(ratio_w, ratio_h)))

        self._update_view()
        self._center_image()

    def _on_canvas_resize(self, event):
        if self._pil_image and not self._user_has_zoomed:
            self._fit_window()

    def set_bounding_boxes(self, boxes) -> None:
        """Sets the list of BoundingBox objects and refreshes highlights."""
        self._bounding_boxes = list(boxes) if boxes else []
        self._redraw_highlights()

    def highlight_path(self, json_path: Optional[str]) -> None:
        """Highlights bounding boxes associated with a specific JSON path and centers the view."""
        self._highlighted_path = json_path
        self._redraw_highlights()
        if json_path:
            self._center_on_highlight(json_path)

    def _get_image_offset(self):
        if not self._image_item:
            return 20, 20
        coords = self.canvas.coords(self._image_item)
        if len(coords) >= 2:
            return coords[0], coords[1]
        return 20, 20

    def _redraw_highlights(self) -> None:
        """Draws glowing vector rectangle overlays over active elements."""
        for item_id in self._highlight_items:
            self.canvas.delete(item_id)
        self._highlight_items.clear()

        if not self._pil_image or not self._bounding_boxes:
            return

        off_x, off_y = self._get_image_offset()
        zoom = self._zoom_factor

        for box in self._bounding_boxes:
            # Check match: exact or suffix
            is_active = False
            if self._highlighted_path:
                if box.json_path == self._highlighted_path or \
                   box.json_path.endswith(f".{self._highlighted_path}") or \
                   self._highlighted_path.endswith(f".{box.json_path}"):
                    is_active = True

            if is_active:
                x1 = off_x + box.x * zoom
                y1 = off_y + box.y * zoom
                x2 = off_x + box.x2 * zoom
                y2 = off_y + box.y2 * zoom

                # Outer high-contrast shadow & inner vibrant border
                outer = self.canvas.create_rectangle(
                    x1 - 2, y1 - 2, x2 + 2, y2 + 2,
                    outline="#ffffff", width=4, tags="highlight_overlay"
                )
                inner = self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline="#007acc", width=2, tags="highlight_overlay"
                )
                self._highlight_items.extend([outer, inner])

    def _center_on_highlight(self, json_path: str) -> None:
        """Smoothly pans canvas viewport so the highlighted element is centered."""
        matching = [b for b in self._bounding_boxes if b.json_path == json_path or b.json_path.endswith(f".{json_path}")]
        if not matching:
            return
        box = matching[0]
        off_x, off_y = self._get_image_offset()
        zoom = self._zoom_factor

        cx = off_x + (box.x + box.width / 2.0) * zoom
        cy = off_y + (box.y + box.height / 2.0) * zoom

        region = self.canvas.bbox("all")
        if not region:
            return
        region_w = region[2] - region[0]
        region_h = region[3] - region[1]
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        if region_w > 0 and canvas_w > 0:
            target_x = max(0.0, min(1.0, (cx - canvas_w / 2.0) / region_w))
            self.canvas.xview_moveto(target_x)
        if region_h > 0 and canvas_h > 0:
            target_y = max(0.0, min(1.0, (cy - canvas_h / 2.0) / region_h))
            self.canvas.yview_moveto(target_y)

    def _canvas_to_image_coords(self, event_x: int, event_y: int):
        """Converts canvas event coordinates to original raster image pixel space."""
        cx = self.canvas.canvasx(event_x)
        cy = self.canvas.canvasy(event_y)
        off_x, off_y = self._get_image_offset()
        zoom = self._zoom_factor
        if zoom <= 0:
            return None, None
        img_px = (cx - off_x) / zoom
        img_py = (cy - off_y) / zoom
        return img_px, img_py

    def _find_box_at(self, img_px: float, img_py: float):
        """Finds the smallest bounding box containing (img_px, img_py)."""
        candidates = [b for b in self._bounding_boxes if b.contains_point(img_px, img_py, self._zoom_factor)]
        if not candidates:
            return None
        # Sort by area ascending so smaller child elements take precedence over containers
        candidates.sort(key=lambda b: b.width * b.height)
        return candidates[0]

    def _on_mouse_move(self, event):
        """Changes cursor to pointing hand when hovering over an interactive element."""
        if not self._bounding_boxes or not self._pil_image:
            return
        px, py = self._canvas_to_image_coords(event.x, event.y)
        if px is not None and py is not None:
            box = self._find_box_at(px, py)
            self.canvas.config(cursor="hand2" if box else "")


    def _on_pan_start(self, event):
        self.canvas.scan_mark(event.x, event.y)
        self._pan_start = (event.x, event.y)
        self._drag_threshold_passed = False

    def _on_pan_move(self, event):
        if self._pan_start is not None:
            dx = abs(event.x - self._pan_start[0])
            dy = abs(event.y - self._pan_start[1])
            if dx > 4 or dy > 4:
                self._drag_threshold_passed = True
                self.canvas.config(cursor="fleur")
                self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_pan_end(self, event):
        if not self._drag_threshold_passed and self._pan_start is not None:
            # It's a clean click without pan: perform element selection!
            px, py = self._canvas_to_image_coords(event.x, event.y)
            if px is not None and py is not None:
                box = self._find_box_at(px, py)
                if box:
                    self.highlight_path(box.json_path)
                    if self.on_canvas_element_clicked:
                        self.on_canvas_element_clicked(box.json_path)

        self._pan_start = None
        self._drag_threshold_passed = False
        self.canvas.config(cursor="hand2")

    def _on_mousewheel_zoom(self, event):
        """Direct mousewheel zoom without requiring Ctrl key."""
        factor = 1.1 if event.delta > 0 else 0.9
        self._zoom_at(event, factor)

    def _zoom_at(self, event, factor: float):
        """Zooms in/out keeping the point under the mouse cursor fixed on screen."""
        if not self._pil_image:
            return
        self._user_has_zoomed = True

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        old_zoom = self._zoom_factor
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, round(old_zoom * factor, 3)))
        if new_zoom == old_zoom:
            return

        scale_ratio = new_zoom / old_zoom
        self._zoom_factor = new_zoom
        self._update_view()

        new_canvas_x = canvas_x * scale_ratio
        new_canvas_y = canvas_y * scale_ratio
        region = self.canvas.bbox("all")
        if region:
            region_w = region[2] - region[0]
            region_h = region[3] - region[1]
            if region_w > 0:
                self.canvas.xview_moveto(max(0.0, (new_canvas_x - event.x) / region_w))
            if region_h > 0:
                self.canvas.yview_moveto(max(0.0, (new_canvas_y - event.y) / region_h))

