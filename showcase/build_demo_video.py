"""Build a narrated LectureLens demo video from captured app states."""

from pathlib import Path
import subprocess
import tempfile

import pyttsx3
from PIL import Image, ImageDraw, ImageFont
from imageio_ffmpeg import get_ffmpeg_exe


ROOT = Path(__file__).resolve().parents[1]
SHOWCASE = ROOT / "showcase"
OUTPUT = SHOWCASE / "LectureLens_Demo.mp4"
FONT = Path("C:/Windows/Fonts/arial.ttf")
BOLD_FONT = Path("C:/Windows/Fonts/arialbd.ttf")

SCENES = [
    ("01  /  EVERY LECTURE DESERVES TO BE HEARD", "From visual slides to a calm, guided listening experience.", "video_lesson.png", "LectureLens turns lecture material into a lesson you can listen to, revisit, and actively study."),
    ("02  /  BRING THE MATERIAL", "PDF, image, or pasted source text.", "video_lesson.png", "The workflow starts with the material students already have. A selectable PDF can be processed directly, a slide image can be read with optional vision support, and pasted text is always available as a fast path."),
    ("03  /  CHOOSE HOW TO LEARN", "Explain it, revise it, or go deeper.", "video_lesson.png", "The learner chooses the shape of the explanation. Explain it is clear and friendly. Revision mode keeps definitions and exam-ready relationships tight. Deep dive connects the why behind the material."),
    ("04  /  CREATE THE AUDIO LESSON", "A structured process, with an offline fallback.", "video_lesson.png", "LectureLens separates reading from explaining. It extracts the source, finds key ideas, creates a natural narration, and prepares the learning views. With no API key, the offline guide keeps the core demo usable and predictable."),
    ("05  /  LISTEN, REPLAY, REMEMBER", "The player is built around control.", "video_lesson.png", "The lesson player works with the device speech engine. Students can choose a voice, adjust speed, restart, stop, and jump to a paragraph. Completion state is saved locally so the lesson can be resumed instead of restarted from zero."),
    ("06  /  DECK INTELLIGENCE", "Three slides become a navigable map.", "video_deck.png", "This is where LectureLens moves beyond transcription. The demo deck is represented as three structured slides: the big idea, inputs and outputs, and the equation. Each slide can be selected and played independently, making review more focused."),
    ("07  /  STUDY KIT + LESSON TUTOR", "Turn listening into active recall.", "video_study_kit.png", "The Study kit gives the learner a compact summary, a quick quiz, flashcards, and next steps. The tutor stays grounded in the current source, so a follow-up question becomes a useful extension of the lesson rather than a disconnected chatbot conversation."),
    ("08  /  THE PRODUCT HORIZON", "Accessible learning, with room to grow.", "video_study_kit.png", "Today, LectureLens already demonstrates the full local learning loop: bring a deck, create an explanation, listen, practice, and ask. The next horizon is persistent accounts, storage for longer decks, background processing, and downloadable browser audio. The direction stays simple: make visual learning audible for more people."),
]


def font(path, size):
    return ImageFont.truetype(str(path if path.exists() else FONT), size)


def make_frame(source, title, subtitle, index, destination):
    image = Image.open(source).convert("RGB")
    image.thumbnail((1200, 650))
    canvas = Image.new("RGB", (1280, 720), "#18221F")
    x = (1280 - image.width) // 2
    y = 54 + (650 - image.height) // 2
    canvas.paste(image, (x, y))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1280, 54), fill="#0D786E")
    draw.text((36, 16), title, fill="white", font=font(BOLD_FONT, 18))
    draw.rectangle((0, 674, 1280, 720), fill="#18221F")
    draw.text((36, 686), subtitle, fill="#CCE9D9", font=font(FONT, 17))
    draw.text((1195, 687), f"{index:02d}/08", fill="#E67B5F", font=font(BOLD_FONT, 16))
    canvas.save(destination, quality=94)


def narrate(text, destination):
    engine = pyttsx3.init()
    engine.setProperty("rate", 145)
    engine.setProperty("volume", 0.95)
    voices = engine.getProperty("voices")
    if voices:
        engine.setProperty("voice", voices[0].id)
    engine.save_to_file(text, str(destination))
    engine.runAndWait()
    engine.stop()


def run(command):
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    missing = [SHOWCASE / name for name in {scene[2] for scene in SCENES} if not (SHOWCASE / name).exists()]
    if missing:
        raise SystemExit("Missing browser captures: " + ", ".join(str(path) for path in missing))
    ffmpeg = get_ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix="lecturelens-video-") as temporary:
        temporary = Path(temporary)
        segments = []
        for index, (title, subtitle, image_name, narration) in enumerate(SCENES, start=1):
            frame_path = temporary / f"frame-{index:02d}.jpg"
            audio_path = temporary / f"audio-{index:02d}.wav"
            segment_path = temporary / f"segment-{index:02d}.mp4"
            make_frame(SHOWCASE / image_name, title, subtitle, index, frame_path)
            narrate(narration, audio_path)
            run([ffmpeg, "-y", "-loop", "1", "-i", str(frame_path), "-i", str(audio_path), "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-af", "apad", "-t", "35", str(segment_path)])
            segments.append(segment_path)
        concat_file = temporary / "concat.txt"
        concat_file.write_text("\n".join(f"file '{path.as_posix()}'" for path in segments), encoding="utf-8")
        run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(OUTPUT)])
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()