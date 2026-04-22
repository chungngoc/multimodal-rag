"""
PDF parser - extracts text, metadata, and page info from PDF files.
Uses PyMupdf (fitz) for PDF processing.
"""

from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMupdf
from loguru import logger


@dataclass
class PageContent:
    """
    Represents the extracted content of a single page in a PDF
    """

    page_number: int
    text: str  # raw extracted text
    char_count: int  # number of characters in the text
    has_images: bool  # whether the page contains images
    has_tables: bool  # whether the page contains tables (basic heuristic)


@dataclass
class PDFDocument:
    """
    Represents a fully parsed PDF document.
    """

    file_path: str
    file_name: str
    total_pages: int
    pages: list[PageContent] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text.strip())

    @property
    def total_chars(self) -> int:
        return sum(p.char_count for p in self.pages)


class PDFParser:
    """
    Extracts text content from PDF files using PyMuPDF.
    Images and tables are detected but extracted later
    """

    # Heuristic: if a page has many tab/pipe characters, it likely has a table
    TABLE_HEURISTIC_CHARS = {"|", "\t"}
    TABLE_HEURISTIC_THRESHOLD = 5

    def parse_pdf(self, file_path: str | Path) -> PDFDocument:
        """
        Parse a PDF file and return a PDFDocument.
        Args:
            file_path: Path to the PDF file to parse.
        Returns:
            PDFDocument containing extracted text, metadata, and page info.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")
        if file_path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a .pdf file, got: {file_path.suffix}")

        logger.info(f"Parsing PDF: {file_path.name}")

        try:
            doc = fitz.open(str(file_path))
        except Exception as e:
            raise ValueError(f"Could not open PDF: {e}")

        metadata = self._extract_metadata(doc)
        pages = self._extract_pages(doc)
        doc.close()

        pdf_doc = PDFDocument(
            file_path=str(file_path),
            file_name=file_path.name,
            total_pages=len(pages),
            pages=pages,
            metadata=metadata,
        )

        logger.info(
            f"Parsed '{file_path.name}' — "
            f"{pdf_doc.total_pages} pages, "
            f"{pdf_doc.total_chars:,} chars"
        )

        return pdf_doc

    def _extract_metadata(self, doc: fitz.Document) -> dict:
        """
        Extract metadata from the PDF document.
        """
        meta = doc.metadata or {}
        return {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "subject": meta.get("subject", ""),
            "creator": meta.get("creator", ""),
            "page_count": doc.page_count,
        }

    def _extract_pages(self, doc: fitz.Document) -> list[PageContent]:
        """
        Extract text from every page.
        """
        pages = []

        for i, page in enumerate(doc):
            text = page.get_text("text")  # plain text extraction
            text = self._clean_text(text)

            has_images = len(page.get_images()) > 0
            has_tables = self._detect_table_heuristic(text)

            pages.append(
                PageContent(
                    page_number=i + 1,
                    text=text,
                    char_count=len(text),
                    has_images=has_images,
                    has_tables=has_tables,
                )
            )

        return pages

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text by normalizing whitespace.
        """
        lines = text.splitlines()
        cleaned = [line.strip() for line in lines if line.strip()]
        # Collapse multiple blank lines into one
        result, prev_blank = [], False
        for line in cleaned:
            is_blank = line == ""
            if is_blank and prev_blank:
                continue
            result.append(line)
            prev_blank = is_blank
        return "\n".join(result).strip()

    def _detect_table_heuristic(self, text: str) -> bool:
        """
        Simple heuristic to detect if a page likely contains a table.
        Checks for presence of multiple '|' or tab characters.
        """
        count = sum(text.count(c) for c in self.TABLE_HEURISTIC_CHARS)
        return count >= self.TABLE_HEURISTIC_THRESHOLD
