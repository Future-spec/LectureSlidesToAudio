# Lecture Slides to Accessible Audio

LectureSlidesToAudio turns lecture images or PDFs into listening-friendly narration. It has two modes:

- A local Python terminal app that extracts text, creates narration, and saves WAV audio.
- A Flask web app that runs locally and deploys to Vercel. The browser uses Web Speech API playback.

For a group presentation, use [VIVA_GUIDE.md](VIVA_GUIDE.md). It divides the explanation into OCR, narration, audio accessibility, and Flask integration.

## Features

- Offline demo with no file, API key, or Tesseract installation
- Image and PDF input in the terminal workflow
- Selectable PDF text extraction with scanned-page OCR fallback
- Optional OpenAI-compatible narration, vision extraction, and structured study coaching
- AI study kit with a summary, quick quiz, flashcards, and next steps
- Source-grounded lesson tutor for follow-up questions
- Interactive quiz scoring and resumable browser history stored locally
- Paragraph-level narration playback with local completion progress
- Structured multi-slide deck map with slide-specific playback
- Browser upload, progress steps, extracted text, narration, and playback speed control
- Upload limit and upstream request timeout suitable for serverless deployment

## Project structure

```text
LectureSlidesToAudio/
  app.py             Flask app
  api/index.py       Vercel entry point
  public/            Browser interface
  main.py            Terminal workflow
  ocr.py             Image/PDF extraction
  ai.py              Narration generation and offline fallback
  speech.py          Local WAV text-to-speech
  requirements.txt   Python dependencies
  vercel.json        Vercel Python runtime configuration
```

## Local setup

Use Python 3.10 or newer:

```powershell
cd LectureSlidesToAudio
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start the web app:

```powershell
python app.py
```

Open `http://localhost:5000`. Run the demo from the terminal with:

```powershell
python main.py --demo
```

The interactive menu is available with `python main.py`. Generated WAV and text files are written to `output/`, which is ignored by Git.

## Optional AI and OCR setup

Demo mode works without external services. For real image OCR in the terminal app, install the Tesseract application and make sure it is on `PATH`. For AI narration or web image extraction, configure environment variables without committing secrets:

Copy `.env.example` to `.env`, then replace the placeholder key:

```powershell
Copy-Item .env.example .env
```

```powershell
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_MODEL = "gpt-4o-mini"
$env:OPENAI_BASE_URL = "https://api.openai.com/v1"
```

The Flask app loads `.env` automatically when `python-dotenv` is installed. The header shows `AI ready` when the key is active; `Offline mode` means the app is deliberately using its local fallback.

The web app uses the configured OpenAI-compatible model for narration, the Study kit tab, and the lesson tutor. The study kit is returned as structured JSON and includes a short summary, three quiz prompts, flashcards, and suggested next steps. PDFs are also returned as structured slide records for the Deck map, where each slide can be played independently. The tutor is constrained to the current lesson source. Narration paragraphs can be replayed individually, and completion state is saved locally with the lesson history. If the key is missing or the provider is unavailable, the app falls back to deterministic offline narration, study coaching, and question answering so the core demo still works.

## Deploy to Vercel

The Vercel configuration points requests to `api/index.py` and serves the browser files from `public/` through Flask. Set the Vercel **Root Directory** to `LectureSlidesToAudio`, then run from this project folder:

```powershell
npm install -g vercel
vercel
vercel --prod
```

Add `OPENAI_API_KEY`, `OPENAI_MODEL`, and optionally `OPENAI_BASE_URL` in the Vercel project environment settings. The deployed app can process selectable-text PDFs without a key and can narrate supplied text through its offline fallback. Image extraction requires an AI key. Vercel functions are stateless and do not create downloadable server-side audio; browser playback uses the device speech engine.

## Workflow

1. Select an image or PDF.
2. Extract text with direct PDF parsing, OCR, or optional vision AI.
3. Convert slide fragments into a natural narration.
4. Read the narration in the browser or save WAV audio locally through the terminal app.

## Limitations and next steps

The prototype processes one upload at a time and does not persist history or user accounts. A production version should add authentication, object storage, a database, and a background job for long PDFs. It could also add slide-by-slide audio merging and downloadable browser audio.
