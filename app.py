"""LectureSlidesToAudio web application.

The app is intentionally designed as a single Flask entrypoint. Vercel detects
``app.py`` as a Flask application and routes requests to it without custom
runtime or rewrite configuration.
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory


BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
MAX_SOURCE_CHARACTERS = 24_000
MAX_PDF_PAGES = 18
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

app = Flask(__name__, static_folder=str(PUBLIC_DIR), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


DEMO_EXTRACTED = """Photosynthesis

- Plants transform light energy into chemical energy.
- Inputs: sunlight, carbon dioxide, and water.
- Outputs: glucose, where energy is stored, and oxygen.
- Equation: 6CO2 + 6H2O -> C6H12O6 + 6O2."""

DEMO_NARRATION = """Let us unpack photosynthesis step by step. Think of a leaf as a tiny solar-powered factory. It captures energy from sunlight and uses that energy to combine carbon dioxide from the air with water from the roots. The plant stores the result as glucose, a sugar it can use later for energy and growth. Oxygen is released as a by-product. The equation on the slide is a compact way to show this exchange: six units of carbon dioxide and six units of water produce one unit of glucose and six units of oxygen. The key takeaway is simple: light energy becomes stored chemical energy."""


@dataclass(frozen=True)
class NarrationProfile:
    label: str
    instruction: str
    opener: str


@dataclass(frozen=True)
class LanguageProfile:
    label: str
    locale: str
    tesseract_code: str
    instruction: str
    fallback_opener: str


LANGUAGE_PROFILES = {
    "en": LanguageProfile(
        label="English",
        locale="en-US",
        tesseract_code="eng",
        instruction="Write the complete response in clear, natural English.",
        fallback_opener="Here is the idea in plain language.",
    ),
    "hi": LanguageProfile(
        label="Hindi",
        locale="hi-IN",
        tesseract_code="hin+eng",
        instruction=(
            "Write the complete response in natural Hindi using Devanagari script. "
            "Keep unavoidable scientific names, formulas, and standard abbreviations in their familiar form, "
            "and explain them in Hindi. Do not translate into Hinglish unless the source itself requires it."
        ),
        fallback_opener="आइए इस विचार को सरल भाषा में समझते हैं।",
    ),

}


NARRATION_PROFILES = {
    "explainer": NarrationProfile(
        label="Clear explainer",
        instruction="Teach it clearly with one helpful analogy where appropriate.",
        opener="Here is the idea in plain language.",
    ),
    "revision": NarrationProfile(
        label="Revision mode",
        instruction="Keep it concise and emphasize definitions, relationships, and exam-ready takeaways.",
        opener="Here is a focused revision of the slide.",
    ),
    "deep": NarrationProfile(
        label="Deep dive",
        instruction="Explain the why behind the material and connect the points logically.",
        opener="Let us build an intuitive understanding of this topic.",
    ),
}


@app.get("/")
def serve_index():
    """Serve the app locally; Vercel serves the same file through its CDN."""
    return send_from_directory(PUBLIC_DIR, "index.html")


@app.get("/api/health")
def health() -> Any:
    configured = bool(os.getenv("OPENAI_API_KEY"))
    return jsonify(
        {
            "status": "ok",
            "service": "LectureSlidesToAudio",
            "ai_configured": configured,
            "ai_provider": "OpenAI-compatible" if configured else "Offline fallback",
            "ai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini") if configured else None,
            "max_upload_mb": MAX_UPLOAD_BYTES // (1024 * 1024),
        }
    )


@app.get("/api/demo")
def demo() -> Any:
    slides = [
        {
            "number": 1,
            "title": "The big idea",
            "text": "Photosynthesis is how plants turn light energy into stored chemical energy.",
        },
        {
            "number": 2,
            "title": "Inputs and outputs",
            "text": "Inputs: sunlight, carbon dioxide, and water. Outputs: glucose, where energy is stored, and oxygen.",
        },
        {
            "number": 3,
            "title": "The equation",
            "text": "6CO2 + 6H2O -> C6H12O6 + 6O2. Six units of carbon dioxide and six units of water produce glucose and oxygen.",
        },
    ]
    return jsonify(
        {
            "title": "Photosynthesis",
            "extracted_text": DEMO_EXTRACTED,
            "narration": DEMO_NARRATION,
            "key_points": [
                "Plants convert light energy into chemical energy.",
                "Carbon dioxide and water are the inputs.",
                "Glucose stores energy and oxygen is released.",
            ],
            "slides": slides,
            "meta": {"source": "interactive demo", "pages": len(slides)},
        }
    )


@app.post("/api/extract")
def extract() -> Any:
    """Extract selectable PDF text or use vision for a lecture-slide image."""
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return _error("Choose a JPG, PNG, WEBP, or PDF before processing.", 400)

    suffix = Path(upload.filename).suffix.lower()
    language = _language_profile(request.form.get("language"))
    try:
        if suffix == ".pdf":
            text, pages, slides = _extract_pdf(upload.read())
            source = "selectable PDF text"
        elif suffix in ALLOWED_IMAGE_EXTENSIONS:
            text = _extract_image(upload.read(), upload.mimetype or "image/jpeg", language)
            pages = 1
            slides = [{"number": 1, "title": _derive_title(text), "text": text}]
            source = "AI slide reading"
        else:
            return _error("That file type is not supported. Use a JPG, PNG, WEBP, or PDF.", 400)
    except UserFacingError as exc:
        return _error(str(exc), exc.status_code)
    except Exception:
        return _error("We could not read that file. Try a smaller, clearer file and try again.", 500)

    clean_text = _clean_source_text(text)
    if not clean_text:
        return _error(
            "No readable text was found. For scanned PDFs, upload an individual slide image with AI reading enabled.",
            422,
        )
    return jsonify(
        {
            "extracted_text": clean_text,
            "slides": [{**slide, "text": _clean_source_text(str(slide.get("text", "")))} for slide in slides],
            "meta": {"source": source, "pages": pages, "characters": len(clean_text)},
        }
    )


@app.post("/api/narrate")
def narrate() -> Any:
    """Turn raw slide text into an accessible, listening-first explanation."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error("Send the slide text as JSON to create a narration.", 400)

    text = _clean_source_text(str(data.get("text", "")))
    if not text:
        return _error("Paste or extract some slide text before generating narration.", 400)
    if len(text) > MAX_SOURCE_CHARACTERS:
        return _error("This source is too long for one narration. Use up to 24,000 characters at a time.", 413)

    language = _language_profile(data.get("language"))
    mode = str(data.get("mode", "explainer")).lower()
    profile = NARRATION_PROFILES.get(mode, NARRATION_PROFILES["explainer"])
    title = _derive_title(text)
    key_points = _derive_key_points(text)

    try:
        narration = _create_ai_narration(text, profile, language)
        engine = "OpenAI"
    except UserFacingError:
        # The no-key and network-error paths still provide a polished demo.
        narration = _fallback_narration(text, profile, language)
        engine = "Smart offline guide"

    return jsonify(
        {
            "title": title,
            "narration": narration,
            "key_points": key_points,
            "meta": {"mode": mode, "engine": engine, "characters": len(text), "language": language.label, "locale": language.locale},
        }
    )


@app.post("/api/study-kit")
def study_kit() -> Any:
    """Create a compact, structured study companion for the current lesson."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error("Send the lesson text as JSON to create a study kit.", 400)

    text = _clean_source_text(str(data.get("text", "")))
    if not text:
        return _error("Create a lesson before generating a study kit.", 400)
    if len(text) > MAX_SOURCE_CHARACTERS:
        return _error("This source is too long for one study kit.", 413)

    language = _language_profile(data.get("language"))
    try:
        kit = _create_ai_study_kit(text, language)
        engine = "OpenAI study coach"
    except UserFacingError:
        kit = _fallback_study_kit(text, language)
        engine = "Offline study coach"

    return jsonify({"study_kit": kit, "meta": {"engine": engine}})


@app.post("/api/ask")
def ask_lesson() -> Any:
    """Answer a learner's question using only the current lesson source."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error("Send a question and lesson text as JSON.", 400)

    text = _clean_source_text(str(data.get("text", "")))
    question = _clean_source_text(str(data.get("question", "")))
    if not text or not question:
        return _error("Add a lesson and a question before asking the tutor.", 400)
    if len(text) > MAX_SOURCE_CHARACTERS:
        return _error("This source is too long for one tutor question.", 413)
    if len(question) > 800:
        return _error("Keep your question under 800 characters.", 413)

    language = _language_profile(data.get("language"))
    try:
        answer = _create_ai_answer(text, question, language)
        engine = "OpenAI lesson tutor"
    except UserFacingError:
        answer = _fallback_answer(text, question, language)
        engine = "Offline lesson tutor"
    return jsonify({"answer": answer, "meta": {"engine": engine}})


@app.errorhandler(413)
def request_too_large(_error: Any) -> Any:
    return _error_response("This upload is too large. Please choose a file under 4 MB.", 413)


@app.errorhandler(404)
def not_found(_error: Any) -> Any:
    if request.path.startswith("/api/"):
        return _error_response("This API route does not exist.", 404)
    return send_from_directory(PUBLIC_DIR, "index.html")


class UserFacingError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def _error(message: str, status_code: int) -> Any:
    return _error_response(message, status_code)


def _error_response(message: str, status_code: int) -> Any:
    return jsonify({"error": message}), status_code


def _extract_pdf(file_bytes: bytes) -> tuple[str, int, list[dict[str, Any]]]:
    if not file_bytes.startswith(b"%PDF"):
        raise UserFacingError("This file does not look like a valid PDF.", 400)
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise UserFacingError("PDF support is temporarily unavailable on this deployment.", 503) from exc

    try:
        document = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise UserFacingError("This PDF could not be opened. It may be password-protected or damaged.", 422) from exc

    try:
        if document.page_count > MAX_PDF_PAGES:
            raise UserFacingError(f"Please upload up to {MAX_PDF_PAGES} PDF pages at a time.", 413)
        pages = []
        slides = []
        for number, page in enumerate(document, start=1):
            extracted = page.get_text("text").strip()
            if extracted:
                pages.append(f"Slide {number}\n{extracted}")
            slides.append({"number": number, "title": _derive_title(extracted), "text": extracted})
        return "\n\n".join(pages), document.page_count, slides
    finally:
        document.close()


def _extract_image(image_bytes: bytes, mime_type: str, language: LanguageProfile) -> str:
    if not image_bytes:
        raise UserFacingError("The image file is empty.", 400)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise UserFacingError(
            "AI slide reading is not configured yet. Paste the slide text below, use a selectable-text PDF, or ask the project owner to add OPENAI_API_KEY on Vercel.",
            503,
        )

    encoded = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {
                "role": "system",
                "content": "You accurately transcribe lecture slides for accessibility.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract every readable word from this lecture slide. Preserve headings, bullets, labels, "
                            "equations, and important ordering. Do not explain it. Return only the transcription. "
                            f"The slide language is {language.label}; preserve its original script exactly."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
                ],
            },
        ],
        "temperature": 0,
        "max_tokens": 2200,
    }
    return _call_openai(payload)


def _create_ai_narration(text: str, profile: NarrationProfile, language: LanguageProfile) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise UserFacingError("AI narration is not configured.", 503)
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an award-winning accessibility tutor. Convert lecture-slide text into a warm, natural "
                    "audio narration for a student who cannot see the slide. Correct obvious OCR mistakes, make "
                    "bullets flow, explain symbols and equations in spoken words, and never invent facts. "
                    f"{profile.instruction} {language.instruction} Use short paragraphs and return only the narration, without a title or markdown."
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0.35,
        "max_tokens": 1800,
    }
    narration = _call_openai(payload)
    if not narration:
        raise UserFacingError("The AI returned an empty narration.", 502)
    return narration


def _create_ai_study_kit(text: str, language: LanguageProfile) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise UserFacingError("AI study kit is not configured.", 503)
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a careful study coach. Based only on the supplied lecture text, create a useful study kit. "
                    "Return valid JSON with exactly these keys: summary (string), quiz (array of 3 objects with question, "
                    "answer, and explanation strings), flashcards (array of 3 objects with front and back strings), "
                    "and next_steps (array of 3 short strings). Never invent facts."
                    f" {language.instruction}"
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0.25,
        "max_tokens": 1600,
    }
    result = _call_openai_json(payload)
    return _normalise_study_kit(result)


def _create_ai_answer(text: str, question: str, language: LanguageProfile) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise UserFacingError("AI tutor is not configured.", 503)
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a patient lecture tutor. Answer the student's question using only the supplied lesson source. "
                    "If the source does not contain enough information, say so clearly and suggest what to review. "
                    f"Use plain language, explain formulas in words, and keep the answer under 180 words. {language.instruction}"
                ),
            },
            {"role": "user", "content": f"LESSON SOURCE:\n{text}\n\nSTUDENT QUESTION:\n{question}"},
        ],
        "temperature": 0.25,
        "max_tokens": 500,
    }
    answer = _call_openai(payload)
    if not answer:
        raise UserFacingError("The AI tutor returned an empty answer.", 502)
    return answer


def _call_openai_json(payload: dict[str, Any]) -> dict[str, Any]:
    raw = _call_openai(payload)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UserFacingError("The AI study coach returned invalid study data.", 502) from exc
    if not isinstance(result, dict):
        raise UserFacingError("The AI study coach returned an unexpected response.", 502)
    return result


def _normalise_study_kit(value: dict[str, Any]) -> dict[str, Any]:
    quiz = value.get("quiz") if isinstance(value.get("quiz"), list) else []
    flashcards = value.get("flashcards") if isinstance(value.get("flashcards"), list) else []
    next_steps = value.get("next_steps") if isinstance(value.get("next_steps"), list) else []
    clean_quiz = [
        {key: str(item.get(key, "")).strip() for key in ("question", "answer", "explanation")}
        for item in quiz[:3]
        if isinstance(item, dict) and item.get("question")
    ]
    clean_cards = [
        {key: str(item.get(key, "")).strip() for key in ("front", "back")}
        for item in flashcards[:3]
        if isinstance(item, dict) and item.get("front")
    ]
    return {
        "summary": str(value.get("summary", "")).strip(),
        "quiz": clean_quiz,
        "flashcards": clean_cards,
        "next_steps": [str(step).strip() for step in next_steps[:3] if str(step).strip()],
    }


def _fallback_study_kit(text: str, language: LanguageProfile) -> dict[str, Any]:
    points = _derive_key_points(text)
    card_back = (
        "इस विचार को अपने शब्दों में समझाइए और इसे स्लाइड की बाकी जानकारी से जोड़िए।"
        if language is LANGUAGE_PROFILES["hi"]
        else "Explain this idea in your own words, then connect it to the surrounding slide."
    )
    cards = [{"front": point, "back": card_back} for point in points]
    question = "इस स्लाइड का मुख्य विचार क्या है?" if language is LANGUAGE_PROFILES["hi"] else "What is the main idea of this slide?"
    explanation = (
        "पहले मुख्य बिंदु से शुरू करें और फिर narration से एक सहायक विवरण जोड़ें।"
        if language is LANGUAGE_PROFILES["hi"]
        else "Start with the first key point, then add one supporting detail from the narration."
    )
    quiz = [
        {
            "question": question,
            "answer": points[0],
            "explanation": explanation,
        }
    ]
    next_steps = (
        ["नरेशन को एक बार फिर सुनें।", "स्रोत देखे बिना मुख्य विचार अपने शब्दों में समझाएँ।", "बाद में लौटकर प्रश्न का उत्तर ज़ोर से दें।"]
        if language is LANGUAGE_PROFILES["hi"]
        else ["Replay the narration once.", "Explain the key idea without looking at the source.", "Return later and answer the quiz aloud."]
    )
    return {
        "summary": " ".join(points),
        "quiz": quiz,
        "flashcards": cards,
        "next_steps": next_steps,
    }


def _fallback_answer(text: str, question: str, language: LanguageProfile) -> str:
    points = _derive_key_points(text)
    lowered_question = question.lower()
    matching = next((point for point in points if any(word in point.lower() for word in lowered_question.split() if len(word) > 4)), points[0])
    if language is LANGUAGE_PROFILES["hi"]:
        return f"इस पाठ के आधार पर सबसे निकटतम उत्तर है: {matching}। आसपास की व्याख्या के लिए narration दोबारा सुनें और फिर इस विचार को अपने शब्दों में समझाने का प्रयास करें।"
    return f"From this lesson, the closest answer is: {matching}. Review the narration for the surrounding explanation, then try explaining the idea in your own words."


def _call_openai(payload: dict[str, Any]) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    request_object = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request_object, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise UserFacingError("The configured AI key was rejected. Check OPENAI_API_KEY in Vercel.", 503) from exc
        raise UserFacingError("The AI service could not complete this request. Please try again.", 502) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise UserFacingError("The AI service took too long to respond. Please try again.", 504) from exc
    except json.JSONDecodeError as exc:
        raise UserFacingError("The AI service returned an unreadable response.", 502) from exc

    try:
        return str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise UserFacingError("The AI service returned an unexpected response.", 502) from exc


def _clean_source_text(value: str) -> str:
    value = value.replace("\x00", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _derive_title(text: str) -> str:
    first_line = next((line.strip(" -:\t") for line in text.splitlines() if line.strip()), "Your lecture")
    if len(first_line) > 72:
        first_line = first_line[:69].rsplit(" ", 1)[0] + "..."
    return first_line or "Your lecture"


def _derive_key_points(text: str) -> list[str]:
    candidates = []
    for line in text.splitlines():
        clean = line.strip(" -*\t")
        if clean and len(clean) > 12 and clean.lower() not in {item.lower() for item in candidates}:
            candidates.append(clean.rstrip("."))
        if len(candidates) == 3:
            break
    if not candidates:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        candidates = [sentence.strip().rstrip(".") for sentence in sentences if len(sentence.strip()) > 12][:3]
    return candidates or ["Listen to the narration for the main idea."]


def _fallback_narration(text: str, profile: NarrationProfile, language: LanguageProfile) -> str:
    title = _derive_title(text)
    points = _derive_key_points(text)
    spoken_points = " ".join(f"{index + 1}. {point}." for index, point in enumerate(points))
    equation_text = re.sub(r"\bCO2\b", "carbon dioxide", text, flags=re.IGNORECASE)
    equation_text = re.sub(r"\bH2O\b", "water", equation_text, flags=re.IGNORECASE)
    equation_text = re.sub(r"\bO2\b", "oxygen", equation_text, flags=re.IGNORECASE)
    equation_text = re.sub(r"->|→", " produces ", equation_text)
    context = " ".join(equation_text.split())
    if len(context) > 620:
        context = context[:617].rsplit(" ", 1)[0] + "."
    if language is LANGUAGE_PROFILES["hi"]:
        return (
            f"{language.fallback_opener} यह स्लाइड {title} के बारे में है। "
            f"इसमें याद रखने योग्य {len(points)} मुख्य बातें हैं। {spoken_points} "
            f"स्लाइड के शब्दों में: {context} "
            "जब भी दोहराने की जरूरत हो, इन मुख्य बातों को फिर से सुनें।"
        )
    return (
        f"{profile.opener} This slide is about {title}. "
        f"There are {len(points)} ideas worth holding onto. {spoken_points} "
        f"In the slide's own words: {context} "
        "Pause here and replay the key points whenever you need a quick refresher."
    )


def _language_profile(value: Any) -> LanguageProfile:
    language = str(value or "en").lower().strip()
    return LANGUAGE_PROFILES.get(language, LANGUAGE_PROFILES["en"])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
