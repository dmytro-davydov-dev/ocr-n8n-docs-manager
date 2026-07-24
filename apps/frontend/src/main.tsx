import React from "react";
import ReactDOM from "react-dom/client";
import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";

import { queryClient } from "./queryClient";
import { router } from "./router";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#0f4c81",
    },
    secondary: {
      main: "#f77f00",
    },
  },
});

function renderApp() {
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </ThemeProvider>
    </React.StrictMode>
  );
}

// WS-02's `/documents` endpoints (PRD-Phase-1) don't exist yet. Until they
// ship, a dev-only mock stands in for the contract so the UI can be built
// and demoed. Toggle off via VITE_ENABLE_API_MOCKS=false once real
// endpoints are available.
const mocksEnabled = import.meta.env.DEV && import.meta.env.VITE_ENABLE_API_MOCKS !== "false";

if (mocksEnabled) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";
  import("./mocks/mockDocumentsApi").then(({ installDocumentMocks }) => {
    installDocumentMocks(baseUrl);
    renderApp();
  });
} else {
  renderApp();
}
