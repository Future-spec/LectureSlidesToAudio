# Viva Guide: Lecture Slides to Accessible Audio

## One-line explanation

This project extracts text from lecture slides, converts it into a clear narration, and makes the result available as speech for learners who benefit from audio.

## Four-member division

### Member 1: Input and OCR
- Explain the supported inputs: image files and PDFs.
- Explain OCR: Optical Character Recognition converts pixels into text.
- Explain that selectable PDF text can be read directly, while scanned pages need OCR.

### Member 2: Narration logic
- Explain why raw slide bullets are not always comfortable to listen to.
- Explain the offline demo narration and the optional AI narration path.
- Mention that formulas and fragments can be rewritten into natural sentences.

### Member 3: Audio and accessibility
- Explain local WAV generation with `pyttsx3` in the terminal app.
- Explain browser playback with the Web Speech API.
- Demonstrate play, pause, stop, and speed controls.

### Member 4: Web application and integration
- Explain the Flask routes: demo, extract, and narrate.
- Explain how the frontend sends a file with `FormData` and receives JSON.
- Show the progress steps and error message when an unsupported file is selected.

## Five-minute demonstration

1. Run `python main.py --demo` to show the complete offline workflow.
2. Start the web app with `python api\index.py`.
3. Open `http://localhost:5000` and click Try Demo.
4. Play the narration and change the speed.
5. Explain the optional real-file path and why an API key is not needed for demo mode.

## Simple viva answers

**What is OCR?** OCR recognizes letters in an image and converts them into editable text.

**Why use narration instead of reading the slide directly?** Slides contain fragments and formulas; narration turns them into connected speech.

**What happens without an AI key?** Demo mode and the built-in fallback still provide a working demonstration.

**What is the difference between local and web audio?** The terminal can save a WAV file with `pyttsx3`; the browser uses the device's speech engine for immediate playback.

**What is the limitation?** OCR quality depends on image clarity, and the teaching version processes one upload at a time.

## Core concepts to study

Python functions and exceptions, Flask routes, file uploads, OCR, JSON, text-to-speech, browser events, and accessibility-focused design.
