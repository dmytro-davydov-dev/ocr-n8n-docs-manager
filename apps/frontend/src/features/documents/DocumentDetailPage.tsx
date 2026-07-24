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

import { ApiError } from "@contract-review/api-client";

import { api } from "../../api";

function confidenceColor(score: number): ChipProps["color"] {
  if (score >= 0.9) return "success";
  if (score >= 0.75) return "warning";
  return "error";
}

function FieldList({ label, values }: { label: string; values: string[] }) {
  if (values.length === 0) return null;
  return (
    <Box sx={{ mb: 1.5 }}>
      <Typography variant="body2" fontWeight={600}>
        {label}
      </Typography>
      <Stack component="ul" sx={{ m: 0, pl: 2.5 }}>
        {values.map((value, index) => (
          <Typography key={index} component="li" variant="body2">
            {value}
          </Typography>
        ))}
      </Stack>
    </Box>
  );
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

  const extractionQuery = useQuery({
    queryKey: ["extraction", id],
    queryFn: () => api.getExtraction(id),
    enabled: isComplete,
    // Extraction runs after OCR completes (FR-301); keep polling until a
    // result (success or validation failure) lands.
    refetchInterval: (query) => (query.state.status === "pending" || query.state.data === null ? 3000 : false),
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

        {isComplete && (
          <Paper variant="outlined" sx={{ mt: 2, p: 2 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography variant="subtitle1">Extracted fields</Typography>
              {extractionQuery.data && (
                <Chip
                  size="small"
                  label={`${Math.round(extractionQuery.data.confidenceScore * 100)}% confidence`}
                  color={confidenceColor(extractionQuery.data.confidenceScore)}
                />
              )}
            </Stack>
            <Divider sx={{ my: 1.5 }} />

            {(extractionQuery.isLoading || (extractionQuery.isSuccess && extractionQuery.data === null)) && (
              <Stack direction="row" spacing={1} alignItems="center">
                <CircularProgress size={18} />
                <Typography variant="body2" color="text.secondary">
                  AI extraction is still running.
                </Typography>
              </Stack>
            )}

            {extractionQuery.isError && (
              <Alert severity={extractionQuery.error instanceof ApiError && extractionQuery.error.status === 422 ? "warning" : "error"}>
                {extractionQuery.error instanceof Error
                  ? extractionQuery.error.message
                  : "Failed to load extraction results."}
              </Alert>
            )}

            {extractionQuery.data && (
              <Box>
                <FieldList label="Parties" values={extractionQuery.data.content.parties} />
                <Stack direction={{ xs: "column", sm: "row" }} spacing={4} sx={{ mb: 1.5 }}>
                  <Box>
                    <Typography variant="body2" fontWeight={600}>
                      Effective date
                    </Typography>
                    <Typography variant="body2">{extractionQuery.data.content.effective_date ?? "—"}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" fontWeight={600}>
                      Termination date
                    </Typography>
                    <Typography variant="body2">{extractionQuery.data.content.termination_date ?? "—"}</Typography>
                  </Box>
                </Stack>
                <FieldList label="Monetary values" values={extractionQuery.data.content.monetary_values} />
                <FieldList label="Key clauses" values={extractionQuery.data.content.key_clauses} />
                <FieldList label="Obligations" values={extractionQuery.data.content.obligations} />
                <Divider sx={{ my: 1.5 }} />
                <Typography variant="caption" color="text.secondary">
                  Prompt {extractionQuery.data.promptId}@{extractionQuery.data.promptVersion} · model{" "}
                  {extractionQuery.data.modelProvider}/{extractionQuery.data.modelName}
                </Typography>
              </Box>
            )}
          </Paper>
        )}
      </Container>
    </>
  );
}
