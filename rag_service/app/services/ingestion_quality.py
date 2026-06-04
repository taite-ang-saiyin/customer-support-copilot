import re
from typing import Any


def analyze_ingestion_quality(
    original_file_name: str,
    cleaned_markdown: str,
    chunks: list[dict[str, Any]] | None = None,
    page_count: int | None = None,
) -> dict[str, Any]:
    chunks = chunks or []
    character_count = len(cleaned_markdown)
    words = re.findall(r"\b\w+\b", cleaned_markdown)
    word_count = len(words)
    heading_count = len(re.findall(r"^#{1,6}\s+", cleaned_markdown, flags=re.MULTILINE))
    chunk_word_counts = [_chunk_word_count(chunk) for chunk in chunks]
    chunk_count = len(chunks)
    average_chunk_words = (
        round(sum(chunk_word_counts) / chunk_count, 2)
        if chunk_count
        else 0
    )
    chunks_missing_citation = [
        index for index, chunk in enumerate(chunks) if _missing_citation(chunk)
    ]
    oversized_chunks = [
        index for index, count in enumerate(chunk_word_counts) if count > 500
    ]
    tiny_chunks = [
        index for index, count in enumerate(chunk_word_counts) if 0 < count < 20
    ]

    warnings = _build_warnings(
        word_count=word_count,
        character_count=character_count,
        heading_count=heading_count,
        chunk_count=chunk_count,
        chunks_missing_citation=chunks_missing_citation,
        oversized_chunks=oversized_chunks,
        tiny_chunks=tiny_chunks,
        page_count=page_count,
    )

    return {
        "file_name": original_file_name,
        "page_count": page_count,
        "character_count": character_count,
        "word_count": word_count,
        "heading_count": heading_count,
        "chunk_count": chunk_count,
        "average_chunk_words": average_chunk_words,
        "chunks_missing_citation": chunks_missing_citation,
        "oversized_chunks": oversized_chunks,
        "tiny_chunks": tiny_chunks,
        "warnings": warnings,
    }


def _chunk_word_count(chunk: dict[str, Any]) -> int:
    text = str(chunk.get("text") or chunk.get("chunk_text") or "")
    return len(re.findall(r"\b\w+\b", text))


def _missing_citation(chunk: dict[str, Any]) -> bool:
    citation = chunk.get("citation")
    section = chunk.get("section") or chunk.get("section_title")
    source = chunk.get("source") or chunk.get("doc_title") or chunk.get("title")
    return not citation and (not section or section == "Overview") and not source


def _build_warnings(
    word_count: int,
    character_count: int,
    heading_count: int,
    chunk_count: int,
    chunks_missing_citation: list[int],
    oversized_chunks: list[int],
    tiny_chunks: list[int],
    page_count: int | None,
) -> list[str]:
    warnings: list[str] = []

    if word_count < 80 or character_count < 500:
        warnings.append("low extracted text")
    if page_count and page_count > 0 and character_count / page_count < 100:
        warnings.append("possible scanned PDF")
    if heading_count == 0:
        warnings.append("no headings detected")
    if chunk_count < 2:
        warnings.append("too few chunks")
    if tiny_chunks and (len(tiny_chunks) >= 5 or len(tiny_chunks) >= max(1, chunk_count // 2)):
        warnings.append("too many tiny chunks")
    if oversized_chunks:
        warnings.append("oversized chunks")
    if chunks_missing_citation:
        warnings.append("missing citations")

    return warnings
