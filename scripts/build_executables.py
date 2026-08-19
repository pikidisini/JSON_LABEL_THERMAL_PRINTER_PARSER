"""
Build script for PyInstaller single-file standalone executables:
1. label_engine.exe (Headless CLI engine for SAP background process)
2. LabelPreviewApp.exe (Desktop Preview & Inspector GUI)
"""

import os
from pathlib import Path
import subprocess
import sys


def build():
    root = Path(__file__).parent.parent
    os.chdir(root)

    print("==================================================")
    print(" 1. Building CLI Executable: label_engine.exe")
    print("==================================================")
    cmd_cli = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "label_engine",
        "--add-binary",
        "engine/bin/resvg.exe;engine/bin",
        "--add-data",
        "assets/templates;assets/templates",
        "--add-data",
        "data_samples;data_samples",
        "cli.py",
    ]
    subprocess.run(cmd_cli, check=True)

    print("\n==================================================")
    print(" 2. Building Desktop GUI App: LabelPreviewApp.exe")
    print("==================================================")
    cmd_gui = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "LabelPreviewApp",
        "--add-binary",
        "engine/bin/resvg.exe;engine/bin",
        "--add-data",
        "assets/templates;assets/templates",
        "--add-data",
        "data_samples;data_samples",
        "gui/app.py",
    ]
    subprocess.run(cmd_gui, check=True)

    print("\n==================================================")
    print(" BUILD COMPLETED SUCCESSFULLY!")
    print(" Executables are located in: dist/")
    print("  - dist/label_engine.exe")
    print("  - dist/LabelPreviewApp.exe")
    print("==================================================")


if __name__ == "__main__":
    build()
