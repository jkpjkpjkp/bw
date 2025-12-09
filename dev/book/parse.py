"""Parse books into chapters and estimate protagonist age.

Uses LLM to analyze chapter content and estimate the author's age
at the time of events described.
"""

from dataclasses import dataclass
from pathlib import Path

from dev.book.epub import Book, load_epub
from dev.utils import query


@dataclass
class ChapterAge:
    """Age estimate for a chapter."""

    chapter_title: str
    age_estimate: int | None
    reasoning: str


@dataclass
class BookAgeProfile:
    """Age profile for an entire book."""

    book_title: str
    author: str
    birth_year: int | None
    chapter_ages: list[ChapterAge]

    @property
    def ages(self) -> list[int]:
        """Get list of all estimated ages (non-None)."""
        return [ca.age_estimate for ca in self.chapter_ages if ca.age_estimate is not None]

    @property
    def age_range(self) -> tuple[int, int] | None:
        """Get (min, max) age range covered by the book."""
        ages = self.ages
        if not ages:
            return None
        return min(ages), max(ages)


def _get_first_paragraphs(text: str, n: int = 3) -> str:
    """Get the first n paragraphs of text."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "\n\n".join(paragraphs[:n])


def estimate_chapter_age(
    chapter_text: str, author_name: str, birth_year: int | None
) -> ChapterAge:
    """Estimate the author's age during the events described in a chapter.

    Args:
        chapter_text: The first few paragraphs of the chapter.
        author_name: The name of the author/protagonist.
        birth_year: The author's birth year (if known).

    Returns:
        ChapterAge with estimated age and reasoning.
    """
    birth_info = f"The author was born in {birth_year}." if birth_year else ""

    prompt = f"""Based on the following excerpt from an autobiography/memoir by {author_name},
estimate the approximate age of the author at the time of the events being described.
{birth_info}

Excerpt:
---
{chapter_text}
---

Respond in this exact format:
AGE: <number or "unknown">
REASONING: <brief explanation of clues used>

Look for clues like:
- Direct age mentions ("when I was 12...")
- Life stages (childhood, college, retirement)
- Career milestones (first job, becoming CEO)
- Historical events with known dates (combined with birth year to compute age)
- Family context (having children, grandchildren)"""

    system_prompt = "You are analyzing autobiographical text to estimate the author's age. Be precise when possible, make reasonable estimates when clues are indirect."

    response = query(prompt, system_prompt)

    # Parse response
    age_estimate = None
    reasoning = ""

    lines = response.strip().split("\n")
    for line in lines:
        if line.startswith("AGE:"):
            age_str = line.replace("AGE:", "").strip()
            try:
                age_estimate = int(age_str)
            except ValueError:
                age_estimate = None
        elif line.startswith("REASONING:"):
            reasoning = line.replace("REASONING:", "").strip()

    return ChapterAge(chapter_title="", age_estimate=age_estimate, reasoning=reasoning)


def analyze_book(
    book: Book, birth_year: int | None = None, max_chapters: int | None = None
) -> BookAgeProfile:
    """Analyze a book and estimate ages for each chapter.

    Args:
        book: The Book object to analyze.
        birth_year: The author's birth year (for age computation).
        max_chapters: Maximum number of chapters to analyze (None for all).

    Returns:
        BookAgeProfile with age estimates for each chapter.
    """
    chapter_ages: list[ChapterAge] = []
    chapters_to_analyze = book.chapters[:max_chapters] if max_chapters else book.chapters

    for chapter in chapters_to_analyze:
        first_paragraphs = _get_first_paragraphs(chapter.text)
        if len(first_paragraphs) < 100:
            continue

        age_result = estimate_chapter_age(first_paragraphs, book.author, birth_year)
        age_result.chapter_title = chapter.title
        chapter_ages.append(age_result)

    return BookAgeProfile(
        book_title=book.title,
        author=book.author,
        birth_year=birth_year,
        chapter_ages=chapter_ages,
    )


def analyze_epub(
    path: str | Path, birth_year: int | None = None, max_chapters: int | None = None
) -> BookAgeProfile:
    """Load an EPUB and analyze it for age estimates.

    Args:
        path: Path to the EPUB file.
        birth_year: The author's birth year (for age computation).
        max_chapters: Maximum number of chapters to analyze.

    Returns:
        BookAgeProfile with age estimates.
    """
    book = load_epub(path)
    return analyze_book(book, birth_year, max_chapters)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m dev.book.parse <epub_path> [birth_year] [max_chapters]")
        sys.exit(1)

    epub_path = sys.argv[1]
    birth_year = int(sys.argv[2]) if len(sys.argv) > 2 else None
    max_chapters = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    print(f"Analyzing: {epub_path}")
    if birth_year:
        print(f"Birth year: {birth_year}")

    profile = analyze_epub(epub_path, birth_year, max_chapters)

    print(f"\nBook: {profile.book_title}")
    print(f"Author: {profile.author}")
    print(f"\nChapter age estimates:")
    for ca in profile.chapter_ages:
        age_str = str(ca.age_estimate) if ca.age_estimate else "unknown"
        print(f"  - {ca.chapter_title}: age ~{age_str}")
        print(f"    {ca.reasoning}")

    if profile.age_range:
        print(f"\nAge range covered: {profile.age_range[0]} - {profile.age_range[1]}")
