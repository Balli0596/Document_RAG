
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from src.pdf_loader import (
    PDFLoadError,
    extract_pdf_pages,
    filter_page_text,
    is_excluded_heading,
    is_included_heading,
)


# --------------------------------------------------
# Test helpers
# --------------------------------------------------

def create_pdf(path: Path, pages: list[str]) -> Path:
    """Create a real PDF with extractable text on each page."""
    pdf = canvas.Canvas(str(path))

    for page_text in pages:
        y = 800

        for line in page_text.splitlines():
            pdf.drawString(50, y, line)
            y -= 20

        pdf.showPage()

    pdf.save()
    return path


def create_encrypted_pdf(path: Path) -> Path:
    """Create an encrypted PDF for testing."""
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.encrypt("test-password")

    with path.open("wb") as file:
        writer.write(file)

    return path


# --------------------------------------------------
# File validation tests
# --------------------------------------------------

def test_missing_pdf_raises_error(tmp_path):
    with pytest.raises(PDFLoadError, match="not found"):
        extract_pdf_pages(tmp_path / "missing.pdf")


def test_directory_path_raises_error(tmp_path):
    with pytest.raises(PDFLoadError, match="not a file"):
        extract_pdf_pages(tmp_path)


def test_non_pdf_file_raises_error(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("This is not a PDF.")

    with pytest.raises(PDFLoadError, match="Only PDF"):
        extract_pdf_pages(path)


def test_malformed_pdf_raises_error(tmp_path):
    path = tmp_path / "malformed.pdf"
    path.write_bytes(b"This is not a valid PDF document.")

    with pytest.raises(PDFLoadError, match="Could not read the PDF"):
        extract_pdf_pages(path)


# --------------------------------------------------
# PDF structure tests
# --------------------------------------------------

def test_empty_pdf_raises_error(tmp_path):
    path = tmp_path / "empty.pdf"

    writer = PdfWriter()
    with path.open("wb") as file:
        writer.write(file)

    with pytest.raises(PDFLoadError, match="no pages"):
        extract_pdf_pages(path)


def test_encrypted_pdf_raises_error(tmp_path):
    path = create_encrypted_pdf(tmp_path / "encrypted.pdf")

    with pytest.raises(PDFLoadError, match="encrypted"):
        extract_pdf_pages(path)


def test_pdf_with_no_extractable_text_raises_error(tmp_path):
    path = tmp_path / "image_only.pdf"

    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)

    with path.open("wb") as file:
        writer.write(file)

    with pytest.raises(PDFLoadError, match="No usable text"):
        extract_pdf_pages(path)


# --------------------------------------------------
# Successful extraction tests
# --------------------------------------------------

def test_extracts_text_from_valid_pdf(tmp_path):
    path = create_pdf(
        tmp_path / "sample.pdf",
        ["Introduction", "Machine learning uses data."],
    )

    pages = extract_pdf_pages(path)

    assert len(pages) == 1
    assert "Introduction" in pages[0]["text"]
    assert "Machine learning uses data." in pages[0]["text"]


def test_preserves_source_and_page_metadata(tmp_path):
    path = create_pdf(
        tmp_path / "sample.pdf",
        [
            "Introduction",
            "Methodology",
            "Conclusion",
        ],
    )

    pages = extract_pdf_pages(path)

    assert [page["metadata"]["page"] for page in pages] == [1, 2, 3]
    assert all(
        page["metadata"]["source"] == "sample.pdf"
        for page in pages
    )


def test_skips_blank_pages_and_preserves_original_page_numbers(tmp_path):
    path = create_pdf(
        tmp_path / "multi_page.pdf",
        [
            "Introduction",
            "",
            "Methodology",
        ],
    )

    pages = extract_pdf_pages(path)

    assert len(pages) == 2
    assert [page["metadata"]["page"] for page in pages] == [1, 3]


def test_accepts_uppercase_pdf_extension(tmp_path):
    path = create_pdf(
        tmp_path / "sample.PDF",
        ["Introduction", "Valid document content."],
    )

    pages = extract_pdf_pages(path)

    assert len(pages) == 1


# --------------------------------------------------
# Heading detection tests
# --------------------------------------------------

@pytest.mark.parametrize(
    "heading",
    [
        "Acknowledgement",
        "Acknowledgements",
        "Acknowledgment",
        "Acknowledgments",
        "Abstract",
        "Table of Contents",
        "Contents",
        "Author",
        "Authors",
        "Author Details",
        "Author Information",
        "List of Figures",
        "List of Tables",
        "List of Abbreviations",
        "Declaration",
        "Certificate",
        "Copyright",
    ],
)
def test_recognizes_excluded_headings(heading):
    assert is_excluded_heading(heading)


@pytest.mark.parametrize(
    "heading",
    [
        "1. Introduction",
        "Background",
        "Methodology",
        "Methods",
        "Proposed Methodology",
        "System Design",
        "Implementation",
        "Results",
        "Discussion",
        "Conclusion",
        "Conclusions",
        "References",
        "Bibliography",
    ],
)
def test_recognizes_included_headings(heading):
    assert is_included_heading(heading)


# --------------------------------------------------
# Section filtering tests
# --------------------------------------------------

def test_removes_acknowledgement_section():
    text = """
Acknowledgement
Thanks to my teachers and family.
Their support was valuable.
Introduction
This research explores machine learning.
"""

    filtered, skipping = filter_page_text(text)

    assert "Acknowledgement" not in filtered
    assert "teachers and family" not in filtered
    assert "Introduction" in filtered
    assert "research explores machine learning" in filtered
    assert skipping is False


def test_removes_abstract_section():
    text = """
Abstract
This paper studies artificial intelligence.
The findings show improved accuracy.
1. Introduction
The project develops a retrieval system.
"""

    filtered, skipping = filter_page_text(text)

    assert "This paper studies" not in filtered
    assert "improved accuracy" not in filtered
    assert "The project develops" in filtered
    assert skipping is False


def test_removes_table_of_contents():
    text = """
Table of Contents
Introduction ........ 1
Methodology ........ 5
Results ............ 10
Introduction
The actual introduction begins here.
"""

    filtered, skipping = filter_page_text(text)

    assert "Methodology ........ 5" not in filtered
    assert "Results ............ 10" not in filtered
    assert "actual introduction begins here" in filtered
    assert skipping is False


def test_keeps_normal_content_without_excluded_sections():
    text = """
Introduction
This is the introduction.
Methodology
This is the methodology.
"""

    filtered, skipping = filter_page_text(text)

    assert "This is the introduction." in filtered
    assert "This is the methodology." in filtered
    assert skipping is False


def test_excluded_section_continues_across_pages():
    page_one = """
Acknowledgement
Thanks to all contributors.
More acknowledgement text.
"""

    page_two = """
Additional acknowledgement text.
Introduction
The main research begins here.
"""

    filtered_one, skipping = filter_page_text(page_one)
    filtered_two, skipping = filter_page_text(
        page_two,
        skip_section=skipping,
    )

    assert "Thanks to all contributors" not in filtered_one
    assert "Additional acknowledgement" not in filtered_two
    assert "The main research begins here" in filtered_two
    assert skipping is False


def test_excluded_heading_at_end_of_page_keeps_skip_state():
    text = """
Introduction
Useful research content.
Abstract
"""

    filtered, skipping = filter_page_text(text)

    assert "Useful research content" in filtered
    assert "Abstract" not in filtered
    assert skipping is True


def test_document_with_only_excluded_sections_raises_error(tmp_path):
    path = create_pdf(
        tmp_path / "front_matter.pdf",
        [
            "Acknowledgement\nThanks to everyone.",
            "Abstract\nThis document discusses AI.",
        ],
    )

    with pytest.raises(PDFLoadError, match="No usable text"):
        extract_pdf_pages(path)


def test_extraction_filters_front_matter_from_pdf(tmp_path):
    path = create_pdf(
        tmp_path / "research.pdf",
        [
            "Acknowledgement\nThanks to my guide.",
            "Abstract\nThis paper discusses RAG.",
            "1. Introduction\nRAG retrieves relevant document chunks.",
        ],
    )

    pages = extract_pdf_pages(path)

    combined_text = "\n".join(page["text"] for page in pages)

    assert "Thanks to my guide" not in combined_text
    assert "This paper discusses RAG" not in combined_text
    assert "RAG retrieves relevant document chunks" in combined_text
    assert pages[-1]["metadata"]["page"] == 3
