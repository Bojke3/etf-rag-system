import logging
import os
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

DEFAULT_OCR_LANGUAGES = ["rs_cyrillic", "en"]


class OCRHandler:
    """Minimal OCR fallback for scanned PDF files."""

    _reader = None

    def __init__(
        self,
        languages: Optional[List[str]] = None,
        zoom: float = 2.5,
        max_pages: Optional[int] = None,
    ):
        self.languages = languages or self._languages_from_env()
        self.zoom = zoom
        self.max_pages = max_pages or self._max_pages_from_env()

    def _languages_from_env(self) -> List[str]:
        value = os.getenv("ETF_RAG_OCR_LANGUAGES")
        if not value:
            return DEFAULT_OCR_LANGUAGES

        languages = [language.strip() for language in value.split(",") if language.strip()]
        return languages or DEFAULT_OCR_LANGUAGES

    def _max_pages_from_env(self) -> Optional[int]:
        value = os.getenv("ETF_RAG_OCR_MAX_PAGES")
        if not value:
            return None

        try:
            max_pages = int(value)
        except ValueError:
            logger.warning("Ignoring invalid ETF_RAG_OCR_MAX_PAGES value: %s", value)
            return None

        return max_pages if max_pages > 0 else None

    def _get_reader(self):
        if OCRHandler._reader is None:
            import easyocr

            logger.info(
                "Loading EasyOCR reader for languages: %s. The first run can take a while.",
                ", ".join(self.languages),
            )
            OCRHandler._reader = easyocr.Reader(self.languages, gpu=False)
        return OCRHandler._reader

    def extract_text_from_pdf(self, file_path: str) -> str:
        try:
            import fitz
            import numpy as np
            from PIL import Image
        except ImportError as exc:
            logger.warning("OCR dependencies are not installed: %s", exc)
            return ""

        path = Path(file_path)
        text_parts = []

        try:
            reader = self._get_reader()

            with fitz.open(path) as pdf:
                matrix = fitz.Matrix(self.zoom, self.zoom)
                page_count = len(pdf)
                pages_to_process = min(page_count, self.max_pages) if self.max_pages else page_count

                logger.info(
                    "Running OCR for %s (%s/%s pages)",
                    path.name,
                    pages_to_process,
                    page_count,
                )

                for page_number, page in enumerate(pdf, start=1):
                    if self.max_pages and page_number > self.max_pages:
                        break

                    try:
                        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                        image = Image.frombytes(
                            "RGB",
                            [pixmap.width, pixmap.height],
                            pixmap.samples,
                        )
                        page_text = reader.readtext(np.array(image), detail=0, paragraph=True)

                        if page_text:
                            text_parts.append("\n".join(page_text))
                    except Exception as exc:
                        logger.warning(
                            "OCR failed for %s page %s: %s",
                            path.name,
                            page_number,
                            exc,
                        )
        except Exception as exc:
            logger.warning("OCR failed for %s: %s", path, exc)
            return ""

        return "\n".join(text_parts)
