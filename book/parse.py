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
    chapter_title: str
    age_min: int | None
    age_max: int | None
    reasoning: str


@dataclass
class BookAgeProfile:
    book_title: str
    author: str
    birth_year: int | None
    chapter_ages: list[ChapterAge]


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
        ChapterAge with estimated age range and reasoning.
    """
    birth_info = f"The author was born in {birth_year}." if birth_year else ""

    prompt = f"""Based on the following excerpt from an autobiography/memoir by {author_name},
estimate the age range of the author during the events being described.
{birth_info}

Excerpt:
---
{chapter_text}
---

Respond in this exact format:
AGE_MIN: <number>
AGE_MAX: <number>
REASONING: <brief explanation of clues used>

The events in a chapter may span multiple years, so provide a range.
If only one age is clear, use the same value for both min and max.
Always provide your best estimate as a number, even if uncertain.

Look for clues like:
- Direct age mentions ("when I was 12...")
- Life stages (childhood, college, retirement)
- Career milestones (first job, becoming CEO)
- Year mentions (e.g., "in 2010...")
- Historical events with known dates (combined with birth year to compute age)
- Family context (having children, grandchildren)"""

    system_prompt = "You are analyzing autobiographical text to estimate the protagonist's age range."

    response = query(prompt, system_prompt)

    # Parse response
    age_min = None
    age_max = None
    reasoning = ""

    lines = response.strip().split("\n")
    for line in lines:
        if line.startswith("AGE_MIN:"):
            age_str = line.replace("AGE_MIN:", "").strip()
            try:
                age_min = int(age_str)
            except ValueError:
                age_min = None
        elif line.startswith("AGE_MAX:"):
            age_str = line.replace("AGE_MAX:", "").strip()
            try:
                age_max = int(age_str)
            except ValueError:
                age_max = None
        elif line.startswith("REASONING:"):
            reasoning = line.replace("REASONING:", "").strip()

    return ChapterAge(chapter_title="", age_min=age_min, age_max=age_max, reasoning=reasoning)


def analyze_book(
    book: Book, birth_year: int | None = None
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

    for chapter in book.chapters:
        first_paragraphs = _get_first_paragraphs(chapter.text)
        if len(first_paragraphs) < 70:
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


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m dev.book.parse <epub_path> [birth_year]")
        sys.exit(1)

    epub_path = sys.argv[1]
    birth_year = int(sys.argv[2]) if len(sys.argv) > 2 else None

    print(f"Analyzing: {epub_path}")
    if birth_year:
        print(f"Birth year: {birth_year}")
        
    book = load_epub(path)
    profile = analyze_book(book, birth_year)

    print(f"\nBook: {profile.book_title}")
    print(f"Author: {profile.author}")
    print(f"\nChapter age estimates:")
    for ca in profile.chapter_ages:
        if ca.age_min is not None and ca.age_max is not None:
            age_str = f"{ca.age_min}-{ca.age_max}" if ca.age_min != ca.age_max else str(ca.age_min)
        else:
            age_str = "unknown"
        print(f"  - {ca.chapter_title}: age ~{age_str}")
        print(f"    {ca.reasoning}")