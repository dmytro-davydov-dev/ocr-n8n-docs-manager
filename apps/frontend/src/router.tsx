import { createBrowserRouter } from "react-router-dom";

import { ErrorBoundary } from "./ErrorBoundary";
import { DocumentDetailPage } from "./features/documents/DocumentDetailPage";
import { DocumentsPage } from "./features/documents/DocumentsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <ErrorBoundary>
        <DocumentsPage />
      </ErrorBoundary>
    ),
  },
  {
    path: "/documents/:id",
    element: (
      <ErrorBoundary>
        <DocumentDetailPage />
      </ErrorBoundary>
    ),
  },
]);
