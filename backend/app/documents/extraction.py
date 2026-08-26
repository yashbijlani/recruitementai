import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import fitz

from app.core.config import settings


@dataclass
class ExtractionResult:
    text: str
    pages: int
    method: str
    quality: float
    characters: int
    words: int
    error: str | None = None


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def text_quality(text: str) -> float:
    normalized = normalize_text(text)
    if not normalized:
        return 0.0
    chars = len(normalized)
    words = re.findall(r"\b[\w][\w+.#&-]*\b", normalized, re.UNICODE)
    replacement_ratio = normalized.count("\ufffd") / chars
    control_ratio = sum(ord(char) < 32 and char not in "\n\t\r" for char in normalized) / chars
    word_ratio = len(words) / max(1, len(normalized.split()))
    length_score = min(1.0, chars / settings.pdf_min_characters)
    return round(max(0.0, min(1.0, 0.4 * length_score + 0.3 * word_ratio + 0.3 * (1 - replacement_ratio - control_ratio))), 3)


def _result(text: str, pages: int, method: str, error: str | None = None) -> ExtractionResult:
    text = normalize_text(text)
    return ExtractionResult(text=text, pages=pages, method=method, quality=text_quality(text), characters=len(text), words=len(re.findall(r"\b[\w][\w+.#&-]*\b", text, re.UNICODE)), error=error)


def extract_pdf_text(path: str | Path) -> ExtractionResult:
    try:
        with fitz.open(path) as document:
            pages = len(document)
            primary = _result("\n\n".join(page.get_text("text", sort=True) for page in document), pages, "pdf_text")
            if primary.quality >= 0.55:
                return primary
            # Blocks preserve positioned text better for multi-column and unusual layouts.
            with_blocks = _result("\n\n".join("\n".join(block[4] for block in page.get_text("blocks", sort=True) if len(block) > 4) for page in document), pages, "pdf_text_blocks")
            if with_blocks.quality > primary.quality:
                primary = with_blocks
            if primary.quality >= 0.35:
                return primary
            try:
                import pytesseract
                from PIL import Image
                ocr_pages = []
                for page in document:
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                    ocr_pages.append(pytesseract.image_to_string(image))
                ocr = _result("\n\n".join(ocr_pages), pages, "ocr")
                if ocr.quality > primary.quality:
                    return ocr
            except Exception as ocr_error:
                primary.error = f"OCR fallback unavailable: {ocr_error}"
            return primary
    except Exception as error:
        return _result("", 0, "failed", str(error))


def extract_document_text(path: str | Path) -> ExtractionResult:
    suffix = Path(path).suffix.casefold()
    if suffix == ".pdf":
        return extract_pdf_text(path)
    if suffix == ".txt":
        try:
            return _result(Path(path).read_text(encoding="utf-8", errors="replace"), 1, "text")
        except Exception as error:
            return _result("", 0, "failed", str(error))
    if suffix == ".docx":
        try:
            from docx import Document
            document = Document(path)
            return _result("\n".join(paragraph.text for paragraph in document.paragraphs), 1, "docx_text")
        except Exception as error:
            return _result("", 0, "failed", str(error))
    return _result("", 0, "unsupported", f"Unsupported document type: {suffix}")
