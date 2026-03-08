#!/usr/bin/env python3
"""Run Q3 and Q4 backtests and regenerate PDFs in one step.

Usage (from the Q3 and 4 directory):

    python3 run_all.py

This will:
  1. Run Q3/run_q3.py (flow-imbalance strategy backtest)
  2. Run Q4/run_q4.py (7-day momentum strategy backtest)
  3. Regenerate the Q3 and Q4 PDF reports via make_pdfs.py
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent

# Ensure we can import the per-question scripts and shared modules
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "Q3"))
sys.path.insert(0, str(BASE / "Q4"))

import run_q3  # type: ignore  # noqa: E402
import run_q4  # type: ignore  # noqa: E402
import make_pdfs  # type: ignore  # noqa: E402


def main() -> None:
    print("=" * 60)
    print("Running Q3 backtest...")
    print("=" * 60)
    run_q3.main()

    print("\n" + "=" * 60)
    print("Running Q4 backtest...")
    print("=" * 60)
    run_q4.main()

    print("\n" + "=" * 60)
    print("Building Q3 and Q4 PDF reports...")
    print("=" * 60)
    make_pdfs.main()


if __name__ == "__main__":
    main()

