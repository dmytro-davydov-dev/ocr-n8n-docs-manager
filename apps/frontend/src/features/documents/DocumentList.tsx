import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import type { DocumentStatus } from "@contract-review/api-client";
import {
  Alert,
  Button,
  Chip,
  CircularProgress,
  FormControlLabel,
  Paper,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import type { ChipProps } from "@mui/material";

import { api } from "../../api";

const STATUS_COLOR: Record<DocumentStatus, ChipProps["color"]> = {
  uploaded: "default",
  queued: "info",
  processing: "warning",
  complete: "success",
  failed: "error",
};

const STATUS_LABEL: Record<DocumentStatus, string> = {
  uploaded: "Uploaded",
  queued: "Queued",
  processing: "Processing",
  complete: "Complete",
  failed: "Failed",
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Document list with live status polling (WS-01 Phase 1 milestone,
 * PRD-Phase-1-Document-Ingestion FR-107/108).
 */
export function DocumentList() {
  const queryClient = useQueryClient();
  const [showArchived, setShowArchived] = useState(false);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["documents", { includeArchived: showArchived }],
    queryFn: () => api.listDocuments({ includeArchived: showArchived }),
    refetchInterval: 2000,
  });

  const archiveMutation = useMutation({
    mutationFn: (id: string) => api.archiveDocument(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const unarchiveMutation = useMutation({
    mutationFn: (id: string) => api.unarchiveDocument(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const reprocessMutation = useMutation({
    mutationFn: (id: string) => api.reprocessDocument(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const toggle = (
    <FormControlLabel
      control={<Switch size="small" checked={showArchived} onChange={(_, checked) => setShowArchived(checked)} />}
      label="Show archived"
    />
  );

  if (isLoading) {
    return <CircularProgress size={24} />;
  }

  if (isError) {
    return <Alert severity="error">{error instanceof Error ? error.message : "Failed to load documents."}</Alert>;
  }

  if (!data || data.length === 0) {
    return (
      <Stack spacing={1} alignItems="flex-start">
        {toggle}
        <Typography color="text.secondary" sx={{ py: 2 }}>
          {showArchived ? "No documents." : "No documents uploaded yet."}
        </Typography>
      </Stack>
    );
  }

  return (
    <Stack spacing={1}>
      <Stack direction="row" justifyContent="flex-end">
        {toggle}
      </Stack>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Filename</TableCell>
              <TableCell>Size</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Updated</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.map((doc) => {
              // "failed" is viewable too -- DocumentDetailPage shows the
              // errorMessage for it. Without this, a failed document has no
              // way to be reached from the list at all.
              const isViewable = doc.status === "complete" || doc.status === "failed";
              const isArchived = doc.archivedAt != null;
              return (
                <TableRow
                  key={doc.id}
                  hover={isViewable}
                  {...(isViewable
                    ? { component: RouterLink, to: `/documents/${doc.id}`, sx: { cursor: "pointer", textDecoration: "none" } }
                    : {})}
                >
                  <TableCell>{doc.filename}</TableCell>
                  <TableCell>{formatSize(doc.sizeBytes)}</TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={0.5}>
                      <Chip size="small" label={STATUS_LABEL[doc.status]} color={STATUS_COLOR[doc.status]} />
                      {isArchived && <Chip size="small" label="Archived" variant="outlined" />}
                    </Stack>
                  </TableCell>
                  <TableCell>{new Date(doc.updatedAt).toLocaleTimeString()}</TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      {!isArchived && (
                        <Button
                          size="small"
                          onClick={(event) => {
                            // Rows for viewable documents are themselves a
                            // RouterLink -- without this, clicking the
                            // button would also navigate to the detail page.
                            event.preventDefault();
                            event.stopPropagation();
                            reprocessMutation.mutate(doc.id);
                          }}
                          disabled={reprocessMutation.isPending}
                        >
                          Reprocess
                        </Button>
                      )}
                      <Button
                        size="small"
                        onClick={(event) => {
                          event.preventDefault();
                          event.stopPropagation();
                          if (isArchived) {
                            unarchiveMutation.mutate(doc.id);
                          } else {
                            archiveMutation.mutate(doc.id);
                          }
                        }}
                        disabled={archiveMutation.isPending || unarchiveMutation.isPending}
                      >
                        {isArchived ? "Unarchive" : "Archive"}
                      </Button>
                    </Stack>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
      {(archiveMutation.isError || unarchiveMutation.isError || reprocessMutation.isError) && (
        <Alert severity="error">
          {(archiveMutation.error ?? unarchiveMutation.error ?? reprocessMutation.error) instanceof Error
            ? ((archiveMutation.error ?? unarchiveMutation.error ?? reprocessMutation.error) as Error).message
            : "Failed to update document."}
        </Alert>
      )}
    </Stack>
  );
}
