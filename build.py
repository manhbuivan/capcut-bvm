"""Build script - package app with PyInstaller."""
import subprocess
import sys


def build():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "CapCutBVM",
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        # Include data files
        "--add-data", "config.json;.",
        "--add-data", "assets;assets",
        # Hidden imports for PySide6
        "--hidden-import", "PySide6.QtSvg",
        "--hidden-import", "PySide6.QtSvgWidgets",
        # Entry point
        "main.py",
    ]

    print("Building CapCut BVM...")
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n✅ Build successful! Check dist/CapCutBVM/")
    else:
        print("\n❌ Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    build()
