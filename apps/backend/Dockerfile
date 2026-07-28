FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ccache \
    libpq-dev \
    curl \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# PaddlePaddle JIT-compiles a native C++ extension the first time PaddleOCR()
# is instantiated, specific to this image's exact CPU/arch (no prebuilt wheel
# covers every target -- confirmed live: this compile alone spiked
# celery-worker's RSS from ~330MB to a 6GiB limit and got OOM-killed (signal
# 9) before it could finish, logged as "No ccache found. Please be aware
# that recompiling all source files may be required"). Because a fresh
# Celery pool worker is forked from the pre-fork parent (which never ran
# this), a crash here became an unrecoverable compile -> OOM -> new worker ->
# compile -> OOM loop at runtime -- no WORKER_MEMORY_LIMIT fixed it, since
# the compile itself was what was unbounded, not steady-state OCR inference.
# Running it here, at build time, isn't competing with celery-worker's
# runtime memory limit or any other running container, so it bakes the
# compiled extension into this image layer -- no container instance built
# from this image has to compile it live again. See
# docs/architecture/Progress.md.
#
# Note: eliminating this compile alone did NOT fix the OOM crash seen with
# real documents -- see Progress.md's follow-up entry. It's kept because
# it's still a real, verified improvement (removes a genuine compile-in-a-
# crash-loop failure mode), just not sufficient by itself.
RUN python -c "from paddleocr import PaddleOCR; PaddleOCR(use_angle_cls=True, lang='en', show_log=False)"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
