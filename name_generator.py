"""
Name Generator - Uses Ollama to generate names from stored prompts.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import ollama

# Default path when not overridden by app (e.g. app uses AppData path)
PROMPTS_PATH = Path(__file__).parent / "prompts.json"

# Phrases that indicate a line is preamble/commentary, not a name (case-insensitive)
NOT_NAME_PHRASES = (
    "here is", "here are", "here's", "sure,", "sure!", "sure ",
    "list of", "names:", "names ", "following", "below:", "below ",
    "generated", "here you go", "of course", "certainly", "glad to", "happy to",
    "i've ", "i have ", "i'll ", "i will ", "as requested", "as you asked",
    "hope this", "hope you", "enjoy!", "enjoy ", "let me", "okay,", "okay ",
    "alright", "certainly!", "of course!", "gladly", "absolutely",
    "here are some", "here are a few", "here are 10", "here are ten",
    "fantasy names", "sci-fi names", "character names", "product names",
    "project names", "business names", "company names", "band names",
    "pet names", "game names", "app names", "artist names",
    "no numbering", "no bullets", "one per line", "one name per line",
)
# Max length for a single name (longer lines are likely sentences)
MAX_NAME_LENGTH = 80


def load_prompts(path: Path = PROMPTS_PATH) -> list[dict]:
    """Load named prompts from JSON file. Returns [] if file is missing or invalid."""
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("prompts", [])
    except (OSError, json.JSONDecodeError):
        return []


def save_prompts(prompts: list[dict], path: Path = PROMPTS_PATH) -> None:
    """Save prompts back to JSON file. Raises OSError on write failure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"prompts": prompts}, f, indent=2)


def list_models() -> list[str]:
    """Return list of available Ollama model names (from local Ollama instance)."""
    try:
        resp = ollama.list()
        # ollama-python returns ListResponse with .models (list of Model objects with .model attribute)
        models = getattr(resp, "models", None) if not isinstance(resp, dict) else resp.get("models", [])
        if models is None:
            models = resp.get("models", []) if isinstance(resp, dict) else []
        if not isinstance(models, list):
            return []
        names = []
        for m in models:
            if hasattr(m, "model"):
                names.append(m.model)
            elif isinstance(m, dict):
                name = m.get("model") or m.get("name")
                if name:
                    names.append(name)
            elif isinstance(m, str):
                names.append(m)
        return names
    except Exception:  # ollama.list() may raise various errors (connection, timeout, etc.)
        return []


def generate_names(
    prompt_text: str,
    model: str = "llama2",
    stream: bool = False,
    temperature: float = 0.8,
) -> str:
    """
    Call Ollama to generate text from the given prompt.
    temperature: 0 = deterministic, higher = more varied (default 0.8 for different names each run).
    Uses repeat_penalty and top_p to reduce repetitive output.
    Returns the raw response text.
    """
    options = {
        "temperature": max(0.0, min(2.0, temperature)),
        "repeat_penalty": 1.2,
        "top_p": 0.95,
    }
    return ollama.generate(
        model=model, prompt=prompt_text, stream=stream, options=options
    )["response"]


def _looks_like_commentary(line: str) -> bool:
    """True if the line is preamble/commentary rather than a name."""
    if len(line) > MAX_NAME_LENGTH:
        return True
    lower = line.lower()
    for phrase in NOT_NAME_PHRASES:
        if phrase in lower:
            return True
    # Skip lines that are just a single word that's clearly meta (e.g. "Sure", "Here")
    if re.match(r"^(sure|here|okay|yes|no|thanks|hello|hi)[\s\.\!\,]?$", lower):
        return True
    return False


def parse_names(raw: str) -> list[str]:
    """
    Parse raw LLM output into a list of names.
    Handles numbered lines, bullets, and plain lines.
    Skips preamble and commentary (e.g. "Sure, here is a list of names").
    Removes duplicates, keeping first occurrence of each name (case-insensitive).
    """
    names = []
    seen = set()
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        # Remove leading numbering (1. 2) 3. 1) etc.) or bullets (- * •)
        line = re.sub(r"^\s*[\d]+[\.\)]\s*", "", line)
        line = re.sub(r"^\s*[-*•]\s*", "", line)
        line = line.strip()
        if not line or _looks_like_commentary(line):
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(line)
    return names
