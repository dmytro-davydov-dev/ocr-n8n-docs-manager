"""Provider-agnostic OCR engine abstraction (ADR-010).

The engine is selected purely by the `OCR_ENGINE` config value (WS-03 Done
Criteria: "OCR engine ... swappable via configuration, not code changes").
Callers depend only on the `OcrEngine` protocol; `get_ocr_engine()` is the
single place that knows which concrete implementation backs it.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from app.core.config import settings


@dataclass(frozen=True)
class PageOcrResult:
    text: str
    confidence: float


class OcrEngine(Protocol):
    engine_name: str
    engine_version: str

    def recognize_page(self, image_bytes: bytes) -> PageOcrResult: ...


class OcrEngineUnavailable(RuntimeError):
    """Raised when the configured engine's dependencies aren't installed.

    This is a terminal, operator-actionable failure (bad deployment config),
    not a transient one — callers must not blindly retry it (ADR-008).
    """


class PaddleOcrEngine:
    """ADR-010's chosen engine. paddleocr/paddlepaddle are heavy native
    dependencies, so the import is deferred to first use: importing this
    module (and running unit tests against a fake OcrEngine) must not
    require them to be installed."""

    engine_name = "paddleocr"

    def __init__(self, lang: str = "en") -> None:
        try:
            from paddleocr import PaddleOCR
            import paddleocr as paddleocr_pkg
        except ImportError as exc:  # pragma: no cover - exercised only when the dep is missing
            raise OcrEngineUnavailable(
                "OCR_ENGINE=paddleocr but the paddleocr package is not installed"
            ) from exc

        self.engine_version = getattr(paddleocr_pkg, "__version__", "unknown")
        self._ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)

    def recognize_page(self, image_bytes: bytes) -> PageOcrResult:
        import numpy as np
        from PIL import Image
        from io import BytesIO

        image = np.array(Image.open(BytesIO(image_bytes)).convert("RGB"))
        result = self._ocr.ocr(image, cls=True)

        lines: list[str] = []
        scores: list[float] = []
        for page_result in result or []:
            for _box, (text, score) in page_result or []:
                lines.append(text)
                scores.append(score)

        confidence = sum(scores) / len(scores) if scores else 0.0
        return PageOcrResult(text="\n".join(lines), confidence=confidence)


class TesseractOcrEngine:
    """ADR-010 addendum engine, added after PaddleOCR/PaddlePaddle turned out
    to have a confirmed, upstream, unfixed native (C++) memory leak on CPU
    inference across sequential calls within one process (multiple open
    PaddlePaddle/PaddleOCR GitHub issues; reproduced live here: RSS climbed
    page-over-page in `run_ocr`'s loop and OOM-crash-looped celery-worker on
    any real multi-page document, immune to `gc.collect()` since the leak
    lives below what Python-level GC can reach -- see
    docs/architecture/Progress.md and this ADR's addendum). Tesseract is
    CPU-native with no ML-framework memory-pool/runtime-cache layer to leak,
    at some cost in accuracy for complex/rotated/multilingual layouts versus
    PaddleOCR's PP-OCRv4 models."""

    engine_name = "tesseract"

    def __init__(self, lang: str = "eng") -> None:
        try:
            import pytesseract
        except ImportError as exc:
            raise OcrEngineUnavailable(
                "OCR_ENGINE=tesseract but the pytesseract package is not installed"
            ) from exc

        try:
            version = pytesseract.get_tesseract_version()
        except Exception as exc:
            # pytesseract raises TesseractNotFoundError (an EnvironmentError
            # subclass) when the `tesseract` binary itself isn't on PATH --
            # caught broadly since the exact exception type/module has moved
            # across pytesseract versions.
            raise OcrEngineUnavailable(
                "OCR_ENGINE=tesseract but the tesseract-ocr binary is not "
                "installed or not on PATH"
            ) from exc

        self._pytesseract = pytesseract
        self._lang = lang
        self.engine_version = str(version)

    def recognize_page(self, image_bytes: bytes) -> PageOcrResult:
        from io import BytesIO

        from PIL import Image

        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        data = self._pytesseract.image_to_data(
            image, lang=self._lang, output_type=self._pytesseract.Output.DICT
        )

        # Group words back into lines (block/par/line triple) rather than
        # joining every recognized word with no structure, so the output
        # text shape roughly matches PaddleOcrEngine's line-per-line result.
        lines: dict[tuple[int, int, int], list[str]] = {}
        confidences: list[float] = []
        for i, raw_text in enumerate(data["text"]):
            text = raw_text.strip()
            if not text:
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            lines.setdefault(key, []).append(text)
            try:
                conf = float(data["conf"][i])
            except (TypeError, ValueError):
                continue
            if conf >= 0:  # tesseract reports -1 confidence for non-text regions
                confidences.append(conf / 100.0)

        text = "\n".join(" ".join(words) for words in lines.values())
        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return PageOcrResult(text=text, confidence=confidence)


class NullOcrEngine:
    """No-op engine for OCR_ENGINE=null. Exists so local/dev environments
    without the paddleocr native dependencies can still boot the worker;
    it must be explicitly configured, never a silent fallback for a
    missing paddleocr install."""

    engine_name = "null"
    engine_version = "0"

    def recognize_page(self, image_bytes: bytes) -> PageOcrResult:
        return PageOcrResult(text="", confidence=0.0)


_ENGINES = {
    "paddleocr": PaddleOcrEngine,
    "tesseract": TesseractOcrEngine,
    "null": NullOcrEngine,
}


@lru_cache(maxsize=1)
def get_ocr_engine() -> OcrEngine:
    engine_cls = _ENGINES.get(settings.ocr_engine)
    if engine_cls is None:
        raise OcrEngineUnavailable(
            f"Unknown OCR_ENGINE '{settings.ocr_engine}'. Valid values: {sorted(_ENGINES)}"
        )
    if engine_cls is TesseractOcrEngine:
        return TesseractOcrEngine(lang=settings.ocr_tesseract_lang)
    return engine_cls()
