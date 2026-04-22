"""
Chunker - splits extracted PDF text into overlapping chunks for retrieval and embedding.

Strategy: Recursive character splitting with overlap.
- Tries to split on paragraphs first (\n\n)
- Falls back to sentences, then words
- Preserves page number metadata on every chunk.
"""

from dataclasses import dataclass
from loguru import logger
from app.ingestion.pdf_parser import PDFDocument, PageContent


@dataclass
class TextChunk:
    """
    A single retrievable chunk of text with source matedata.
    """

    chunk_id: str  # unique id: "{filename}_p{page}_{chunk_index}"
    text: str  # chunk content
    page_number: int  # source page number
    char_start: int  # start position within page text
    char_end: int  # end position within page text
    file_name: str  # source PDF filename
    has_images: bool  # whether the source page has images
    has_tables: bool  # whether the source page has tables
    chunk_index: int  # index within the document


class RecursiveChunker:
    """
    Splits PDF pages into overlapping text chunks.
    Args:
        chunk_size: Maximum number of characters in a chunk.
        chunk_overlap: Number of characters to overlap between chunks.
        min_chunk_size: Discard chunks smaller than this size.
    """

    # Split priority: paragraph -> newline -> sentence -> space
    SEPARATORS = ["\n\n", "\n", ". ", " "]

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        min_chunk_size: int = 50,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_document(self, doc: PDFDocument) -> list[TextChunk]:
        """
        Chunk all pages of a PDFDocument.
        Args:
            doc: PDFDocument to chunk.
        Returns:
            List of TextChunk objects across all pages.
        """
        all_chunks: list[TextChunk] = []
        chunk_index = 0

        for page in doc.pages:
            if not page.text.strip():
                logger.debug(f"Skipping empty page {page.page_number}")
                continue
            page_chunks = self._chunk_page(page, doc.file_name, chunk_index)
            all_chunks.extend(page_chunks)
            chunk_index += len(page_chunks)

        logger.info(
            f"Chunked '{doc.file_name}' → "
            f"{len(all_chunks)} chunks "
            f"(size={self.chunk_size}, overlap={self.chunk_overlap})"
        )

        return all_chunks

    def _chunk_page(
        self, page: PageContent, file_name: str, start_index: int
    ) -> list[TextChunk]:
        """Split a single page into chunks."""
        raw_chunks = self._recursive_split(page.text, self.chunk_size)
        chunks = []

        # Build overlapping windows
        char_cursor = 0
        for i, text in enumerate(raw_chunks):
            if len(text) < self.min_chunk_size:
                continue  # skip tiny chunks

            char_start = page.text.find(text, max(0, char_cursor - 20))
            char_end = char_start + len(text)
            char_cursor = char_end

            chunk = TextChunk(
                chunk_id=f"{file_name}_p{page.page_number}_{start_index + i}",
                text=text,
                page_number=page.page_number,
                char_start=max(char_start, 0),
                char_end=char_end,
                file_name=file_name,
                has_images=page.has_images,
                has_tables=page.has_tables,
                chunk_index=start_index + i,
            )
            chunks.append(chunk)

        return self._apply_overlap(chunks)

    def _recursive_split(self, text: str, max_size: int) -> list[str]:
        """
        Recursively split text using a priority list of separators.
        Falls back to the next separator if chunks are too large.
        """
        if len(text) <= max_size:
            return [text]

        for sep in self.SEPARATORS:
            parts = text.split(sep)
            if len(parts) == 1:
                continue  # separator not found, try next

            chunks, current = [], ""
            for part in parts:
                candidate = current + (sep if current else "") + part
                if len(candidate) <= max_size:
                    current = candidate
                else:
                    if current:
                        chunks.append(current)
                    # if single part too large, recurse on it
                    if len(part) > max_size:
                        chunks.extend(self._recursive_split(part, max_size))
                        current = ""
                    else:
                        current = part

            if current:
                chunks.append(current)

            return [c.strip() for c in chunks if c.strip()]

        # hard split by charactor
        return [text[i : i + max_size] for i in range(0, len(text), max_size)]

    def _apply_overlap(self, chunks: list[TextChunk]) -> list[TextChunk]:
        """
        Add training text from the previous chunk to the start of each chunk to maintain context across boundaries.
        """
        if len(chunks) <= 1:
            return chunks

        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_text = chunks[i - 1].text
            overlap_text = (
                prev_text[-self.chunk_overlap :]
                if len(prev_text) > self.chunk_overlap
                else prev_text
            )

            new_text = overlap_text + " " + chunks[i].text
            chunks[i].text = new_text.strip()
            overlapped.append(chunks[i])

        return overlapped
