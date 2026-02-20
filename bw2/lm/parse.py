"""Estimate protagonist's age in each chapter."""
from dataclasses import dataclass

import duckdb

from ..utils.file._utils import get_db
from . import query


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


def _get_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def estimate_chapter_age(
    chapter_text: str, name: str, birth_year: int | None
) -> ChapterAge:
    birth_info = f"The main character was born in {birth_year}." if birth_year else ""
    prompt = f"""Based on the following excerpt from an autobiography/memoir by {name},
estimate the age range of the main character during the events being described.
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
    lines = response.strip().split("\n")

    age_min = None
    age_max = None
    reasoning = ""
    for line in lines:
        if line.startswith("AGE_MIN:"):
            age_str = line.replace("AGE_MIN:", "").strip()
            try:
                age_min = int(age_str)
            except ValueError:
                pass
        elif line.startswith("AGE_MAX:"):
            age_str = line.replace("AGE_MAX:", "").strip()
            try:
                age_max = int(age_str)
            except ValueError:
                pass
        elif line.startswith("REASONING:"):
            reasoning = line.replace("REASONING:", "").strip()

    return ChapterAge(chapter_title="", age_min=age_min, age_max=age_max, reasoning=reasoning)


def analyze_book(
    uid_book: str,
    birth_year: int | None = None,
    con: duckdb.DuckDBPyConnection | None = None,
) -> BookAgeProfile:
    """Analyze a book and estimate ages for each chapter.

    Args:
        uid_book: The uid_book of the book to analyze.
        birth_year: The author's birth year (for age computation).
        con: Optional DuckDB connection. If None, creates new one.

    Returns:
        BookAgeProfile with age estimates for each chapter.
    """
    close_con = con is None
    if con is None:
        con = get_db()

    # Get book info
    book_row = con.execute(
        "SELECT title, author FROM book WHERE uid_book = ?", [uid_book]
    ).fetchone()
    if not book_row:
        raise ValueError(f"Book not found: {uid_book}")

    book_title, author = book_row

    # Get chapters
    chapters = con.execute(
        "SELECT title, text FROM chapter WHERE uid_book = ? ORDER BY uid_chapter",
        [uid_book]
    ).fetchall()

    chapter_ages: list[ChapterAge] = []

    for chapter_title, chapter_text in chapters:
        paras = _get_paragraphs(chapter_text)
        paras = paras if len(paras) <= 6 else paras[:3] + ['...'] + paras[-3:]
        paras_text = '\n\n'.join(paras)
        if len(paras_text) < 120:
            continue

        age_result = estimate_chapter_age(paras_text, author, birth_year)
        age_result.chapter_title = chapter_title
        chapter_ages.append(age_result)

    if close_con:
        con.close()

    return BookAgeProfile(
        book_title=book_title,
        author=author,
        birth_year=birth_year,
        chapter_ages=chapter_ages,
    )
