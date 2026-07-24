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
}
