import { createBrowserRouter } from "react-router-dom";

import { ErrorBoundary } from "./ErrorBoundary";
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
]);
