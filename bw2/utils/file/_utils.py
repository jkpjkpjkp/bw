"""Common utilities shared between epub and pdf parsers."""

import uuid
from pathlib import Path

import duckdb

from ...cfg import DB_DIR


def get_db() -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection, creating tables if needed."""
    db_path = Path(DB_DIR)
    db_path.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path / "books.db"))

    conn.execute("""
        CREATE TABLE IF NOT EXISTS book (
            uid_book TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT,
            chapters TEXT[]
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chapter (
            uid_chapter TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            text TEXT NOT NULL,
            uid_book TEXT NOT NULL REFERENCES book(uid_book)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS person (
            uid_person TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS book_person (
            uid_book TEXT NOT NULL REFERENCES book(uid_book),
            uid_person TEXT NOT NULL REFERENCES person(uid_person),
            role TEXT DEFAULT 'author',
            PRIMARY KEY (uid_book, uid_person)
        )
    """)

    return conn


# Titles that indicate non-content chapters
NON_CONTENT_TITLES = {
    "title page", "titlepage", "cover", "copyright", "dedication",
    "acknowledgments", "acknowledgements", "notes", "index", "bibliography",
    "references", "about the author", "also by", "praise for", "contents",
    "table of contents", "photographs", "photo insert", "maps", "illustrations",
}


def is_content_chapter(title: str) -> bool:
    """Check if a chapter title indicates actual content (not front/back matter)."""
    title_lower = title.lower().strip()
    return title_lower not in NON_CONTENT_TITLES


def store_book(
    title: str,
    author: str,
    chapters: list[tuple[str, str]],
    con: duckdb.DuckDBPyConnection | None = None,
) -> str:
    """Store book and chapters directly into DuckDB.

    Args:
        title: Book title.
        author: Book author.
        chapters: List of (chapter_title, chapter_text) tuples.
        con: Optional existing connection. If None, creates new one.

    Returns:
        The uid_book of the created book.
    """
    close_con = con is None
    if con is None:
        con = get_db()

    uid_book = str(uuid.uuid4())
    chapter_uids: list[str] = []

    # Insert chapters
    for chapter_title, chapter_text in chapters:
        uid_chapter = str(uuid.uuid4())
        chapter_uids.append(uid_chapter)
        con.execute(
            "INSERT INTO chapter (uid_chapter, title, text, uid_book) VALUES (?, ?, ?, ?)",
            [uid_chapter, chapter_title, chapter_text, uid_book]
        )

    # Insert book with chapter list
    con.execute(
        "INSERT INTO book (uid_book, title, author, chapters) VALUES (?, ?, ?, ?)",
        [uid_book, title, author, chapter_uids]
    )

    # Handle author as person
    if author:
        # Check if person already exists
        result = con.execute(
            "SELECT uid_person FROM person WHERE name = ?", [author]
        ).fetchone()

        if result:
            uid_person = result[0]
        else:
            uid_person = str(uuid.uuid4())
            con.execute(
                "INSERT INTO person (uid_person, name) VALUES (?, ?)",
                [uid_person, author]
            )

        # Link book to person
        con.execute(
            "INSERT INTO book_person (uid_book, uid_person, role) VALUES (?, ?, ?)",
            [uid_book, uid_person, "author"]
        )

    if close_con:
        con.close()

    return uid_book
