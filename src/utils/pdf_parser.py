"""PDF parsing utilities."""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import pdfplumber

from src.utils.logger import logger


@dataclass
class PDFMetadata:
    """PDF document metadata."""
    filename: str
    pages: int
    file_size: int
    title: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[str] = None


@dataclass
class PDFContent:
    """Parsed PDF content."""
    text: str
    metadata: PDFMetadata
    page_texts: list[str]


class PDFParser:
    """PDF text extraction using pdfplumber."""

    def __init__(self, max_pages: int = 120):
        """Initialize PDF parser.

        Args:
            max_pages: Maximum number of pages to parse
        """
        self.max_pages = max_pages

    def extract_text(self, file_path: str | Path) -> str:
        """Extract text from PDF file.

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text content

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid PDF
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        if file_path.suffix.lower() != ".pdf":
            raise ValueError(f"Not a PDF file: {file_path}")

        text_parts = []

        try:
            with pdfplumber.open(file_path) as pdf:
                pages_to_process = min(len(pdf.pages), self.max_pages)

                logger.info(f"Parsing PDF: {file_path.name} ({pages_to_process} pages)")

                for i, page in enumerate(pdf.pages[:pages_to_process]):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

                    if (i + 1) % 20 == 0:
                        logger.debug(f"Parsed {i + 1}/{pages_to_process} pages")

            logger.info(f"PDF parsing complete: {len(text_parts)} pages extracted")
            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
            raise

    def get_metadata(self, file_path: str | Path) -> PDFMetadata:
        """Get PDF metadata.

        Args:
            file_path: Path to PDF file

        Returns:
            PDF metadata
        """
        file_path = Path(file_path)

        with pdfplumber.open(file_path) as pdf:
            info = pdf.metadata or {}

            return PDFMetadata(
                filename=file_path.name,
                pages=len(pdf.pages),
                file_size=file_path.stat().st_size,
                title=info.get("Title"),
                author=info.get("Author"),
                creation_date=info.get("CreationDate")
            )

    def parse(self, file_path: str | Path) -> PDFContent:
        """Parse PDF and return content with metadata.

        Args:
            file_path: Path to PDF file

        Returns:
            PDFContent with text and metadata
        """
        file_path = Path(file_path)

        page_texts = []

        with pdfplumber.open(file_path) as pdf:
            info = pdf.metadata or {}
            pages_to_process = min(len(pdf.pages), self.max_pages)

            for page in pdf.pages[:pages_to_process]:
                page_text = page.extract_text()
                if page_text:
                    page_texts.append(page_text)

            metadata = PDFMetadata(
                filename=file_path.name,
                pages=len(pdf.pages),
                file_size=file_path.stat().st_size,
                title=info.get("Title"),
                author=info.get("Author"),
                creation_date=info.get("CreationDate")
            )

        return PDFContent(
            text="\n\n".join(page_texts),
            metadata=metadata,
            page_texts=page_texts
        )


# Default parser instance
pdf_parser = PDFParser()
