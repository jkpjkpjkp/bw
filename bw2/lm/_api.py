"""api call wrappers to kimi k2"""

import hashlib
import json
from pathlib import Path

import lmdb
from openai import OpenAI

_API_KEY_PATH = Path(__file__).parent.parent.parent / ".secret" / "moonshot-api-key.txt"
_CACHE_DIR = Path(__file__).parent.parent.parent / ".cache" / "llm"


def _get_cache_env() -> lmdb.Environment:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return lmdb.open(str(_CACHE_DIR), map_size=1024 * 1024 * 1024)  # 1GB


def _cache_key(prompt: str, system_prompt: str | None) -> bytes:
    data = json.dumps({"prompt": prompt, "system_prompt": system_prompt}, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest().encode()


def _get_client() -> OpenAI:
    api_key = _API_KEY_PATH.read_text().strip()
    return OpenAI(
        api_key=api_key,
        base_url="https://api.moonshot.ai/v1",
    )


def query(prompt: str, system_prompt: str | None = None) -> str:
    """Query Kimi K2 with a prompt and optional system prompt. Results are cached."""
    key = _cache_key(prompt, system_prompt)

    # Check cache first
    env = _get_cache_env()
    with env.begin() as txn:
        cached = txn.get(key)
        if cached is not None:
            return cached.decode()

    # Make API call
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
    result = completion.choices[0].message.content

    # Store in cache
    with env.begin(write=True) as txn:
        txn.put(key, result.encode())

    return result
