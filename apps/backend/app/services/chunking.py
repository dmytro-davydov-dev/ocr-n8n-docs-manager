"""Document chunking (ADR-018): configurable token limits/overlap, with
page and character-offset metadata on every chunk. Chunking is deterministic
given the same OCR pages and config, so re-running it (e.g. after a partial
embedding failure) always reproduces the same chunk boundaries/indices --
that determinism is what makes per-chunk upsert idempotent (ADR-008).
"""

from dataclasses import dataclass

from app.core.config import settings
from app.models.ocr_page import OcrPage


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    page_number: int
    start_offset: int
    end_offset: int
    text: str
    token_count: int


def chunk_pages(
    pages: list[OcrPage],
    *,
    token_limit: int | None = None,
    overlap_tokens: int | None = None,
) -> list[TextChunk]:
    limit = token_limit if token_limit is not None else settings.chunk_token_limit
    overlap = overlap_tokens if overlap_tokens is not None else settings.chunk_overlap_tokens
    if limit <= 0:
        raise ValueError("chunk token limit must be positive")
    if overlap >= limit:
        raise ValueError("chunk overlap must be smaller than the chunk token limit")

    chunks: list[TextChunk] = []
    chunk_index = 0
    step = limit - overlap

    for page in sorted(pages, key=lambda p: p.page_number):
        words = page.extracted_text.split()
        if not words:
            continue

        offsets: list[int] = []
        cursor = 0
        for word in words:
            start = page.extracted_text.index(word, cursor)
            offsets.append(start)
            cursor = start + len(word)

        i = 0
        while i < len(words):
            window = words[i : i + limit]
            last = i + len(window) - 1
            chunks.append(
                TextChunk(
                    chunk_index=chunk_index,
                    page_number=page.page_number,
                    start_offset=offsets[i],
                    end_offset=offsets[last] + len(words[last]),
                    text=" ".join(window),
                    token_count=len(window),
                )
            )
            chunk_index += 1
            if i + limit >= len(words):
                break
            i += step

    return chunks
