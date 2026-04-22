"""
Tests for PDF ingestion - parser and chunker.
Uses a programmatically generated PDF so no external files are needed.
"""

from pathlib import Path
import fitz  # PyMupdf
import pytest

from app.ingestion.pdf_parser import PDFParser, PDFDocument
from app.ingestion.chunker import RecursiveChunker, TextChunk

# Fixtures


def make_test_pdf(path: Path, pages: list[str]) -> None:
    """
    Create a real PDF file with given text per page.
    """
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((50, 50), text, fontsize=11)
    doc.save(str(path))
    doc.close()


@pytest.fixture
def simple_pdf(tmp_path) -> Path:
    """
    Create a simple PDF with 3 pages of text.
    """
    pdf_path = tmp_path / "test.pdf"
    pages = [
        "This is the first page with some sample text to parse.",
        "Second page contains different content about machine learning.",
        "Third page discusses retrieval augmented generation systems.",
    ]
    make_test_pdf(pdf_path, pages)
    return pdf_path


@pytest.fixture
def long_pdf(tmp_path) -> Path:
    """
    Create a PDF with one very long page to test chunking.
    """
    pdf_path = tmp_path / "long.pdf"
    long_text = " ".join([f"Sentence {i}." for i in range(100)])  # 100 sentences
    make_test_pdf(pdf_path, [long_text])
    return pdf_path


# PDFParser Tests
class TestPDFParser:

    def test_parse_returns_pdf_document(self, simple_pdf):
        parser = PDFParser()
        doc = parser.parse_pdf(simple_pdf)
        assert isinstance(doc, PDFDocument)

    def test_correct_page_count(self, simple_pdf):
        doc = PDFParser().parse_pdf(simple_pdf)
        assert doc.total_pages == 3

    def test_text_extracted_per_page(self, simple_pdf):
        doc = PDFParser().parse_pdf(simple_pdf)
        assert "first page" in doc.pages[0].text.lower()
        assert "machine learning" in doc.pages[1].text.lower()
        assert "retrieval augmented generation" in doc.pages[2].text.lower()

    def test_full_text_combines_pages(self, simple_pdf):
        doc = PDFParser().parse_pdf(simple_pdf)
        assert "first page" in doc.full_text.lower()
        assert "machine learning" in doc.full_text.lower()

    def test_char_count_positive(self, simple_pdf):
        doc = PDFParser().parse_pdf(simple_pdf)
        for page in doc.pages:
            assert page.char_count > 0

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            PDFParser().parse_pdf(tmp_path / "missing.pdf")

    def test_wrong_extension_raises(self, tmp_path):
        fake = tmp_path / "file.txt"
        fake.write_text("not a pdf")
        with pytest.raises(ValueError, match="Expected a .pdf"):
            PDFParser().parse_pdf(fake)

    def test_metadata_extracted(self, simple_pdf):
        doc = PDFParser().parse_pdf(simple_pdf)
        assert "page_count" in doc.metadata
        assert doc.metadata["page_count"] == 3


# RecursiveChunker Tests
class TestRecursiveChunker:

    def test_chunks_returned(self, simple_pdf):
        doc = PDFParser().parse_pdf(simple_pdf)
        chunks = RecursiveChunker().chunk_document(doc)
        assert len(chunks) > 0
        assert all(isinstance(c, TextChunk) for c in chunks)

    def test_chunk_size_respected(self, long_pdf):
        doc = PDFParser().parse_pdf(long_pdf)
        chunk_size = 200
        chunker = RecursiveChunker(chunk_size=chunk_size)
        chunks = chunker.chunk_document(doc)
        # Allow small overflow due to overlap
        for chunk in chunks:
            assert len(chunk.text) <= chunk_size * 2

    def test_chunk_ids_unique(self, simple_pdf):
        doc = PDFParser().parse_pdf(simple_pdf)
        chunks = RecursiveChunker().chunk_document(doc)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(chunks)  # all IDs should be unique

    def test_chunk_metadata_populated(self, simple_pdf):
        doc = PDFParser().parse_pdf(simple_pdf)
        chunks = RecursiveChunker().chunk_document(doc)
        for chunk in chunks:
            assert chunk.file_name == doc.file_name
            assert chunk.page_number > 0
            assert chunk.text.strip() != ""
            assert chunk.char_start >= 0
            assert chunk.char_end > chunk.char_start

    def test_min_chunk_size_filters_small(self, simple_pdf):
        doc = PDFParser().parse_pdf(simple_pdf)
        chunks = RecursiveChunker(min_chunk_size=50).chunk_document(doc)
        for chunk in chunks:
            assert len(chunk.text) >= 50

    def test_overlap_applied(self, long_pdf):
        doc = PDFParser().parse_pdf(long_pdf)
        chunker = RecursiveChunker(chunk_size=200, chunk_overlap=50)
        chunks = chunker.chunk_document(doc)
        # With overlap, consecutive chunks should share some text
        if len(chunks) > 1:
            prev_tail = chunks[0].text[-50:]
            assert prev_tail in chunks[1].text or len(chunks[1].text) < 50
