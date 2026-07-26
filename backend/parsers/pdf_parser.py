"""
parsers/pdf_parser.py — Extract text from PDF files.
Tries pypdf first, falls back to pdfplumber for complex layouts.
"""
from pathlib import Path


def parse_pdf(file_path: str) -> str:
    """Return full text content of a PDF file."""
    path = Path(file_path)
    text = _try_pypdf(path)
    if not text or len(text.strip()) < 50:
        text = _try_pdfplumber(path)
    return text or ""


def _try_pypdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        pages = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(f"[Page {i+1}]\n{page_text}")
        return "\n\n".join(pages)
    except Exception:
        return ""


def _try_pdfplumber(path: Path) -> str:
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(str(path)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages.append(f"[Page {i+1}]\n{page_text}")
        return "\n\n".join(pages)
    except Exception:
        return ""
