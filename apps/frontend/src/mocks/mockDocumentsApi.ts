import type {
  DocumentStatus,
  DocumentSummary,
  ExtractionResult,
  OcrPage,
} from "@contract-review/api-client";

/**
 * Dev-only mock for the document ingestion + OCR API (PRD-Phase-1-Document-
 * Ingestion, PRD-Phase-2-OCR-Pipeline).
 *
 * WS-02 (Backend & Data) has not yet shipped the `/documents` endpoints.
 * Per WS-01's dependency note, a mocked contract is sufficient to unblock
 * frontend work: this module intercepts `fetch` (list/get/ocr/file) and
 * `XMLHttpRequest` (upload, for progress events) so the UI can be built and
 * demoed against a realistic lifecycle. Remove this file once WS-02
 * delivers the real endpoints and point `VITE_API_BASE_URL` at them.
 */

const DOCUMENTS_PATH = "/documents";
const LIFECYCLE: DocumentStatus[] = ["uploaded", "queued", "processing", "complete"];

let store: DocumentSummary[] = [];
let idCounter = 0;
const fileBlobs = new Map<string, Blob>();
const ocrResults = new Map<string, OcrPage[]>();
const extractionResults = new Map<string, ExtractionResult>();

function nowIso(): string {
  return new Date().toISOString();
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Rough page-count guess from file size, purely for a plausible-looking demo. */
function estimatePageCount(sizeBytes: number): number {
  return Math.min(6, Math.max(1, Math.round(sizeBytes / 50_000)));
}

function generateOcrPages(doc: DocumentSummary): OcrPage[] {
  const pageCount = estimatePageCount(doc.sizeBytes);
  return Array.from({ length: pageCount }, (_, index) => {
    const pageNumber = index + 1;
    // Vary confidence so the UI can demo high/medium/low indicators.
    const confidenceScore = pageNumber === 2 ? 0.68 : Math.round((0.9 + Math.random() * 0.09) * 100) / 100;
    return {
      documentId: doc.id,
      pageNumber,
      extractedText:
        `[Mock OCR output for "${doc.filename}", page ${pageNumber} of ${pageCount}]\n\n` +
        "This is placeholder extracted text standing in for WS-03's OCR pipeline output " +
        "(PRD-Phase-2-OCR-Pipeline). Once the real OCR service is wired up via n8n/Celery, " +
        "this text will reflect the actual scanned content of the document.",
      confidenceScore,
      processingTimestamp: nowIso(),
      ocrEngineVersion: "mock-ocr-0.1.0",
    };
  });
}

/** Standing in for WS-03's LLM extraction pipeline (PRD-Phase-3-AI-Extraction). */
function generateExtraction(doc: DocumentSummary): ExtractionResult {
  return {
    documentId: doc.id,
    content: {
      parties: ["Acme Corp", "Globex Inc"],
      effective_date: "2026-01-01",
      termination_date: "2027-01-01",
      monetary_values: ["$12,000"],
      key_clauses: ["Confidentiality", "Limitation of liability"],
      obligations: ["Acme shall deliver monthly reports", "Globex shall pay within 30 days"],
    },
    confidenceScore: 0.87,
    promptId: "contract_extraction",
    promptVersion: "mock-v1",
    modelProvider: "mock-llm",
    modelName: "mock-model-1",
    processingTimestamp: nowIso(),
  };
}

function advanceLifecycle(id: string): void {
  const step = () => {
    const doc = store.find((d) => d.id === id);
    if (!doc) return;
    const idx = LIFECYCLE.indexOf(doc.status);
    if (idx === -1 || idx >= LIFECYCLE.length - 1) return;
    doc.status = LIFECYCLE[idx + 1];
    doc.updatedAt = nowIso();

    if (doc.status === "complete") {
      ocrResults.set(doc.id, generateOcrPages(doc));
      setTimeout(() => extractionResults.set(doc.id, generateExtraction(doc)), 1500);
    } else {
      setTimeout(step, 1500 + Math.random() * 1500);
    }
  };
  setTimeout(step, 1000 + Math.random() * 1000);
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Minimal XHR-compatible shim so ApiClient.uploadDocument (which relies on
 * XMLHttpRequest for upload-progress events) works against the mock without
 * a real network layer. Non-matching requests are delegated to a real XHR. */
class MockCapableXHR extends EventTarget {
  public upload = new EventTarget();
  public status = 0;
  public responseText = "";

  private isMocked = false;
  private method = "";
  private url = "";
  private real: XMLHttpRequest | null = null;

  constructor(
    private readonly RealXHR: typeof XMLHttpRequest,
    private readonly baseUrl: string
  ) {
    super();
  }

  open(method: string, url: string): void {
    this.method = method;
    this.url = url;
    this.isMocked = method === "POST" && url === `${this.baseUrl}${DOCUMENTS_PATH}`;

    if (!this.isMocked) {
      this.real = new this.RealXHR();
      this.real.open(method, url);
      this.real.upload.addEventListener("progress", (event) => {
        const progress = event as ProgressEvent;
        this.upload.dispatchEvent(
          new ProgressEvent("progress", {
            lengthComputable: progress.lengthComputable,
            loaded: progress.loaded,
            total: progress.total,
          })
        );
      });
      (["load", "error", "abort"] as const).forEach((type) => {
        this.real!.addEventListener(type, () => {
          this.status = this.real!.status;
          this.responseText = this.real!.responseText;
          this.dispatchEvent(new Event(type));
        });
      });
    }
  }

  send(body?: Document | XMLHttpRequestBodyInit | null): void {
    if (this.isMocked) {
      handleMockUpload(this, body as FormData);
      return;
    }
    this.real?.send(body);
  }
}

function handleMockUpload(xhr: MockCapableXHR, formData: FormData): void {
  const file = formData.get("file") as File | null;
  const total = file?.size ?? 1024;
  let loaded = 0;

  const interval = setInterval(() => {
    loaded = Math.min(total, loaded + Math.max(1, Math.ceil(total / 8)));
    xhr.upload.dispatchEvent(new ProgressEvent("progress", { lengthComputable: true, loaded, total }));

    if (loaded >= total) {
      clearInterval(interval);
      idCounter += 1;
      const doc: DocumentSummary = {
        id: `doc-${Date.now()}-${idCounter}`,
        filename: file?.name ?? "unknown.pdf",
        sizeBytes: total,
        status: "uploaded",
        createdAt: nowIso(),
        updatedAt: nowIso(),
      };
      store = [doc, ...store];
      if (file) {
        fileBlobs.set(doc.id, file);
      }
      advanceLifecycle(doc.id);

      xhr.status = 201;
      xhr.responseText = JSON.stringify(doc);
      xhr.dispatchEvent(new Event("load"));
    }
  }, 120);
}

export function installDocumentMocks(baseUrl: string): void {
  const realFetch = window.fetch.bind(window);
  const listUrl = `${baseUrl}${DOCUMENTS_PATH}`;
  const ocrUrlPattern = new RegExp(`^${escapeRegExp(listUrl)}/([^/]+)/ocr$`);
  const extractionUrlPattern = new RegExp(`^${escapeRegExp(listUrl)}/([^/]+)/extraction$`);
  const fileUrlPattern = new RegExp(`^${escapeRegExp(listUrl)}/([^/]+)/file$`);
  const singleUrlPattern = new RegExp(`^${escapeRegExp(listUrl)}/([^/]+)$`);

  window.fetch = async (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

    if (url === listUrl && (!init?.method || init.method === "GET")) {
      const sorted = [...store].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
      return jsonResponse(sorted);
    }

    const ocrMatch = url.match(ocrUrlPattern);
    if (ocrMatch) {
      return jsonResponse(ocrResults.get(ocrMatch[1]) ?? []);
    }

    const extractionMatch = url.match(extractionUrlPattern);
    if (extractionMatch) {
      const extraction = extractionResults.get(extractionMatch[1]);
      return extraction ? jsonResponse(extraction) : jsonResponse({ detail: "Extraction not found" }, 404);
    }

    const fileMatch = url.match(fileUrlPattern);
    if (fileMatch) {
      const blob = fileBlobs.get(fileMatch[1]);
      return blob
        ? new Response(blob, { status: 200, headers: { "Content-Type": "application/pdf" } })
        : jsonResponse({ message: "File not found" }, 404);
    }

    const singleMatch = url.match(singleUrlPattern);
    if (singleMatch) {
      const doc = store.find((d) => d.id === singleMatch[1]);
      return doc ? jsonResponse(doc) : jsonResponse({ message: "Document not found" }, 404);
    }

    return realFetch(input, init);
  };

  const RealXHR = window.XMLHttpRequest;
  window.XMLHttpRequest = class extends MockCapableXHR {
    constructor() {
      super(RealXHR, baseUrl);
    }
  } as unknown as typeof XMLHttpRequest;
}
