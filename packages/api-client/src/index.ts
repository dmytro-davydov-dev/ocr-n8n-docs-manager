export interface HealthResponse {
  status: string;
}

/**
 * Document lifecycle per PRD-Phase-1-Document-Ingestion (FR-106).
 */
export type DocumentStatus = "uploaded" | "queued" | "processing" | "complete" | "failed";

export interface DocumentSummary {
  id: string;
  filename: string;
  sizeBytes: number;
  status: DocumentStatus;
  createdAt: string;
  updatedAt: string;
  errorMessage?: string;
}

export type UploadProgressHandler = (percent: number) => void;

/**
 * Page-level OCR result per ADR-011-OCR-Storage-Strategy.
 */
export interface OcrPage {
  documentId: string;
  pageNumber: number;
  extractedText: string;
  confidenceScore: number;
  processingTimestamp: string;
  ocrEngineVersion: string;
}

/**
 * FR-302/303: structured contract fields validated against the backend's
 * `ExtractedContractFields` schema. Nested content keys stay snake_case
 * (they pass through as a raw dict on the backend, not through the
 * camelCase alias generator the rest of the API contract uses).
 */
export interface ExtractedContractFields {
  parties: string[];
  effective_date: string | null;
  termination_date: string | null;
  monetary_values: string[];
  key_clauses: string[];
  obligations: string[];
}

/**
 * FR-307/308: AI extraction result, traceable to its prompt and model
 * version (ADR-013).
 */
export interface ExtractionResult {
  documentId: string;
  content: ExtractedContractFields;
  confidenceScore: number;
  promptId: string;
  promptVersion: string;
  modelProvider: string;
  modelName: string;
  processingTimestamp: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class ApiClient {
  constructor(private readonly baseUrl: string) {}

  async health(): Promise<HealthResponse> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) {
      throw new ApiError(`Health check failed: ${response.status}`, response.status);
    }

    return (await response.json()) as HealthResponse;
  }

  /**
   * FR-108: list documents and their current status.
   */
  async listDocuments(): Promise<DocumentSummary[]> {
    const response = await fetch(`${this.baseUrl}/documents`);
    if (!response.ok) {
      throw new ApiError(`Failed to list documents: ${response.status}`, response.status);
    }

    return (await response.json()) as DocumentSummary[];
  }

  /**
   * FR-107: fetch the current status of a single document.
   */
  async getDocument(id: string): Promise<DocumentSummary> {
    const response = await fetch(`${this.baseUrl}/documents/${id}`);
    if (!response.ok) {
      throw new ApiError(`Failed to fetch document ${id}: ${response.status}`, response.status);
    }

    return (await response.json()) as DocumentSummary;
  }

  /**
   * FR-101/102: upload a document with progress reporting.
   * Uses XMLHttpRequest because fetch has no upload-progress event.
   */
  uploadDocument(file: File, onProgress?: UploadProgressHandler): Promise<DocumentSummary> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${this.baseUrl}/documents`);

      xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable && onProgress) {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      });

      xhr.addEventListener("load", () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText) as DocumentSummary);
          } catch {
            reject(new ApiError("Failed to parse upload response"));
          }
        } else {
          reject(new ApiError(`Upload failed: ${xhr.status}`, xhr.status));
        }
      });

      xhr.addEventListener("error", () => reject(new ApiError("Upload failed: network error")));
      xhr.addEventListener("abort", () => reject(new ApiError("Upload aborted")));

      const formData = new FormData();
      formData.append("file", file, file.name);
      xhr.send(formData);
    });
  }

  /**
   * FR-207: fetch page-level OCR output for a document.
   */
  async getOcrPages(documentId: string): Promise<OcrPage[]> {
    const response = await fetch(`${this.baseUrl}/documents/${documentId}/ocr`);
    if (!response.ok) {
      throw new ApiError(`Failed to fetch OCR pages for ${documentId}: ${response.status}`, response.status);
    }

    return (await response.json()) as OcrPage[];
  }

  /**
   * FR-307: fetch AI extraction results for a document. Resolves `null`
   * when extraction hasn't produced a result yet (still processing, or not
   * dispatched); throws `ApiError` with `status === 422` when extraction
   * ran but failed schema validation (FR-304), carrying the reason in
   * `message` for the UI to surface.
   */
  async getExtraction(documentId: string): Promise<ExtractionResult | null> {
    const response = await fetch(`${this.baseUrl}/documents/${documentId}/extraction`);
    if (response.status === 404) {
      return null;
    }
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const detail = body && typeof body.detail === "string" ? body.detail : undefined;
      throw new ApiError(
        detail ?? `Failed to fetch extraction for ${documentId}: ${response.status}`,
        response.status
      );
    }

    return (await response.json()) as ExtractionResult;
  }

  /**
   * Fetch the original document file for viewing alongside its OCR text.
   */
  async getDocumentFile(documentId: string): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/documents/${documentId}/file`);
    if (!response.ok) {
      throw new ApiError(`Failed to fetch file for ${documentId}: ${response.status}`, response.status);
    }

    return await response.blob();
  }
}
