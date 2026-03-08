"""Utilities to convert the Q3/Q4 markdown reports to PDFs with embedded figures."""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer


def _md_to_story(md_path: Path, image_paths=None):
    """Very lightweight Markdown-to-ReportLab conversion for our reports."""
    styles = getSampleStyleSheet()
    # Subsection heading (###) — same family as Heading2, slightly smaller
    if "Heading3" not in styles.byName:
        styles.add(ParagraphStyle(
            name="Heading3",
            parent=styles["Heading2"],
            fontSize=11,
            spaceBefore=10,
            spaceAfter=6,
        ))
    story = []

    # Make a working copy so we can consume images in order as we see placeholders
    pending_images = [Path(p) for p in (image_paths or [])]

    text = md_path.read_text(encoding="utf-8")
    # Split into paragraphs by blank lines
    for block in text.split("\n\n"):
        raw = block.strip()
        if not raw:
            continue

        # If this paragraph is an inline markdown image reference, treat it
        # as a placeholder and drop the next pending image into the story here.
        if raw.startswith("![") and "](figures/" in raw:
            if pending_images:
                img_path = pending_images.pop(0)
                if img_path.exists():
                    im = Image(str(img_path))
                    im._restrictSize(5.5 * inch, 3.5 * inch)
                    im.hAlign = "CENTER"
                    story.append(im)
                    story.append(Spacer(1, 0.25 * inch))
            continue

        # Basic cleanup: drop markdown emphasis/backticks and convert to plain
        # ASCII so we don't get odd glyph boxes or stray "**" in the PDF.
        cleaned = raw.replace("`", "").replace("**", "")
        cleaned = cleaned.encode("ascii", "ignore").decode("ascii")

        if cleaned.startswith("# "):
            story.append(Paragraph(cleaned[2:].strip(), styles["Heading1"]))
        elif cleaned.startswith("## "):
            story.append(Paragraph(cleaned[3:].strip(), styles["Heading2"]))
        elif cleaned.startswith("### "):
            story.append(Paragraph(cleaned[4:].strip(), styles["Heading3"]))
        else:
            story.append(Paragraph(cleaned, styles["BodyText"]))
        story.append(Spacer(1, 0.18 * inch))

    return story


def _build_report_pdf(root: Path, subdir: str, pdf_filename: str, figure_names: list):
    """Build a report PDF from REPORT.md and figures in root / 'Q3 and 4' / subdir."""
    base = root / "Q3 and 4" / subdir
    md_path = base / "REPORT.md"
    pdf_path = base / pdf_filename
    images = [base / "figures" / name for name in figure_names]
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
    doc.build(_md_to_story(md_path, images))
    return pdf_path


def build_q3_pdf(root: Path, pdf_filename: str = "Q3_FlowImbalance_LongShort.pdf"):
    """Build Q3 PDF from Q3/REPORT.md and the Q3 figures."""
    return _build_report_pdf(root, "Q3", pdf_filename, ["q3_barplot.png", "q3_pnl.png"])


def build_q4_pdf(root: Path, pdf_filename: str = "Q4_Momentum_LongShort.pdf"):
    """Build Q4 PDF from Q4/REPORT.md and the Q4 figures."""
    return _build_report_pdf(root, "Q4", pdf_filename, ["q4_barplot.png", "q4_pnl.png"])

