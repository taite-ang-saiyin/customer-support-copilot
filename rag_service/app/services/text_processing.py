from pathlib import Path

from app.services.chunker import TextChunk, chunk_markdown
from app.services.markdown_cleaner import clean_pdf_pages_to_markdown, clean_text
from app.services.pdf_extractor import extract_pdf_to_markdown

SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt", ".pdf"}


def extract_text(file_path: str) -> str:
    extension = Path(file_path).suffix.lower()
    if extension == ".pdf":
        return extract_pdf_to_markdown(file_path)

    with open(file_path, encoding="utf-8") as file:
        return file.read()


__all__ = [
    "SUPPORTED_EXTENSIONS",
    "TextChunk",
    "chunk_markdown",
    "clean_pdf_pages_to_markdown",
    "clean_text",
    "extract_pdf_to_markdown",
    "extract_text",
]
