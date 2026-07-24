# ADR-010 — OCR Engine Selection

**Status:** Accepted  
**Date:** 2026-07-24

# Context

The platform requires a self-hosted OCR engine that integrates with Docker, Celery, and n8n while supporting scanned PDFs and images.

# Decision

Use **PaddleOCR** as the primary OCR engine behind an internal OCR service.

# Rationale

- High OCR accuracy
- Good support for multi-language documents
- Container-friendly
- Active open-source community
- Suitable for future layout-aware extraction

# Alternatives Considered

- Tesseract
- OCRmyPDF
- Cloud OCR APIs

# Consequences

## Positive

- Fully self-hosted
- No vendor lock-in
- Easy Docker deployment
- Works offline

## Negative

- Higher CPU usage than Tesseract
- Additional model management

## Risks

- Future model upgrades may require regression testing.

# Related Documents

- PRD-Phase-2-OCR-Pipeline
- ADR-009-n8n
