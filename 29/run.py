#!/usr/bin/env python3
"""
Streamlitアプリケーション起動スクリプト
"""
import subprocess
import sys
from pathlib import Path


def main() -> None:
    app_path = Path(__file__).parent / "src" / "sd_29" / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])


if __name__ == "__main__":
    main()
