"""AI narration generation with a useful offline demo fallback."""

import json
import os
import re
import urllib.request

DEMO_TEXT = (
    "Photosynthesis is the process by which green plants convert light energy "
    "into chemical energy. Plants use sunlight, carbon dioxide, and water to "
    "produce glucose and oxygen."
)


def create_narration(raw_text: str, demo: bool = False) -> str:
    """Return a listening-friendly narration from OCR text."""
    cleaned = " ".join(raw_text.split())
    if not cleaned:
        raise ValueError("No text was extracted from the slide.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not demo and api_key:
        return _ask_ai(cleaned, api_key)

    return _demo_narration(cleaned)


def _demo_narration(text: str) -> str:
    """A deterministic response for demonstrations without an API key."""
    if "photosynthesis" in text.lower():
        return (
            "Photosynthesis is the process through which green plants use sunlight "
            "to make food. They take in carbon dioxide and water, then produce "
            "glucose, which stores energy, and release oxygen."
        )

    text = re.sub(r"\bF\s*=\s*ma\b", "force equals mass multiplied by acceleration", text, flags=re.I)
    text = re.sub(r"\bF\s*=\s*Force\b", "F represents force", text, flags=re.I)
    text = re.sub(r"\bm\s*=\s*Mass\b", "m represents mass", text, flags=re.I)
    text = re.sub(r"\ba\s*=\s*Acceleration\b", "a represents acceleration", text, flags=re.I)
    text = text.replace(":", ". ")
    text = re.sub(r"\s*[-*]\s*", ". ", text)
    text = re.sub(r"\bvs\.?\b", "versus", text, flags=re.I)
    return "Here is a clear explanation of the slide. " + text


def _ask_ai(text: str, api_key: str) -> str:
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Convert OCR text from a lecture slide into a clear narration "
                    "for a visually impaired student. Fix obvious OCR errors, "
                    "expand abbreviations, explain formulas in words, and turn "
                    "fragments or bullets into natural sentences. Return only the narration."
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"].strip()
    except Exception as error:
        print(f"AI service unavailable ({error}). Using demo narration instead.")
        return _demo_narration(text)
