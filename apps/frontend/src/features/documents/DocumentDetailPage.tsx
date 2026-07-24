import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";
import type { ChipProps } from "@mui/material";
import {
  Alert,
  AppBar,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Divider,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";

import { api } from "../../api";

function confidenceColor(score: number): ChipProps["color"] {
  if (score >= 0.9) return "success";
  if (score >= 0.75) return "warning";
  return "error";
}

/**
 * OCR viewer synced to the source PDF, with per-page confidence indicators
 * (WS-01 Phase 2 milestone; PRD-Phase-2-OCR-Pipeline, ADR-011).
 */
export function DocumentDetailPage() {
  const { id = "" } = useParams<{ id: string }>();
  const [selectedPage, setSelectedPage] = useState(1);
  const [fileUrl, setFileUrl] = useState<string | null>(null);

  const documentQuery = useQuery({
    queryKey: ["document", id],
    queryFn: () => api.getDocument(id),
    refetchInterval: (query) => (query.state.data?.status === "complete" ? false : 2000),
  });

  const isComplete = documentQuery.data?.status === "complete";

  const fileQuery = useQuery({
    queryKey: ["document-file", id],
    queryFn: () => api.getDocumentFile(id),
    enabled: isComplete,
  });

  const ocrQuery = useQuery({
    queryKey: ["ocr-pages", id],
    queryFn: () => api.getOcrPages(id),
    enabled: isComplete,
  });

  useEffect(() => {
    if (!fileQuery.data) return;
    const url = URL.createObjectURL(fileQuery.data);
    setFileUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [fileQuery.data]);

  const pdfSrc = useMemo(() => (fileUrl ? `${fileUrl}#page=${selectedPage}` : undefined), [fileUrl, selectedPage]);

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Button color="inherit" component={RouterLink} to="/" sx={{ mr: 2 }}>
            ← Back
          </Button>
          <Typography variant="h6" noWrap>
            {documentQuery.data?.filename ?? "Document"}
          </Typography>
        </Toolbar>
      </AppBar>
      <Container maxWidth="lg" sx={{ py: 3 }}>
        {documentQuery.isLoading && <CircularProgress size={24} />}
        {documentQuery.isError && (
          <Alert severity="error">
            {documentQuery.error instanceof Error ? documentQuery.error.message : "Failed to load document."}
          </Alert>
        )}

        {documentQuery.data && !isComplete && (
          <Alert severity="info">
            OCR is still {documentQuery.data.status}. The viewer becomes available once processing completes.
          </Alert>
        )}

        {isComplete && (
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mt: 1, height: { md: "75vh" } }}>
            <Box sx={{ flex: 3, minHeight: 400 }}>
              {fileQuery.isLoading && <CircularProgress size={24} />}
              {pdfSrc && (
                <Box
                  component="iframe"
                  title="Document preview"
                  src={pdfSrc}
                  sx={{ width: "100%", height: "100%", minHeight: 400, border: 1, borderColor: "divider" }}
                />
              )}
            </Box>

            <Paper variant="outlined" sx={{ flex: 2, minHeight: 400, overflow: "auto" }}>
              <Typography variant="subtitle1" sx={{ p: 2, pb: 1 }}>
                OCR pages
              </Typography>
              <Divider />
              {ocrQuery.isLoading && (
                <Box sx={{ p: 2 }}>
                  <CircularProgress size={20} />
                </Box>
              )}
              <List disablePadding>
                {ocrQuery.data?.map((page) => (
                  <ListItemButton
                    key={page.pageNumber}
                    selected={page.pageNumber === selectedPage}
                    onClick={() => setSelectedPage(page.pageNumber)}
                    alignItems="flex-start"
                    sx={{ display: "block" }}
                  >
                    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
                      <Typography variant="body2" fontWeight={600}>
                        Page {page.pageNumber}
                      </Typography>
                      <Chip
                        size="small"
                        label={`${Math.round(page.confidenceScore * 100)}% confidence`}
                        color={confidenceColor(page.confidenceScore)}
                      />
                    </Stack>
                    <ListItemText
                      secondary={page.extractedText}
                      secondaryTypographyProps={{ sx: { whiteSpace: "pre-wrap" } }}
                    />
                  </ListItemButton>
                ))}
              </List>
            </Paper>
          </Stack>
        )}
      </Container>
    </>
  );
}
