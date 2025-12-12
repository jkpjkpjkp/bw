"""Lightweight PDF loader using pdfplumber.

PDFs don't have native chapter structure, so we use heuristics:
- Detect chapter headings by font size and text patterns
- Group pages into chapters based on detected headings
"""

import re
from pathlib import Path

import pdfplumber

from .common import Book, Chapter, is_content_chapter


# Patterns that suggest chapter headings
_CHAPTER_PATTERNS = [
    re.compile(r"^chapter\s+(\d+|[ivxlc]+)", re.IGNORECASE),
    re.compile(r"^part\s+(\d+|[ivxlc]+)", re.IGNORECASE),
    re.compile(r"^(\d+)\.\s+\w+"),  # "1. Introduction"
    re.compile(r"^section\s+\d+", re.IGNORECASE),
]


def _normalize_text(text: str) -> str:
    """Normalize whitespace in extracted text."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_chapter_heading(text: str) -> bool:
    """Check if text looks like a chapter heading."""
    text = text.strip()
    if not text or len(text) > 100:
        return False

    for pattern in _CHAPTER_PATTERNS:
        if pattern.match(text):
            return True

    return False


def _extract_metadata(pdf: pdfplumber.PDF) -> tuple[str, str]:
    """Extract title and author from PDF metadata."""
    title = ""
    author = ""

    if pdf.metadata:
        title = pdf.metadata.get("Title", "") or pdf.metadata.get("title", "") or ""
        author = (
            pdf.metadata.get("Author", "")
            or pdf.metadata.get("author", "")
            or pdf.metadata.get("Creator", "")
            or ""
        )

    return str(title), str(author)


def _find_large_text_on_page(page: pdfplumber.page.Page) -> list[tuple[str, float]]:
    """Find text that appears larger than average (potential headings).

    Returns list of (text, font_size) tuples.
    """
    chars = page.chars
    if not chars:
        return []

    # Calculate average font size
    sizes = [c.get("size", 12) for c in chars if c.get("size")]
    if not sizes:
        return []
    avg_size = sum(sizes) / len(sizes)

    # Group chars by line (same top position)
    lines_by_top: dict[float, list[dict]] = {}
    for char in chars:
        top = round(char.get("top", 0), 1)
        if top not in lines_by_top:
            lines_by_top[top] = []
        lines_by_top[top].append(char)

    large_texts = []
    for top in sorted(lines_by_top.keys()):
        line_chars = lines_by_top[top]
        line_sizes = [c.get("size", 12) for c in line_chars if c.get("size")]
        if not line_sizes:
            continue

        line_avg_size = sum(line_sizes) / len(line_sizes)
        # Consider text "large" if it's significantly bigger than page average
        if line_avg_size > avg_size * 1.2:
            text = "".join(c.get("text", "") for c in sorted(line_chars, key=lambda x: x.get("x0", 0)))
            text = text.strip()
            if text:
                large_texts.append((text, line_avg_size))

    return large_texts


def _detect_chapters_by_headings(pdf: pdfplumber.PDF) -> list[tuple[int, str]]:
    """Detect chapter boundaries using heading patterns and font sizes.

    Returns list of (page_index, chapter_title) tuples.
    """
    chapters: list[tuple[int, str]] = []

    for page_idx, page in enumerate(pdf.pages):
        # Look for large text that might be headings
        large_texts = _find_large_text_on_page(page)

        for text, _ in large_texts:
            if _is_chapter_heading(text):
                chapters.append((page_idx, text))
                break  # Only one chapter start per page

        # Also check first few lines of page text for chapter patterns
        if not any(idx == page_idx for idx, _ in chapters):
            page_text = page.extract_text() or ""
            lines = page_text.split("\n")[:5]  # Check first 5 lines
            for line in lines:
                line = line.strip()
                if _is_chapter_heading(line):
                    chapters.append((page_idx, line))
                    break

    return chapters


def load_pdf(path: str | Path) -> Book:
    """Load a PDF file and return a Book object with chapters.

    Args:
        path: Path to the PDF file.

    Returns:
        Book object with title, author, and chapters.
    """
    path = Path(path)

    with pdfplumber.open(path) as pdf:
        title, author = _extract_metadata(pdf)

        # Try to detect chapters
        chapter_boundaries = _detect_chapters_by_headings(pdf)

        chapters: list[Chapter] = []

        if chapter_boundaries:
            # Process detected chapters
            for i, (start_page, chapter_title) in enumerate(chapter_boundaries):
                # Determine end page
                if i + 1 < len(chapter_boundaries):
                    end_page = chapter_boundaries[i + 1][0]
                else:
                    end_page = len(pdf.pages)

                # Extract text from pages in this chapter
                chapter_text_parts = []
                for page_idx in range(start_page, end_page):
                    page_text = pdf.pages[page_idx].extract_text() or ""
                    chapter_text_parts.append(page_text)

                chapter_text = _normalize_text("\n".join(chapter_text_parts))

                # Skip very short chapters or non-content
                if len(chapter_text) < 500:
                    continue
                if not is_content_chapter(chapter_title):
                    continue

                chapters.append(Chapter(title=chapter_title, text=chapter_text))
        else:
            # No chapters detected - treat whole PDF as one chapter or split by page count
            all_text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                all_text_parts.append(page_text)

            full_text = _normalize_text("\n".join(all_text_parts))

            if len(full_text) > 500:
                # If PDF is long, split into chunks of ~10 pages each
                if len(pdf.pages) > 20:
                    chunk_size = 10
                    for i in range(0, len(pdf.pages), chunk_size):
                        chunk_texts = []
                        for page_idx in range(i, min(i + chunk_size, len(pdf.pages))):
                            page_text = pdf.pages[page_idx].extract_text() or ""
                            chunk_texts.append(page_text)
                        chunk_text = _normalize_text("\n".join(chunk_texts))
                        if len(chunk_text) > 500:
                            chapters.append(Chapter(
                                title=f"Section {i // chunk_size + 1}",
                                text=chunk_text
                            ))
                else:
                    # Short PDF - single chapter
                    chapters.append(Chapter(title="Content", text=full_text))

        return Book(title=title or path.stem, author=author, chapters=chapters)
