"""api call wrappers to kimi k2"""

from pathlib import Path
from openai import OpenAI

_API_KEY_PATH = Path(__file__).parent.parent.parent / ".secret" / "moonshot-api-key.txt"


def _get_client() -> OpenAI:
    api_key = _API_KEY_PATH.read_text().strip()
    return OpenAI(
        api_key=api_key,
        base_url="https://api.moonshot.ai/v1",
    )


def query(prompt: str, system_prompt: str | None = None) -> str:
    """Query Kimi K2 with a prompt and optional system prompt."""
    client = _get_client()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    completion = client.chat.completions.create(
        model="kimi-k2-turbo-preview",
        messages=messages,
        temperature=0.6,
    )
    return completion.choices[0].message.content
