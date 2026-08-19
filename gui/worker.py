"""
GUI Background Worker Thread Module.
Executes label rendering tasks asynchronously to prevent UI freeze,
with explicit timeout and error propagation callbacks to Tkinter main thread.
"""

from __future__ import annotations

from pathlib import Path
import threading
from typing import Any, Callable, Dict, Optional, Union
import tkinter as tk

from engine.processor import process_label
from engine.renderer import RendererError


class RenderWorker:
    """
    Background worker thread for executing label rendering pipelines safely.
    All callbacks are guaranteed to be scheduled on the Tkinter main loop via parent.after().
    """

    def __init__(
        self,
        parent: tk.Tk,
        json_path: Path,
        template_path: Path,
        out_dir: Path,
        fmt: str,
        on_success: Callable[[Path, Dict[str, Path]], None],
        on_error: Callable[[str], None],
    ):
        self.parent = parent
        self.json_path = json_path
        self.template_path = template_path
        self.out_dir = out_dir
        self.fmt = fmt
        self.on_success = on_success
        self.on_error = on_error
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Starts the worker thread."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        """Worker execution loop running in background thread."""
        try:
            results = process_label(
                json_source=self.json_path,
                template_source=self.template_path,
                out_dir=self.out_dir,
                formats=self.fmt,
            )
            # Dispatch success callback on UI thread
            self.parent.after(0, self.on_success, self.json_path, results)
        except RendererError as e:
            err_msg = f"Template/Data Contract Error: {e}"
            self.parent.after(0, self.on_error, err_msg)
        except RuntimeError as e:
            err_msg = f"Engine Execution Error: {e}"
            self.parent.after(0, self.on_error, err_msg)
        except Exception as e:
            err_msg = f"Unexpected Error: {type(e).__name__}: {e}"
            self.parent.after(0, self.on_error, err_msg)
