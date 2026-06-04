import re
from dataclasses import dataclass

from app.services.markdown_cleaner import clean_text


@dataclass(frozen=True)
class TextChunk:
    text: str
    section_title: str
    chunk_index: int


def chunk_markdown(text: str, max_chars: int = 1800) -> list[TextChunk]:
    cleaned = clean_text(text)
    sections = _split_markdown_sections(cleaned)
    chunks: list[TextChunk] = []

    for section_title, section_text in sections:
        for part in _split_long_section(section_text, max_chars=max_chars):
            if part.strip():
                chunks.append(
                    TextChunk(
                        text=part.strip(),
                        section_title=section_title or "Overview",
                        chunk_index=len(chunks),
                    )
                )

    if not chunks and cleaned:
        chunks.append(TextChunk(text=cleaned, section_title="Overview", chunk_index=0))

    return chunks


def _split_markdown_sections(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_title = "Overview"
    current_lines: list[str] = []

    for line in lines:
        heading = re.match(r"^(#{1,3})\s+(.+?)\s*$", line)
        if heading:
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = heading.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_lines))

    return [(title, "\n".join(section_lines).strip()) for title, section_lines in sections]


def _split_long_section(section_text: str, max_chars: int) -> list[str]:
    if len(section_text) <= max_chars:
        return [section_text]

    paragraphs = [paragraph.strip() for paragraph in section_text.split("\n\n") if paragraph.strip()]
    parts: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            parts.append(current)
        if len(paragraph) <= max_chars:
            current = paragraph
        else:
            parts.extend(_split_by_sentence(paragraph, max_chars=max_chars))
            current = ""

    if current:
        parts.append(current)

    return parts


def _split_by_sentence(text: str, max_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    parts: list[str] = []
    current = ""

    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                parts.append(current)
            current = sentence

    if current:
        parts.append(current)

    return parts
