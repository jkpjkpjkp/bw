import re
import json
from dataclasses import dataclass

from dev.utils.llm import query


@dataclass
class Entity:
    name: str
    type: str


def entity(f: str):
    """input a chapter's main text and extract any entities mentioned.

    1. use heuristics:
        running capitalized words breaking only by `of` `in` etc.
        capital word not prepended by '. '
    2. dedup
    3. sample small chunks of text, the union of which should cover all heiristically found entites
    4. let an llm fill out the type and name of entity, based on a chunk of text.
    """
    # Step 1: Use heuristics to find potential entities
    # Find sequences of capitalized words, allowing breaks at "of", "in", "the", etc.
    # Exclude words that come right after '. ' (start of sentence)

    # Pattern to match capitalized word sequences
    # This captures running capitalized words, potentially separated by lowercase connectors
    pattern = r'(?<!\. )(?:[A-Z][a-z]+(?:\s+(?:of|in|the|de|van|von|la|le|da|di)\s+)?)+[A-Z][a-z]+'
    potential_entities = re.findall(pattern, f)

    # Also find single capitalized words not after '. '
    single_cap_pattern = r'(?<!\. )[A-Z][a-z]+'
    single_words = re.findall(single_cap_pattern, f)

    # Combine and filter out very short matches
    all_candidates = list(set(potential_entities + [w for w in single_words if len(w) > 2]))

    # Step 2: Dedup
    unique_entities = list(set(all_candidates))

    if not unique_entities:
        return []

    # Step 3: Sample small chunks of text that cover all heuristically found entities
    # For each entity, find a chunk of text around it (context window)
    chunk_size = 200  # characters around the entity
    chunks = []
    covered_entities = set()

    for entity_str in unique_entities:
        # Find first occurrence of this entity
        match = re.search(re.escape(entity_str), f)
        if match:
            start = max(0, match.start() - chunk_size // 2)
            end = min(len(f), match.end() + chunk_size // 2)
            chunk = f[start:end]
            chunks.append((entity_str, chunk))
            covered_entities.add(entity_str)

    # Step 4: Let an LLM fill out the type and name of entity
    results = []

    for entity_str, chunk in chunks:
        system_prompt = """You are an entity extraction assistant. Given a text chunk with an entity,
classify the entity type (e.g., PERSON, LOCATION, ORGANIZATION, EVENT, CONCEPT, etc.)
and provide the normalized name. Return ONLY valid JSON in this format:
{"name": "normalized entity name", "type": "ENTITY_TYPE"}"""

        user_prompt = f"""Text chunk: {chunk}

Entity to classify: {entity_str}

Classify this entity and return JSON with 'name' and 'type' fields."""

        try:
            response = query(user_prompt, system_prompt)
            # Parse the JSON response
            # Extract JSON from response (in case there's extra text)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                entity_data = json.loads(json_match.group())
                results.append(Entity(
                    name=entity_data.get('name', entity_str),
                    type=entity_data.get('type', 'UNKNOWN')
                ))
        except (json.JSONDecodeError, Exception):
            # Fallback if LLM response is malformed
            results.append(Entity(name=entity_str, type='UNKNOWN'))

    return results