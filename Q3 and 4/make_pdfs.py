#!/usr/bin/env python3
"""Build PDF versions of the Q3 and Q4 reports."""
from pathlib import Path

from common.data_loader import ROOT
from common.pdf_reports import build_q3_pdf, build_q4_pdf


def main():
    root = ROOT  # assignment root (parent of "Q3 and 4")
    q3_pdf = build_q3_pdf(root)
    q4_pdf = build_q4_pdf(root)
    print(f"Wrote Q3 PDF: {q3_pdf}")
    print(f"Wrote Q4 PDF: {q4_pdf}")


if __name__ == "__main__":
    main()

