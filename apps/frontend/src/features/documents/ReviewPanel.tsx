import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import type { ChipProps } from "@mui/material";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  List,
  ListItem,
  ListItemText,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { ApiError, type ExtractedContractFields, type ReviewStatus, type ReviewSummary } from "@contract-review/api-client";

import { api } from "../../api";

const STATUS_LABEL: Record<ReviewStatus, string> = {
  draft_review: "Draft",
  in_review: "In review",
  approved: "Approved",
  rejected: "Rejected",
  archived: "Archived",
};

function statusColor(status: ReviewStatus): ChipProps["color"] {
  switch (status) {
    case "approved":
      return "success";
    case "rejected":
      return "error";
    case "in_review":
      return "warning";
    case "archived":
      return "default";
    default:
      return "info";
  }
}

/** Editable mirror of `ExtractedContractFields`; list fields are edited as
 * newline-separated text and split/joined at the boundary. */
interface EditableContent {
  parties: string;
  effective_date: string;
  termination_date: string;
  monetary_values: string;
  key_clauses: string;
  obligations: string;
}

function toEditable(content: Record<string, unknown>): EditableContent {
  const asLines = (value: unknown): string => (Array.isArray(value) ? value.join("\n") : "");
  const asText = (value: unknown): string => (typeof value === "string" ? value : "");
  return {
    parties: asLines(content.parties),
    effective_date: asText(content.effective_date),
    termination_date: asText(content.termination_date),
    monetary_values: asLines(content.monetary_values),
    key_clauses: asLines(content.key_clauses),
    obligations: asLines(content.obligations),
  };
}

function fromEditable(editable: EditableContent): Record<string, unknown> {
  const asLines = (value: string): string[] =>
    value
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
  return {
    parties: asLines(editable.parties),
    effective_date: editable.effective_date.trim() || null,
    termination_date: editable.termination_date.trim() || null,
    monetary_values: asLines(editable.monetary_values),
    key_clauses: asLines(editable.key_clauses),
    obligations: asLines(editable.obligations),
  };
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

/**
 * Review workspace: FR-401-408 (PRD-Phase-4-Contract-Review-UI). Consumes
 * WS-02's review API (ADR-014) end to end -- edit, save draft, submit,
 * approve, reject (with reason), revise a rejected review, archive, and the
 * append-only audit history.
 */
export function ReviewPanel({
  documentId,
  extractionContent,
}: {
  documentId: string;
  extractionContent: ExtractedContractFields | undefined;
}) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<EditableContent | null>(null);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [historyOpen, setHistoryOpen] = useState(false);

  const reviewQuery = useQuery({
    queryKey: ["review", documentId],
    queryFn: () => api.getReview(documentId),
  });

  const historyQuery = useQuery({
    queryKey: ["review-history", documentId],
    queryFn: () => api.getReviewHistory(documentId),
    enabled: historyOpen,
  });

  const review = reviewQuery.data ?? null;

  useEffect(() => {
    if (review && review.status === "draft_review") {
      setDraft(toEditable(review.content));
    } else {
      setDraft(null);
    }
  }, [review?.id, review?.status, review?.version]);

  const invalidateReview = () => {
    queryClient.invalidateQueries({ queryKey: ["review", documentId] });
    queryClient.invalidateQueries({ queryKey: ["review-history", documentId] });
  };

  const startMutation = useMutation({
    mutationFn: () => api.createReview(documentId, extractionContent ? { ...extractionContent } : {}),
    onSuccess: invalidateReview,
    onError: invalidateReview,
  });

  const saveDraftMutation = useMutation({
    mutationFn: () => {
      if (!review || !draft) throw new Error("Nothing to save");
      return api.saveDraft(documentId, fromEditable(draft), review.version);
    },
    onSuccess: invalidateReview,
    onError: invalidateReview,
  });

  const submitMutation = useMutation({
    mutationFn: () => {
      if (!review) throw new Error("No review to submit");
      return api.submitReview(documentId, review.version);
    },
    onSuccess: invalidateReview,
    onError: invalidateReview,
  });

  const approveMutation = useMutation({
    mutationFn: () => {
      if (!review) throw new Error("No review to approve");
      return api.approveReview(documentId, review.version);
    },
    onSuccess: invalidateReview,
    onError: invalidateReview,
  });

  const rejectMutation = useMutation({
    mutationFn: () => {
      if (!review) throw new Error("No review to reject");
      return api.rejectReview(documentId, review.version, rejectReason);
    },
    onSuccess: () => {
      invalidateReview();
      setRejectDialogOpen(false);
      setRejectReason("");
    },
    onError: invalidateReview,
  });

  const reviseMutation = useMutation({
    mutationFn: () => {
      if (!review) throw new Error("No review to revise");
      return api.reviseReview(documentId, review.version);
    },
    onSuccess: invalidateReview,
    onError: invalidateReview,
  });

  const archiveMutation = useMutation({
    mutationFn: () => {
      if (!review) throw new Error("No review to archive");
      return api.archiveReview(documentId, review.version);
    },
    onSuccess: invalidateReview,
    onError: invalidateReview,
  });

  const allMutations = [
    startMutation,
    saveDraftMutation,
    submitMutation,
    approveMutation,
    rejectMutation,
    reviseMutation,
    archiveMutation,
  ];

  // React Query leaves a mutation's `isError` set until it's retried or
  // explicitly reset, so without this a failed action (e.g. a stale save
  // draft) would keep shadowing the error/pending banner for every later,
  // unrelated action (e.g. a successful submit) -- reset every sibling
  // before starting a new one so the banner always reflects the action the
  // user just took.
  const runMutation = (mutation: (typeof allMutations)[number]) => {
    allMutations.forEach((m) => m !== mutation && m.reset());
    mutation.mutate();
  };

  const pendingMutation = allMutations.find((mutation) => mutation.isPending || mutation.isError);

  return (
    <Paper variant="outlined" sx={{ mt: 2, p: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Typography variant="subtitle1">Review</Typography>
        {review && <Chip size="small" label={STATUS_LABEL[review.status]} color={statusColor(review.status)} />}
      </Stack>
      <Divider sx={{ my: 1.5 }} />

      {reviewQuery.isLoading && <CircularProgress size={20} />}

      {reviewQuery.isError && (
        <Alert severity="error" sx={{ mb: 1.5 }}>
          {errorMessage(reviewQuery.error, "Failed to load this document's review.")}
        </Alert>
      )}

      {pendingMutation?.isError && (
        <Alert
          severity={pendingMutation.error instanceof ApiError && pendingMutation.error.status === 412 ? "warning" : "error"}
          sx={{ mb: 1.5 }}
        >
          {errorMessage(pendingMutation.error, "Review action failed.")}
          {pendingMutation.error instanceof ApiError && pendingMutation.error.status === 412
            ? " Someone else may have edited this review — reloading the latest version."
            : ""}
        </Alert>
      )}

      {!reviewQuery.isLoading && !reviewQuery.isError && !review && (
        <Stack spacing={1} alignItems="flex-start">
          <Typography variant="body2" color="text.secondary">
            No review has been started for this document yet.
          </Typography>
          <Button variant="contained" size="small" onClick={() => runMutation(startMutation)} disabled={startMutation.isPending}>
            Start review
          </Button>
        </Stack>
      )}

      {review && (
        <Stack spacing={2}>
          {review.status === "rejected" && review.rejectionReason && (
            <Alert severity="error">Rejected: {review.rejectionReason}</Alert>
          )}

          {review.status === "draft_review" && draft ? (
            <Stack spacing={1.5}>
              <TextField
                label="Parties (one per line)"
                multiline
                minRows={2}
                value={draft.parties}
                onChange={(event) => setDraft({ ...draft, parties: event.target.value })}
              />
              <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                <TextField
                  label="Effective date"
                  value={draft.effective_date}
                  onChange={(event) => setDraft({ ...draft, effective_date: event.target.value })}
                  fullWidth
                />
                <TextField
                  label="Termination date"
                  value={draft.termination_date}
                  onChange={(event) => setDraft({ ...draft, termination_date: event.target.value })}
                  fullWidth
                />
              </Stack>
              <TextField
                label="Monetary values (one per line)"
                multiline
                minRows={2}
                value={draft.monetary_values}
                onChange={(event) => setDraft({ ...draft, monetary_values: event.target.value })}
              />
              <TextField
                label="Key clauses (one per line)"
                multiline
                minRows={2}
                value={draft.key_clauses}
                onChange={(event) => setDraft({ ...draft, key_clauses: event.target.value })}
              />
              <TextField
                label="Obligations (one per line)"
                multiline
                minRows={2}
                value={draft.obligations}
                onChange={(event) => setDraft({ ...draft, obligations: event.target.value })}
              />
            </Stack>
          ) : (
            <Box component="pre" sx={{ m: 0, fontSize: 13, whiteSpace: "pre-wrap", fontFamily: "inherit" }}>
              {JSON.stringify(review.content, null, 2)}
            </Box>
          )}

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {review.status === "draft_review" && (
              <>
                <Button size="small" variant="outlined" onClick={() => runMutation(saveDraftMutation)} disabled={saveDraftMutation.isPending}>
                  Save draft
                </Button>
                <Button size="small" variant="contained" onClick={() => runMutation(submitMutation)} disabled={submitMutation.isPending}>
                  Submit for review
                </Button>
                <Button size="small" color="inherit" onClick={() => runMutation(archiveMutation)} disabled={archiveMutation.isPending}>
                  Archive
                </Button>
              </>
            )}

            {review.status === "in_review" && (
              <>
                <Button size="small" variant="contained" color="success" onClick={() => runMutation(approveMutation)} disabled={approveMutation.isPending}>
                  Approve
                </Button>
                <Button size="small" variant="outlined" color="error" onClick={() => setRejectDialogOpen(true)}>
                  Reject
                </Button>
              </>
            )}

            {review.status === "rejected" && (
              <>
                <Button size="small" variant="contained" onClick={() => runMutation(reviseMutation)} disabled={reviseMutation.isPending}>
                  Revise (back to draft)
                </Button>
                <Button size="small" color="inherit" onClick={() => runMutation(archiveMutation)} disabled={archiveMutation.isPending}>
                  Archive
                </Button>
              </>
            )}

            {review.status === "approved" && (
              <Button size="small" color="inherit" onClick={() => runMutation(archiveMutation)} disabled={archiveMutation.isPending}>
                Archive
              </Button>
            )}

            <Button size="small" onClick={() => setHistoryOpen(true)}>
              Audit history
            </Button>
          </Stack>

          <Typography variant="caption" color="text.secondary">
            Version {review.version}
          </Typography>
        </Stack>
      )}

      <Dialog open={rejectDialogOpen} onClose={() => setRejectDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Reject review</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 1.5 }}>A reason is required (ADR-014).</DialogContentText>
          <TextField
            autoFocus
            fullWidth
            multiline
            minRows={2}
            label="Reason"
            value={rejectReason}
            onChange={(event) => setRejectReason(event.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRejectDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            color="error"
            disabled={rejectReason.trim().length === 0 || rejectMutation.isPending}
            onClick={() => runMutation(rejectMutation)}
          >
            Reject
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={historyOpen} onClose={() => setHistoryOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Audit history</DialogTitle>
        <DialogContent>
          {historyQuery.isLoading && <CircularProgress size={20} />}
          <List dense>
            {historyQuery.data?.map((revision) => (
              <ListItem key={revision.id} divider>
                <ListItemText
                  primary={`v${revision.version} · ${STATUS_LABEL[revision.status]} · ${revision.actor}`}
                  secondary={new Date(revision.createdAt).toLocaleString()}
                />
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHistoryOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
