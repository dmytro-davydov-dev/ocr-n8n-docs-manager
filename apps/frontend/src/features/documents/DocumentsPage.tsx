import { useQuery } from "@tanstack/react-query";
import { AppBar, Box, Chip, Container, Stack, Toolbar, Typography } from "@mui/material";

import { api } from "../../api";
import { DocumentList } from "./DocumentList";
import { UploadDropzone } from "./UploadDropzone";

function HealthChip() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.health(),
  });

  const label = isLoading ? "checking backend..." : isError ? "backend unreachable" : `backend: ${data?.status}`;
  const color = isLoading ? "default" : isError ? "error" : "success";

  return <Chip size="small" label={label} color={color} variant="outlined" sx={{ borderColor: "inherit" }} />;
}

export function DocumentsPage() {
  return (
    <>
      <AppBar position="static">
        <Toolbar sx={{ justifyContent: "space-between" }}>
          <Typography variant="h6">Contract Review MVP</Typography>
          <HealthChip />
        </Toolbar>
      </AppBar>
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Stack spacing={3}>
          <Box>
            <Typography variant="h5" gutterBottom>
              Documents
            </Typography>
            <Typography color="text.secondary">
              Upload a PDF to start processing. Status updates automatically.
            </Typography>
          </Box>
          <UploadDropzone />
          <DocumentList />
        </Stack>
      </Container>
    </>
  );
}
