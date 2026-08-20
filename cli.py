"""
CLI Entrypoint for Centralized Factory Label Printing Engine.

Usage:
    python cli.py --json <path_to_json> --template <path_to_svg> [--out-dir <path>] [--format all|zpl|tspl|ipl|pdf|png|bmp|svg] [--dpi 203.2]
"""

import argparse
import sys
from pathlib import Path

from engine.processor import process_label
from engine.renderer import RendererError


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Centralized Factory Label Engine CLI - 3-Layer Architecture"
    )
    parser.add_argument("--json", required=True, help="Path to input JSON contract file")
    parser.add_argument("--template", required=True, help="Path to SVG template file")
    parser.add_argument(
        "--out-dir",
        required=False,
        default="out",
        help="Directory to store rendered outputs (default: 'out' in current working directory)",
    )
    parser.add_argument(
        "--format",
        required=False,
        default="all",
        choices=["all", "zpl", "tspl", "ipl", "pdf", "png", "bmp", "svg"],
        help="Output format to generate (default: all)",
    )
    parser.add_argument(
        "--dpi",
        required=False,
        type=float,
        default=203.2,
        help="Thermal printer resolution DPI (default: 203.2 = 8 dots/mm)",
    )
    parser.add_argument(
        "--rotation",
        required=False,
        type=int,
        default=0,
        choices=[0, 90, 180, 270],
        help="Image rotation angle in degrees (default: 0 = normal)",
    )

    args = parser.parse_args()

    try:
        json_path = Path(args.json)
        template_path = Path(args.template)
        out_dir = Path(args.out_dir)

        results = process_label(
            json_source=json_path,
            template_source=template_path,
            out_dir=out_dir,
            formats=args.format,
            dpi=args.dpi,
            rotation=args.rotation,
        )

        print("[OK] Label processed successfully. Generated files:")
        for fmt, path in results.items():
            print(f"  - [{fmt.upper()}] {path.resolve()}")
        return 0

    except RendererError as e:
        print(f"[ERROR - RENDERER] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR - SYSTEM] {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

