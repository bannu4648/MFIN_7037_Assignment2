#!/usr/bin/env python3
"""Build the PDF report for Question 3 (flow-imbalance long/short)."""
import sys
from pathlib import Path

# Allow importing from the shared "common" package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.data_loader import ROOT  # type: ignore  # noqa: E402
from common.pdf_reports import build_q3_pdf  # type: ignore  # noqa: E402


def main() -> None:
    pdf_path = build_q3_pdf(ROOT)
    print(f"Wrote Q3 PDF: {pdf_path}")


if __name__ == "__main__":
    main()

