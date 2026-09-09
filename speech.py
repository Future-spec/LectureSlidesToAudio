"""Local text-to-speech output."""

from pathlib import Path


def save_audio(narration: str, output_path: str) -> Path:
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
    engine.setProperty("rate", 155)
    engine.save_to_file(narration, str(path))
    engine.runAndWait()
    return path
