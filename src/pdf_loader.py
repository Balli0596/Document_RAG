
from pathlib import Path
from pypdf import PdfReader


class PDFLoadError(Exception):
    """Raised when a PDF cannot be loaded or read."""


def extract_pdf_pages(file_path: str | Path) -> list[dict]:
    """
    Extract text from a PDF while preserving page numbers.

    Returns:
        A list of dictionaries containing page text and metadata.
        Page numbers are 1-based for user-friendly citations.
    """
    path = Path(file_path)

    if not path.exists():
        raise PDFLoadError(f"PDF file not found: {path}")

    if not path.is_file():
        raise PDFLoadError("The supplied path is not a file.")

    if path.suffix.lower() != ".pdf":
        raise PDFLoadError("Only PDF files are supported.")

    try:
        reader = PdfReader(str(path))

        if reader.is_encrypted:
            raise PDFLoadError(
                "The PDF is encrypted. Please upload an accessible PDF."
            )

        if len(reader.pages) == 0:
            raise PDFLoadError("The PDF contains no pages.")

        extracted_pages = []

        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()

            if not text:
                continue

            extracted_pages.append(
                {
                    "text": text,
                    "metadata": {
                        "source": path.name,
                        "page": page_number,
                    },
                }
            )

        if not extracted_pages:
            raise PDFLoadError(
                "No extractable text was found. "
                "The PDF may be scanned or image-only; OCR may be needed."
            )

        return extracted_pages

    except PDFLoadError:
        raise
    except Exception as exc:
        raise PDFLoadError(
            f"Could not read the PDF: {exc}"
        ) from exc
