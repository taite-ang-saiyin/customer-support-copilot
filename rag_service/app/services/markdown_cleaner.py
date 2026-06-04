import re


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_pdf_pages_to_markdown(pages: list[str], default_title: str = "Document") -> str:
    filtered_pages = [_filter_pdf_noise(page, pages) for page in pages]
    lines: list[str] = []
    for page in filtered_pages:
        lines.extend(page)
        lines.append("")

    markdown_lines = _lines_to_markdown(lines, default_title=default_title)
    return clean_text("\n".join(markdown_lines))


def _filter_pdf_noise(page_text: str, all_pages: list[str]) -> list[str]:
    repeated_edge_lines = _repeated_pdf_edge_lines(all_pages)
    filtered: list[str] = []

    for raw_line in page_text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            filtered.append("")
            continue
        normalized = _normalize_noise_line(line)
        if normalized in repeated_edge_lines:
            continue
        if _is_page_number(line):
            continue
        filtered.append(line)

    return filtered


def _repeated_pdf_edge_lines(pages: list[str]) -> set[str]:
    counts: dict[str, int] = {}
    for page in pages:
        page_lines = [
            _normalize_noise_line(line)
            for line in page.splitlines()
            if _normalize_noise_line(line)
        ]
        edge_lines = page_lines[:2] + page_lines[-2:]
        for line in edge_lines:
            counts[line] = counts.get(line, 0) + 1

    minimum_repeats = max(2, len(pages) // 2)
    return {line for line, count in counts.items() if count >= minimum_repeats}


def _lines_to_markdown(lines: list[str], default_title: str) -> list[str]:
    markdown: list[str] = []
    paragraph: list[str] = []
    has_title = False

    def flush_paragraph() -> None:
        if paragraph:
            markdown.append(" ".join(paragraph).strip())
            markdown.append("")
            paragraph.clear()

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            continue

        if _is_heading_candidate(line):
            flush_paragraph()
            heading_text = _normalize_heading(line)
            heading_level = "#" if not has_title else "##"
            markdown.append(f"{heading_level} {heading_text}")
            markdown.append("")
            has_title = True
            continue

        if _is_bullet_line(line):
            flush_paragraph()
            markdown.append(_normalize_bullet(line))
            continue

        paragraph.append(line)

    flush_paragraph()

    if not has_title:
        title = _normalize_heading(default_title.replace("_", " ").replace("-", " "))
        markdown.insert(0, "")
        markdown.insert(0, f"# {title}")

    return markdown


def _is_heading_candidate(line: str) -> bool:
    if len(line) > 90:
        return False
    if _is_bullet_line(line) or _is_page_number(line):
        return False
    if re.search(r"[.!?]$", line):
        return False
    if _looks_like_error_code_line(line):
        return False
    if re.match(r"^\d+(\.\d+)*\.?\s+[A-Z][A-Za-z0-9 /&(),:-]+$", line):
        return True
    if line.isupper() and len(line.split()) <= 10:
        return True
    if _looks_like_title_case_heading(line):
        return True
    return False


def _looks_like_error_code_line(line: str) -> bool:
    return bool(re.search(r"\b[A-Z]{2,}-[A-Z0-9-]+\b", line)) and len(line.split()) <= 3


def _looks_like_title_case_heading(line: str) -> bool:
    words = [word.strip(":/&(),-") for word in line.split()]
    words = [word for word in words if word]
    if not words or len(words) > 8:
        return False

    small_words = {"and", "or", "of", "to", "for", "in", "on", "with", "the", "a", "an"}
    title_like_words = 0
    for index, word in enumerate(words):
        if index > 0 and word.lower() in small_words:
            title_like_words += 1
        elif word[:1].isupper():
            title_like_words += 1

    return title_like_words / len(words) >= 0.75


def _is_bullet_line(line: str) -> bool:
    symbolic_bullet = line.startswith("- ") or line.startswith("* ") or line.startswith(chr(8226) + " ")
    numbered_bullet = bool(re.match(r"^\d+[.)]\s+", line))
    return symbolic_bullet or numbered_bullet


def _normalize_bullet(line: str) -> str:
    if line.startswith("* ") or line.startswith(chr(8226) + " "):
        return "- " + line[2:].strip()
    return line


def _normalize_heading(line: str) -> str:
    line = re.sub(r"^\d+(\.\d+)*\.?\s+", "", line)
    line = line.strip(" :-")
    return line[:1].upper() + line[1:]


def _normalize_noise_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip().lower()


def _is_page_number(line: str) -> bool:
    patterns = [
        r"^page\s+\d+(\s+of\s+\d+)?$",
        r"^\d+\s*/\s*\d+$",
        r"^-?\s*\d+\s*-?$",
    ]
    return any(re.match(pattern, line, flags=re.IGNORECASE) for pattern in patterns)
