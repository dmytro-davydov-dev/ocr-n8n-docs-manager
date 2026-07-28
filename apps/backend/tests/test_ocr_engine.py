import io
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from app.services import ocr_engine
from app.services.ocr_engine import (
    OcrEngineUnavailable,
    TesseractOcrEngine,
    get_ocr_engine,
)


def _load_test_font(size: int):
    """A real (scalable) font renders far more reliably for tesseract than
    Pillow's tiny built-in bitmap default -- this is a test-fixture concern
    only, not something `TesseractOcrEngine` itself depends on. Falls back
    to the default font if none of these happen to be installed, since the
    assertions below are loose enough to tolerate the default font's lower
    accuracy too."""
    from PIL import ImageFont

    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _render_text_page(lines: list[str]) -> bytes:
    """A synthetic page image, standing in for a rasterized PDF page (what
    `run_ocr` actually feeds an engine) without needing PyMuPDF here."""
    font = _load_test_font(36)
    image = Image.new("RGB", (900, 120 * len(lines)), "white")
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(lines):
        draw.text((20, 20 + i * 100), line, fill="black", font=font)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


class TesseractOcrEngineTest(unittest.TestCase):
    """ADR-010 addendum: added after paddleocr/paddlepaddle turned out to
    have a confirmed, unfixed native memory leak on CPU inference (see
    docs/architecture/ADR-010-OCR-Engine-Selection.md and Progress.md).
    Unlike PaddleOcrEngine (untested here -- heavy native dependency, see
    that class's own docstring), tesseract-ocr is light enough to actually
    exercise for real in this suite rather than only via a fake."""

    def test_recognize_page_returns_real_recognized_text(self) -> None:
        engine = TesseractOcrEngine(lang="eng")
        image_bytes = _render_text_page(["Hello Contract", "Effective Date 2026"])

        result = engine.recognize_page(image_bytes)

        self.assertIn("Contract", result.text)
        self.assertIn("Effective Date", result.text)
        self.assertGreater(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_recognize_page_preserves_line_structure(self) -> None:
        engine = TesseractOcrEngine(lang="eng")
        image_bytes = _render_text_page(["First line here", "Second line here"])

        result = engine.recognize_page(image_bytes)

        lines = result.text.splitlines()
        self.assertEqual(len(lines), 2)

    def test_repeated_calls_do_not_grow_memory(self) -> None:
        """The whole reason this engine exists: paddleocr's RSS climbed
        page-over-page within one process and OOM-crash-looped celery-worker
        on a real multi-page document (Progress.md). Confirms tesseract
        doesn't exhibit the same growth over many sequential calls."""
        import resource

        engine = TesseractOcrEngine(lang="eng")
        image_bytes = _render_text_page(["Repeated page content"])

        def rss_kb() -> int:
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        for _ in range(10):
            engine.recognize_page(image_bytes)
        before = rss_kb()
        for _ in range(30):
            engine.recognize_page(image_bytes)
        after = rss_kb()

        # Generous bound (2MB) -- this isn't asserting zero fluctuation, just
        # that 30 more calls don't meaningfully grow RSS the way paddleocr's
        # did (observed climbing by gigabytes within a single document).
        self.assertLess(after - before, 2048, f"RSS grew {after - before}KB over 30 calls")

    def test_engine_metadata(self) -> None:
        engine = TesseractOcrEngine(lang="eng")

        self.assertEqual(engine.engine_name, "tesseract")
        self.assertTrue(engine.engine_version)

    def test_raises_ocr_engine_unavailable_when_pytesseract_not_installed(self) -> None:
        with patch.dict("sys.modules", {"pytesseract": None}):
            with self.assertRaises(OcrEngineUnavailable):
                TesseractOcrEngine(lang="eng")

    def test_raises_ocr_engine_unavailable_when_tesseract_binary_missing(self) -> None:
        import pytesseract

        with patch.object(
            pytesseract, "get_tesseract_version", side_effect=RuntimeError("not found")
        ):
            with self.assertRaises(OcrEngineUnavailable):
                TesseractOcrEngine(lang="eng")


class GetOcrEngineWiringTest(unittest.TestCase):
    """FR/WS-03 Done Criteria: OCR engine is swappable via `OCR_ENGINE`
    config alone. Covers the wiring added alongside `TesseractOcrEngine`,
    not engine-internal behavior (covered above)."""

    def setUp(self) -> None:
        get_ocr_engine.cache_clear()

    def tearDown(self) -> None:
        get_ocr_engine.cache_clear()

    def test_ocr_engine_tesseract_uses_configured_language(self) -> None:
        with patch.object(ocr_engine.settings, "ocr_engine", "tesseract"), patch.object(
            ocr_engine.settings, "ocr_tesseract_lang", "por"
        ):
            engine = get_ocr_engine()

        self.assertIsInstance(engine, TesseractOcrEngine)
        self.assertEqual(engine._lang, "por")

    def test_unknown_ocr_engine_raises_unavailable_and_lists_tesseract(self) -> None:
        with patch.object(ocr_engine.settings, "ocr_engine", "not-a-real-engine"):
            with self.assertRaises(OcrEngineUnavailable) as ctx:
                get_ocr_engine()

        self.assertIn("tesseract", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
