# Frontend

React + TypeScript + Vite SPA for uploading contracts, watching them move through the processing pipeline, and reviewing AI-extracted fields. See [[architecture/templates/ADR-005-React-TypeScript-Vite|ADR-005]] for the stack rationale.

## Location

`apps/frontend/`

## Stack

- React 18 + TypeScript, built with Vite 5
- React Router 6 (`src/router.tsx`) for client-side routing
- TanStack React Query 5 for server state/polling
- MUI (Material UI) 6 + Emotion for components/styling
- `@contract-review/api-client` (`packages/api-client`) — the hand-written TypeScript client shared with the rest of the monorepo; not yet generated from `packages/api-client/openapi.json`, which is a separate, checked-in artifact kept in sync manually

## Structure

```text
apps/frontend/
  src/
    main.tsx                # entry point; installs the API mock if enabled
    router.tsx               # route table: "/" and "/documents/:id"
    api.ts                   # ApiClient instance, reads VITE_API_BASE_URL
    queryClient.ts            # shared React Query client
    ErrorBoundary.tsx
    features/documents/
      DocumentsPage.tsx        # upload + document list ("/")
      DocumentList.tsx
      UploadDropzone.tsx        # drag-and-drop upload with per-file progress
      DocumentDetailPage.tsx    # PDF viewer + OCR panel + extraction panel ("/documents/:id")
      ReviewPanel.tsx           # review workspace: edit/save draft/submit/approve/reject/revise/archive, audit history
    mocks/
      mockDocumentsApi.ts       # dev-only mock of the /documents API surface
  Dockerfile
  vite.config.ts
  package.json
```

## Pages

- `/` — `DocumentsPage`: upload dropzone plus a live-polling list of documents and their status.
- `/documents/:id` — `DocumentDetailPage`: PDF viewer, per-page OCR text with confidence chips, the AI extraction panel, and (once a document is `complete`) the `ReviewPanel` review workspace.

## Talking to the backend

`src/api.ts` constructs a single `ApiClient` pointed at `VITE_API_BASE_URL` (default `http://localhost:8000/api`). All document/review/OCR/extraction calls go through this client — see `packages/api-client/src/index.ts` for the full method list and types.

## Dev-only API mock

`src/mocks/mockDocumentsApi.ts` intercepts `fetch` and `XMLHttpRequest` to simulate the `/documents` API (upload progress, a fake status lifecycle `uploaded → queued → processing → complete`, fabricated OCR/extraction output, and a review store that mirrors the backend's `ADR-014` transition table) without a running backend.

It is gated by `VITE_ENABLE_API_MOCKS` (default `false` — the app talks to the real backend by default; set to `true` for a frontend-only demo). This flag must be forwarded into the container's environment in `docker-compose.yml` for it to have any effect — it previously wasn't (see `docs/architecture/Progress.md` Completed log), which silently forced every containerized run onto the mock regardless of `.env`.

## Local development

Outside Docker:

```bash
cd apps/frontend
npm install
npm run dev       # vite --host 0.0.0.0 --port 5173
```

Via Docker Compose (recommended — matches production wiring and backend dependency):

```bash
docker compose up --build frontend
```

Other scripts (`apps/frontend/package.json`):

```bash
npm run build      # tsc -b && vite build
npm run preview    # vite preview --host 0.0.0.0 --port 4173
```

## Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:8000/api` |
| `VITE_ENABLE_API_MOCKS` | Use the dev-only mock instead of the real backend | `false` |

## Known gaps

Per [[architecture/Progress.md]]: the review workspace (`ReviewPanel`) and the rest of the frontend have never been click-tested in an actual browser in this environment (verification has been `tsc -b` / `vite build` plus the mock's own transition logic). There is currently no frontend UI for search/chat (`GET /api/search`, `POST /api/chat`) — Phase 5's PRD scopes those as backend-only.

## Related

- [[architecture/templates/PRD-Phase-1-Document-Ingestion]]
- [[architecture/templates/PRD-Phase-2-OCR-Pipeline]]
- [[architecture/templates/PRD-Phase-3-AI-Extraction]]
- [[architecture/templates/PRD-Phase-4-Contract-Review-UI]]
- [[architecture/templates/ADR-005-React-TypeScript-Vite]]
- [[architecture/templates/ADR-014-Review-State-Management]]
- [[workstreams/WS-01-Frontend]]
