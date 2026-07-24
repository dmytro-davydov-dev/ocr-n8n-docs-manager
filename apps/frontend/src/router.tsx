import { useQuery } from "@tanstack/react-query";
import { createBrowserRouter } from "react-router-dom";
import { AppBar, Box, CircularProgress, Container, Paper, Toolbar, Typography } from "@mui/material";

import { ErrorBoundary } from "./ErrorBoundary";
import { api } from "./api";

function HomePage() {
  const { data, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health(),
  });

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6">Contract Review MVP</Typography>
        </Toolbar>
      </AppBar>
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>
            Foundation Environment
          </Typography>
          <Typography color="text.secondary" paragraph>
            Frontend shell is running and connected to backend health checks.
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
            <Typography variant="body1">Backend status:</Typography>
            {isLoading ? <CircularProgress size={18} /> : <Typography>{data?.status ?? "unknown"}</Typography>}
          </Box>
        </Paper>
      </Container>
    </>
  );
}

export const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <ErrorBoundary>
        <HomePage />
      </ErrorBoundary>
    ),
  },
]);
