"""search for most notable persons in a specimen, and books authored by them.

at this stage the `search` is querying an llm
"""

import yaml
from pathlib import Path

from dev.utils import query

_PERSONS_YAML_PATH = Path(__file__).parent.parent / "book" / "persons.yaml"


def search_distinguished_persons(category: str, count: int = 10) -> list[dict]:
    """Search for distinguished persons in a given category and their autobiographies/memoirs."""
    prompt = f"""List {count} extremely distinguished {category} who have written autobiographies or memoirs.
For each person, provide:
- name: their full name
- book: the title of their most notable autobiography or memoir (must be a real book they authored about themselves)
- any relevant identifying info (company, country, field, etc.)

Return ONLY valid YAML format like this:
- name: "Person Name"
  book: "Book Title"
  company: "Company Name"  # or country, field, etc. as appropriate

Important: Only include people who have actually written autobiographies or memoirs about their own lives.
Do not include biographies written by others."""

    system_prompt = "You are a knowledgeable assistant that provides accurate information about notable figures and their autobiographical works. Return only valid YAML."

    response = query(prompt, system_prompt)

    # Clean response - remove markdown code blocks if present
    response = response.strip()
    if response.startswith("```"):
        lines = response.split("\n")
        response = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        return yaml.safe_load(response)
    except yaml.YAMLError:
        return []


def search_books_by_person(name: str) -> list[str]:
    """Search for autobiographies/memoirs written by a specific person."""
    prompt = f"""List all autobiographies and memoirs written by {name}.
Return ONLY valid YAML format - a simple list of book titles:
- "Book Title 1"
- "Book Title 2"

Only include books that are autobiographies or memoirs written by {name} themselves."""

    system_prompt = "You are a knowledgeable assistant. Return only valid YAML."

    response = query(prompt, system_prompt)

    response = response.strip()
    if response.startswith("```"):
        lines = response.split("\n")
        response = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        return yaml.safe_load(response) or []
    except yaml.YAMLError:
        return []


def populate_persons_yaml(categories: list[str] | None = None) -> None:
    """Populate persons.yaml with distinguished people from various categories."""
    if categories is None:
        categories = [
            "entrepreneurs",
            "executives/CEOs",
            "politicians",
            "scientists",
            "athletes",
            "artists",
            "military leaders",
        ]

    if _PERSONS_YAML_PATH.exists():
        existing = yaml.safe_load(_PERSONS_YAML_PATH.read_text()) or {}
    else:
        existing = {}

    # Collect all existing names across all categories for global dedup
    all_names: set[str] = set()
    for cat_persons in existing.values():
        if isinstance(cat_persons, list):
            for p in cat_persons:
                if p.get("name"):
                    all_names.add(p.get("name"))

    for category in categories:
        # Normalize category name for YAML key
        key = category.split("/")[0].rstrip("s")  # "entrepreneurs" -> "entrepreneur"

        print(f"Searching for distinguished {category}...")
        persons = search_distinguished_persons(category, count=10)

        if persons:
            if key not in existing:
                existing[key] = []

            # Add new persons, avoiding duplicates across entire file
            for person in persons:
                name = person.get("name")
                if name and name not in all_names:
                    existing[key].append(person)
                    all_names.add(name)

    # Write back
    _PERSONS_YAML_PATH.write_text(yaml.dump(existing, default_flow_style=False, allow_unicode=True, sort_keys=False))
    print(f"Updated {_PERSONS_YAML_PATH}")


if __name__ == "__main__":
    populate_persons_yaml()
