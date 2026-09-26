"""Local text-to-speech output."""

from pathlib import Path


def save_audio(narration: str, output_path: str, language: str = "en") -> Path:
    """Speak narration and save it as a WAV file."""
    try:
        import pyttsx3
    except ImportError as error:
        raise RuntimeError(
            "Text-to-speech package is missing. Run: pip install -r requirements.txt"
        ) from error

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = pyttsx3.init()
    language_prefix = language.lower().split("-")[0]
    for voice in engine.getProperty("voices") or []:
        voice_details = f"{voice.id} {voice.name} {voice.languages}".lower()
        if language_prefix == "hi" and ("hindi" in voice_details or "hi-in" in voice_details):
            engine.setProperty("voice", voice.id)
            break
    engine.setProperty("rate", 155)
    engine.save_to_file(narration, str(path))
    engine.runAndWait()
    return path
