import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import yaml

from book import load_epub, analyze_book


def load_persons() -> list[dict]:
    with open('./book/persons.yaml') as f:
        data = yaml.safe_load(f)

    persons = []
    for category, people in data.items():
        for person in people:
            person["category"] = category
            # Extract first name only
            full_name = person["name"]
            person["first_name"] = full_name.split()[0]
            persons.append(person)
    return persons


def find_book_file(person_name: str, book_title: str) -> Path | None:
    name_parts = person_name.lower().split()
    book_parts = [p for p in book_title.lower().split() if len(p) > 3]

    for epub_file in Path('./.books').glob("*.epub"):
        filename_lower = epub_file.name.lower()

        name_hits = sum(1 for part in name_parts if part in filename_lower)
        name_ratio = name_hits / len(name_parts)

        book_hits = sum(1 for part in book_parts if part in filename_lower)
        book_ratio = book_hits / len(book_parts)

        if name_ratio > 0.66 and book_ratio >= 0.75:
            return epub_file
    return None


class UIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.static_dir = Path(__file__).parent / "static"
        super().__init__(*args, directory=str(self.static_dir), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/persons":
            self.send_json(load_persons())
        elif parsed.path.startswith("/api/book/"):
            try:
                person_idx = int(parsed.path.split("/")[-1])
                persons = load_persons()
                if 0 <= person_idx < len(persons):
                    person = persons[person_idx]
                    book_file = find_book_file(person["name"], person.get("book", ""))
                    if book_file:
                        book = load_epub(book_file)
                        profile = analyze_book(book, person.get("birth_year"))
                        self.send_json({
                            "title": book.title,
                            "author": book.author,
                            "chapters": [
                                {
                                    "title": ch.title,
                                    "text": ch.text,
                                    "age_min": profile.chapter_ages[i].age_min if i < len(profile.chapter_ages) else None,
                                    "age_max": profile.chapter_ages[i].age_max if i < len(profile.chapter_ages) else None,
                                }
                                for i, ch in enumerate(book.chapters)
                            ]
                        })
                    else:
                        self.send_json({"error": "Book not found"}, 404)
                else:
                    self.send_json({"error": "Person not found"}, 404)
            except (ValueError, IndexError):
                self.send_json({"error": "Invalid request"}, 400)

    def send_json(self, data: dict | list, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def run_server(port: int = 8080):
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)

    server = HTTPServer(("", port), UIHandler)
    print(f"Server running at http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
