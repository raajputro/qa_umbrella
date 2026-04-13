import os
from pathlib import Path
from typing import Optional


def load_requirement_text(file_path: str) -> str:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Requirement file not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix in [".txt", ".md"]:
        return _load_text_file(path)

    elif suffix == ".docx":
        return _load_docx_file(path)

    elif suffix == ".pdf":
        return _load_pdf_file(path)

    else:
        raise ValueError(f"Unsupported file type: {suffix}")


# --------------------------
# TXT / MD
# --------------------------
def _load_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


# --------------------------
# DOCX
# --------------------------
def _load_docx_file(path: Path) -> str:
    try:
        from docx import Document
    except ImportError:
        raise ImportError("Please install python-docx: pip install python-docx")

    doc = Document(path) # type: ignore
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    return "\n".join(paragraphs)


# --------------------------
# PDF
# --------------------------
def _load_pdf_file(path: Path) -> str:
    text = _try_pypdf(path)

    if not text or len(text.strip()) < 50:
        # fallback to pdfplumber if text is poor
        text = _try_pdfplumber(path)

    return text.strip() # type: ignore


def _try_pypdf(path: Path) -> Optional[str]:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("Please install pypdf: pip install pypdf")

    try:
        reader = PdfReader(str(path))
        texts = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                texts.append(page_text.strip())

        return "\n".join(texts)

    except Exception as e:
        print(f"[WARN] pypdf failed: {e}")
        return None


def _try_pdfplumber(path: Path) -> Optional[str]:
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("Please install pdfplumber: pip install pdfplumber")

    try:
        texts = []

        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    texts.append(page_text.strip())

        return "\n".join(texts)

    except Exception as e:
        print(f"[WARN] pdfplumber failed: {e}")
        return None