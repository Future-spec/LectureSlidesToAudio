"""Terminal application for converting lecture slides into accessible audio."""

import argparse
from datetime import datetime
from pathlib import Path

from ai import DEMO_TEXT, create_narration
from ocr import extract_text
from speech import save_audio

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"


def print_header():
    print("\n" + "=" * 44)
    print("LECTURE SLIDES TO ACCESSIBLE AUDIO")
    print("=" * 44)


def process_slide(file_path: str, demo: bool = False, language: str = "eng"):
    print("\n[1] Reading slide...")
    if demo:
        print("[2] Demo OCR text loaded (no file or Tesseract needed).")
        raw_text = DEMO_TEXT
    else:
        print("[2] Extracting text with OCR...")
        raw_text = extract_text(file_path, language=language)

    print("[3] AI is simplifying and structuring the content...")
    narration_language = "Hindi" if language.startswith("hin") else "English"
    narration = create_narration(raw_text, demo=demo, language=narration_language)
    print("[4] Generating narration...")
    print("[5] Creating audio...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = OUTPUT_DIR / f"lecture_{timestamp}.wav"
    narration_path = OUTPUT_DIR / f"lecture_{timestamp}.txt"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    narration_path.write_text(narration, encoding="utf-8")
    try:
        save_audio(narration, str(audio_path), language="hi-IN" if language.startswith("hin") else "en-US")
        audio_message = str(audio_path)
    except Exception as error:
        audio_message = f"Audio unavailable: {error}"

    print("\n" + "-" * 44)
    print("EXTRACTED CONTENT:")
    print(raw_text)
    print("\nAI NARRATION:")
    print(narration)
    print("\nAudio saved as:")
    print(audio_message)
    print("Narration text saved as:")
    print(narration_path)


def show_previous_results():
    files = sorted(OUTPUT_DIR.glob("*.wav"), reverse=True) if OUTPUT_DIR.exists() else []
    print("\nPrevious audio results:")
    if not files:
        print("No audio files have been generated yet.")
        return
    for file_path in files:
        print(f"- {file_path.name}")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Convert a lecture image or PDF into accessible narration and audio."
    )
    parser.add_argument("--demo", action="store_true", help="run the offline demonstration")
    parser.add_argument("--file", help="process an image or PDF without opening the menu")
    parser.add_argument("--language", choices=("english", "hindi"), default="english", help="language for OCR, narration, and audio")
    parser.add_argument("--list", action="store_true", help="list previous generated audio")
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    try:
        if arguments.demo:
            process_slide("demo", demo=True, language="hin+eng" if arguments.language == "hindi" else "eng")
            return
        if arguments.file:
            process_slide(arguments.file, language="hin+eng" if arguments.language == "hindi" else "eng")
            return
        if arguments.list:
            show_previous_results()
            return
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"\nError: {error}")
        return

    while True:
        print_header()
        print("1. Process a lecture slide/image/PDF")
        print("2. Run demo mode")
        print("3. View previous results")
        print("4. Exit")
        try:
            choice = input("\nChoose an option: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        try:
            if choice == "1":
                file_path = input("Enter image or PDF path: ").strip().strip('"')
                process_slide(file_path)
            elif choice == "2":
                process_slide("demo", demo=True)
            elif choice == "3":
                show_previous_results()
            elif choice == "4":
                print("Goodbye.")
                break
            else:
                print("Please choose 1, 2, 3, or 4.")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        except (FileNotFoundError, RuntimeError, ValueError) as error:
            print(f"\nError: {error}")
        try:
            input("\nPress Enter to return to the menu...")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break


if __name__ == "__main__":
    main()
