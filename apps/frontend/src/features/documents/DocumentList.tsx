import { useQuery } from "@tanstack/react-query";
import type { DocumentStatus } from "@contract-review/api-client";
import {
  Alert,
  Chip,
  CircularProgress,
  Paper,
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
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.listDocuments(),
    refetchInterval: 2000,
  });

  if (isLoading) {
    return <CircularProgress size={24} />;
  }

  if (isError) {
    return <Alert severity="error">{error instanceof Error ? error.message : "Failed to load documents."}</Alert>;
  }

  if (!data || data.length === 0) {
    return (
      <Typography color="text.secondary" sx={{ py: 2 }}>
        No documents uploaded yet.
      </Typography>
    );
  }

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Filename</TableCell>
            <TableCell>Size</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Updated</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data.map((doc) => (
            <TableRow key={doc.id} hover>
              <TableCell>{doc.filename}</TableCell>
              <TableCell>{formatSize(doc.sizeBytes)}</TableCell>
              <TableCell>
                <Chip size="small" label={STATUS_LABEL[doc.status]} color={STATUS_COLOR[doc.status]} />
              </TableCell>
              <TableCell>{new Date(doc.updatedAt).toLocaleTimeString()}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
