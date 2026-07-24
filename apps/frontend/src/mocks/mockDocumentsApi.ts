import type { DocumentStatus, DocumentSummary } from "@contract-review/api-client";

/**
 * Dev-only mock for the document ingestion API (PRD-Phase-1-Document-Ingestion).
 *
 * WS-02 (Backend & Data) has not yet shipped the `/documents` endpoints for
 * Phase 1. Per WS-01's dependency note, a mocked contract is sufficient to
 * unblock frontend work: this module intercepts `fetch` (list/get) and
 * `XMLHttpRequest` (upload, for progress events) so the UI can be built and
 * demoed against a realistic lifecycle. Remove this file once WS-02 delivers
 * the real endpoints and point `VITE_API_BASE_URL` at them.
 */

const DOCUMENTS_PATH = "/documents";
const LIFECYCLE: DocumentStatus[] = ["uploaded", "queued", "processing", "complete"];

let store: DocumentSummary[] = [];
let idCounter = 0;

function nowIso(): string {
  return new Date().toISOString();
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function advanceLifecycle(id: string): void {
  const step = () => {
    const doc = store.find((d) => d.id === id);
    if (!doc) return;
    const idx = LIFECYCLE.indexOf(doc.status);
    if (idx === -1 || idx >= LIFECYCLE.length - 1) return;
    doc.status = LIFECYCLE[idx + 1];
    doc.updatedAt = nowIso();
    if (doc.status !== "complete") {
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
  const singleUrlPattern = new RegExp(`^${escapeRegExp(listUrl)}/(.+)$`);

  window.fetch = async (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

    if (url === listUrl && (!init?.method || init.method === "GET")) {
      const sorted = [...store].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
      return jsonResponse(sorted);
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
