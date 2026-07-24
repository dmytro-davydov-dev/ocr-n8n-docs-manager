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
    "null": NullOcrEngine,
}


@lru_cache(maxsize=1)
def get_ocr_engine() -> OcrEngine:
    engine_cls = _ENGINES.get(settings.ocr_engine)
    if engine_cls is None:
        raise OcrEngineUnavailable(
            f"Unknown OCR_ENGINE '{settings.ocr_engine}'. Valid values: {sorted(_ENGINES)}"
        )
    return engine_cls()
