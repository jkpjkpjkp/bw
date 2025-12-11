"""most notable persons in a specimen, and books them by authored."""
import yaml
from pathlib import Path

from dev.utils import query


def search_distinguished_persons(category: str, count: int = 10) -> list[dict]:
    prompt = f"""List {count} extremely distinguished {category} who have published autobiographic book(s).
For each person, provide:
- name: 
- book: title of their most notable autobiography or memoir(s)
- identifying info (company, country, field, etc.)

Return ONLY valid YAML format like this:
- name: "Person Name"
  book: "Book Title"
  company: "Company Name"  # or country, field, etc. as appropriate

Do not include biographies written by others. only autobiographies (co-)authored or deeply involved by them. """
    system_prompt = "You are a knowledgeable assistant that provides accurate information about notable figures and their autobiographical works. Return only valid YAML."

    response = query(prompt, system_prompt).strip()

    if response.startswith("```"):
        lines = response.split("\n")
        response = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        return yaml.safe_load(response)
    except yaml.YAMLError:
        return []


_PERSONS_YAML_PATH = Path("./book/persons.yaml").absolute()
def populate_persons_yaml(categories: list[str] | None = None) -> None:
    """Populate persons.yaml with distinguished people from various categories."""
    if categories is None:
        categories = [
            "entrepreneurs",
            "executives/CEOs",
            "scientists",
            "athletes",
            "artists",
            "engineers",
            "political or military leaders",
        ]

    existing = yaml.safe_load(_PERSONS_YAML_PATH.read_text())

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
