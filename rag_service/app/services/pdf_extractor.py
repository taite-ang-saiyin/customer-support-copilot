from pathlib import Path
from typing import Literal

from app.services.markdown_cleaner import clean_pdf_pages_to_markdown

PdfExtractionMode = Literal["text", "blocks"]


def extract_pdf_pages(file_path: str, mode: PdfExtractionMode = "text") -> list[str]:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError(
            "PDF extraction requires PyMuPDF. Install it with `pip install pymupdf`."
        ) from exc

    pages: list[str] = []
    with fitz.open(file_path) as document:
        for page in document:
            if mode == "blocks":
                pages.append(_extract_page_blocks(page))
            else:
                pages.append(page.get_text("text"))
    return pages


def extract_pdf_to_markdown(file_path: str, mode: PdfExtractionMode = "blocks") -> str:
    pages = extract_pdf_pages(file_path, mode=mode)
    return clean_pdf_pages_to_markdown(pages, default_title=Path(file_path).stem)


def count_pdf_pages(file_path: str) -> int:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError(
            "PDF page counting requires PyMuPDF. Install it with `pip install pymupdf`."
        ) from exc

    with fitz.open(file_path) as document:
        return int(document.page_count)


def _extract_page_blocks(page: object) -> str:
    blocks = page.get_text("blocks")
    text_blocks = []
    for block in blocks:
        x0, y0, _x1, _y1, text, *_rest = block
        cleaned = str(text).strip()
        if cleaned:
            text_blocks.append((float(y0), float(x0), cleaned))

    text_blocks.sort(key=lambda item: (item[0], item[1]))
    return "\n".join(text for _y0, _x0, text in text_blocks)
