from app.services.ingestion_quality import analyze_ingestion_quality


def test_low_text_warning() -> None:
    report = analyze_ingestion_quality(
        original_file_name="empty_policy.pdf",
        cleaned_markdown="Tiny text",
        chunks=[],
        page_count=3,
    )

    assert "low extracted text" in report["warnings"]
    assert "possible scanned PDF" in report["warnings"]


def test_no_headings_warning() -> None:
    report = analyze_ingestion_quality(
        original_file_name="policy.pdf",
        cleaned_markdown="This document has enough words but no markdown headings. " * 20,
        chunks=[{"text": "This is a normal chunk with enough words to avoid tiny warning.", "section": "Overview"}],
    )

    assert "no headings detected" in report["warnings"]


def test_missing_citation_warning() -> None:
    report = analyze_ingestion_quality(
        original_file_name="policy.md",
        cleaned_markdown="# Policy\n\n## Duplicate Charges\n\nUseful content.",
        chunks=[{"text": "Useful chunk without citation metadata."}],
    )

    assert report["chunks_missing_citation"] == [0]
    assert "missing citations" in report["warnings"]


def test_tiny_chunk_warning() -> None:
    report = analyze_ingestion_quality(
        original_file_name="faq.md",
        cleaned_markdown="# FAQ\n\n## Short Items\n\nA lot of short chunks.",
        chunks=[
            {"text": "Tiny", "section": "Short Items"},
            {"text": "Small", "section": "Short Items"},
            {"text": "Brief", "section": "Short Items"},
            {"text": "Mini", "section": "Short Items"},
            {"text": "Short", "section": "Short Items"},
        ],
    )

    assert "too many tiny chunks" in report["warnings"]


def test_oversized_chunk_warning() -> None:
    report = analyze_ingestion_quality(
        original_file_name="contract.md",
        cleaned_markdown="# Contract\n\n## Terms\n\n" + ("word " * 700),
        chunks=[{"text": "word " * 700, "section": "Terms"}],
    )

    assert report["oversized_chunks"] == [0]
    assert "oversized chunks" in report["warnings"]
