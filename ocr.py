"""Text extraction from image files and PDF pages."""

from pathlib import Path


def extract_text(file_path: str) -> str:
    """Extract text from an image or PDF using local OCR tools."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    try:
        import pytesseract
        from PIL import Image
    except ImportError as error:
        raise RuntimeError(
            "OCR packages are missing. Run: pip install -r requirements.txt"
        ) from error

    if path.suffix.lower() == ".pdf":
        return _extract_pdf_text(path, pytesseract)

    try:
        return pytesseract.image_to_string(Image.open(path)).strip()
    except Exception as error:
        raise RuntimeError(
            "Could not read the image. Check that Tesseract OCR is installed."
        ) from error


def _extract_pdf_text(path: Path, pytesseract) -> str:
    try:
        import fitz
    except ImportError as error:
        raise RuntimeError(
            "PDF support is missing. Run: pip install -r requirements.txt"
        ) from error

    pages = []
    try:
        document = fitz.open(path)
        for page_number, page in enumerate(document, start=1):
            direct_text = page.get_text().strip()
            if direct_text:
                pages.append(f"Page {page_number}:\n{direct_text}")
                continue

            image = _render_page(page)
            page_text = pytesseract.image_to_string(image).strip()
            if page_text:
                pages.append(f"Page {page_number}:\n{page_text}")
    except Exception as error:
        raise RuntimeError("Could not read this PDF file.") from error

    return "\n\n".join(pages)


def _render_page(page):
    from PIL import Image
    import fitz

    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    return Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
