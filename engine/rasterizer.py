"""
SVG to Bitmap Rasterizer Module using resvg CLI executable.
Converts SVG to PNG Preview and 1-Bit Monochrome BMP.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Union
from PIL import Image


def get_resvg_executable_path() -> Path:
    """Resolves path to resvg.exe binary bundled with the engine or in PyInstaller bundle."""
    # PyInstaller bundle support (_MEIPASS)
    if hasattr(sys, "_MEIPASS"):
        meipass_resvg = Path(sys._MEIPASS) / "engine" / "bin" / "resvg.exe"
        if meipass_resvg.is_file():
            return meipass_resvg

    current_dir = Path(__file__).parent
    bundled_resvg = current_dir / "bin" / "resvg.exe"
    if bundled_resvg.is_file():
        return bundled_resvg

    # Fallback to system path
    import shutil
    sys_resvg = shutil.which("resvg")
    if sys_resvg:
        return Path(sys_resvg)

    raise FileNotFoundError(
        f"resvg executable not found. Expected at '{bundled_resvg.resolve()}' or in system PATH."
    )



def svg_to_png(
    svg_source: Union[str, Path],
    output_png_path: Union[str, Path],
    width_px: int = 1600,
    height_px: int = 640,
    dpi: float = 203.2,
    resvg_path: Optional[Union[str, Path]] = None,
    timeout: float = 15.0,
) -> Path:
    """
    Renders an SVG file or SVG string to PNG image using resvg CLI.
    Default dimensions: 1600 x 640 px (200mm x 80mm @ 203.2 DPI / 8 dots per mm).
    Includes explicit process timeout and Windows-safe creationflags to avoid hangs
    in windowed PyInstaller desktop apps.
    """
    resvg_exe = Path(resvg_path) if resvg_path else get_resvg_executable_path()
    if not resvg_exe.is_file():
        raise FileNotFoundError(f"resvg binary not found: {resvg_exe.resolve()}")

    out_p = Path(output_png_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    # If svg_source is a path to an existing file
    is_file = False
    if isinstance(svg_source, (str, Path)):
        p = Path(svg_source)
        if p.is_file():
            is_file = True
            input_file = p

    temp_svg_file: Optional[Path] = None
    if not is_file:
        # Write SVG content to temp file
        temp_svg_file = out_p.parent / f"_temp_{os.getpid()}.svg"
        with open(temp_svg_file, "w", encoding="utf-8") as f:
            f.write(str(svg_source))
        input_file = temp_svg_file

    try:
        cmd = [
            str(resvg_exe),
            str(input_file.resolve()),
            str(out_p.resolve()),
            "--width", str(width_px),
            "--height", str(height_px),
            "--dpi", str(int(round(dpi))),
            "--background", "white",
        ]

        # Windows-safe creationflags to suppress console popup and prevent stdio hang
        kwargs = {
            "capture_output": True,
            "text": True,
            "check": False,
            "stdin": subprocess.DEVNULL,
            "timeout": timeout,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        result = subprocess.run(cmd, **kwargs)
        if result.returncode != 0:
            raise RuntimeError(f"resvg failed with code {result.returncode}: {result.stderr}")

        if not out_p.is_file():
            raise FileNotFoundError(f"Output PNG not created by resvg: {out_p}")

        return out_p
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"resvg rendering timed out after {timeout} seconds: {e}") from e
    except OSError as e:
        raise RuntimeError(f"Failed to execute resvg binary '{resvg_exe}': {e}") from e
    finally:
        if temp_svg_file and temp_svg_file.is_file():
            try:
                temp_svg_file.unlink()
            except OSError:
                pass


def png_to_1bit_monochrome(
    png_source: Union[str, Path, Image.Image],
    threshold: int = 128,
) -> Image.Image:
    """
    Converts PNG image to 1-Bit monochrome binarized PIL Image (mode '1')
    without dithering using a clean threshold point lookup.
    """
    if isinstance(png_source, Image.Image):
        img = png_source
    else:
        img = Image.open(png_source)

    # Convert to Grayscale ('L')
    gray = img.convert("L")

    # Threshold lookup table: < threshold -> 0 (Black), >= threshold -> 255 (White)
    table = [0 if i < threshold else 255 for i in range(256)]
    binarized = gray.point(table, mode="1")
    return binarized


def save_1bit_bmp(image_1bit: Image.Image, output_bmp_path: Union[str, Path]) -> Path:
    """Saves 1-bit monochrome PIL Image to BMP file."""
    out_p = Path(output_bmp_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    if image_1bit.mode != "1":
        image_1bit = image_1bit.convert("1", dither=Image.NONE)
    image_1bit.save(out_p, format="BMP")
    return out_p

