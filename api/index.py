"""Flask API for Lecture Slides to Audio — runs on Vercel as serverless functions."""

import base64
import json
import os
import re
import urllib.request

from flask import Flask, jsonify, request, send_from_directory

# ---------------------------------------------------------------------------
#  Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__, static_folder="../public", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# ---------------------------------------------------------------------------
#  Serve the frontend (local dev only — Vercel serves /public automatically)
# ---------------------------------------------------------------------------

@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(app.static_folder, path)


# ---------------------------------------------------------------------------
#  Demo data — works without any API key or file upload
# ---------------------------------------------------------------------------

DEMO_EXTRACTED = (
    "Photosynthesis\n\n"
    "- Process by which green plants convert light energy into chemical energy\n"
    "- Uses sunlight, CO2, and water\n"
    "- Produces glucose and oxygen\n"
    "- Equation: 6CO2 + 6H2O → C6H12O6 + 6O2"
)

DEMO_NARRATION = (
    "This slide explains photosynthesis. Photosynthesis is the process through "
    "which green plants use sunlight to make food. They take in carbon dioxide "
    "and water, then produce glucose, which stores energy, and release oxygen. "
    "The chemical equation shows that six molecules of carbon dioxide combine "
    "with six molecules of water to produce one molecule of glucose and six "
    "molecules of oxygen."
)


@app.route("/api/demo")
def demo():
    """Return predefined demo data — no API key or file needed."""
    return jsonify({"extracted_text": DEMO_EXTRACTED, "narration": DEMO_NARRATION})


# ---------------------------------------------------------------------------
#  Extract text from uploaded file
# ---------------------------------------------------------------------------

@app.route("/api/extract", methods=["POST"])
def extract():
    """Extract text from an uploaded image (via AI Vision) or PDF (via PyMuPDF)."""
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file uploaded."}), 400

    filename = file.filename.lower()

    try:
        if filename.endswith(".pdf"):
            text = _extract_pdf(file)
        elif filename.endswith((".jpg", ".jpeg", ".png", ".webp")):
            text = _extract_image(file)
        else:
            return jsonify({"error": "Unsupported file type. Use JPG, PNG, or PDF."}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    if not text.strip():
        return jsonify({"error": "No text could be extracted from this file."}), 400

    return jsonify({"extracted_text": text.strip()})


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error": "File is too large. Maximum upload size is 5 MB."}), 413


def _extract_pdf(file):
    """Extract text from a PDF using PyMuPDF (works on Vercel — pure pip package)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError("PDF support is not available on this server.")

    file_bytes = file.read()
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for i, page in enumerate(doc, 1):
        text = page.get_text().strip()
        if text:
            pages.append(f"Page {i}:\n{text}")

    if not pages:
        raise ValueError(
            "This PDF appears to be scanned images without selectable text. "
            "Try uploading individual slide images (JPG/PNG) instead."
        )
    return "\n\n".join(pages)


def _extract_image(file):
    """Read slide text from an image using AI Vision (replaces Tesseract on Vercel)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "An API key is required to read images. "
            "Set OPENAI_API_KEY in your environment, or try the Demo button."
        )

    image_bytes = file.read()
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    mime = file.content_type or "image/jpeg"

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract ALL text from this lecture slide image. "
                            "Preserve the structure: headings, bullet points, formulas. "
                            "Return only the raw text content — no commentary."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1500,
    }

    return _call_openai(base_url, api_key, payload)


# ---------------------------------------------------------------------------
#  Generate narration from extracted text
# ---------------------------------------------------------------------------

@app.route("/api/narrate", methods=["POST"])
def narrate():
    """Convert extracted slide text into a listening-friendly narration."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided."}), 400

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Offline fallback — regex-based cleanup
        return jsonify({"narration": _demo_narration(text)})

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
                    "fragments or bullets into natural sentences. Return only "
                    "the narration — no headings, no labels."
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0.2,
        "max_tokens": 2000,
    }

    try:
        narration = _call_openai(base_url, api_key, payload)
    except Exception:
        narration = _demo_narration(text)

    return jsonify({"narration": narration})


# ---------------------------------------------------------------------------
#  Shared helpers
# ---------------------------------------------------------------------------

def _call_openai(base_url: str, api_key: str, payload: dict) -> str:
    """Make a chat completions request to any OpenAI-compatible API."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"].strip()


def _demo_narration(text: str) -> str:
    """Offline regex-based narration — same logic as the terminal ai.py."""
    lower = text.lower()
    if "photosynthesis" in lower:
        return DEMO_NARRATION

    text = re.sub(r"\bF\s*=\s*ma\b", "force equals mass multiplied by acceleration", text, flags=re.I)
    text = re.sub(r"\bF\s*=\s*Force\b", "F represents force", text, flags=re.I)
    text = re.sub(r"\bm\s*=\s*Mass\b", "m represents mass", text, flags=re.I)
    text = re.sub(r"\ba\s*=\s*Acceleration\b", "a represents acceleration", text, flags=re.I)
    text = text.replace(":", ". ")
    text = re.sub(r"\s*[-*]\s*", ". ", text)
    text = re.sub(r"\bvs\.?\b", "versus", text, flags=re.I)
    return "Here is a clear explanation of the slide. " + text


# ---------------------------------------------------------------------------
#  Local development server
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n  Starting local dev server...")
    print("  Open http://localhost:5000 in your browser\n")
    app.run(debug=True, port=5000)

