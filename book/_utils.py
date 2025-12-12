"""Common utilities shared between epub and pdf parsers."""

from dataclasses import dataclass, field


@dataclass
class Chapter:
    title: str
    text: str


@dataclass
class Book:
    title: str
    author: str
    chapters: list[Chapter] = field(default_factory=list)

    def __iter__(self):
        return iter(self.chapters)

    def __len__(self):
        return len(self.chapters)


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
    book: Book,
    db_url: str = "ws://localhost:8000/rpc",
    namespace: str = "bw",
    database: str = "books",
) -> str:
    """Store book structure into SurrealDB.

    Args:
        book: The Book object to store.
        db_url: SurrealDB connection URL.
        namespace: SurrealDB namespace.
        database: SurrealDB database name.

    Returns:
        The record ID of the created book.
    """
    from surrealdb import Surreal

    with Surreal(db_url) as db:
        db.signin({"username": "root", "password": "root"})
        db.use(namespace, database)

        # Create book record first (without chapters list)
        book_record = db.create(
            "book",
            {
                "title": book.title,
                "author": book.author,
                "chapter_count": len(book.chapters),
            },
        )
        book_id = book_record[0]["id"]  # type: ignore[index]

        # Create chapter records linked to book
        chapter_ids = []
        for i, chapter in enumerate(book.chapters):
            chapter_record = db.create(
                "chapter",
                {
                    "book": book_id,
                    "index": i,
                    "title": chapter.title,
                    "text": chapter.text,
                },
            )
            chapter_ids.append(chapter_record[0]["id"])  # type: ignore[index]

        # Update book with list of chapter foreign keys
        db.update(book_id, {
            "title": book.title,
            "author": book.author,
            "chapter_count": len(book.chapters),
            "chapters": chapter_ids,
        })

        return book_id
