from app.services.text_processing import chunk_markdown, clean_pdf_pages_to_markdown, clean_text


def test_clean_text_normalizes_spacing() -> None:
    raw = "Title\r\n\r\n\r\nLine   with\tspaces"

    assert clean_text(raw) == "Title\n\nLine with spaces"


def test_chunk_markdown_uses_section_titles() -> None:
    text = """# Refund Policy

## Duplicate Charges

A duplicate charge occurs when the same workspace is billed twice.

## Processing Time

Approved refunds are submitted within 2 business days.
"""

    chunks = chunk_markdown(text)

    assert [chunk.section_title for chunk in chunks] == [
        "Refund Policy",
        "Duplicate Charges",
        "Processing Time",
    ]
    assert "duplicate charge" in chunks[1].text.lower()


def test_chunk_markdown_splits_long_sections() -> None:
    text = "# Long Doc\n\n## Details\n\n" + ("Sentence about billing. " * 200)

    chunks = chunk_markdown(text, max_chars=500)

    assert len(chunks) > 1
    assert all(chunk.section_title in {"Long Doc", "Details"} for chunk in chunks)


def test_clean_pdf_pages_to_markdown_removes_noise_and_adds_headings() -> None:
    pages = [
        """CloudDesk Internal
Page 1 of 2
Refund Policy
Duplicate Charges
A duplicate charge occurs when the same
workspace is billed twice.
CloudDesk Internal""",
        """CloudDesk Internal
Page 2 of 2
Refund Processing Time
Approved refunds are submitted within
2 business days.
CloudDesk Internal""",
    ]

    markdown = clean_pdf_pages_to_markdown(pages)

    assert "# Refund Policy" in markdown
    assert "## Duplicate Charges" in markdown
    assert "same workspace is billed twice" in markdown
    assert "## Refund Processing Time" in markdown
    assert "Page 1 of 2" not in markdown
    assert "CloudDesk Internal" not in markdown
