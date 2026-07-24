import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Alert, Box, LinearProgress, Paper, Stack, Typography } from "@mui/material";
import { useCallback, useRef, useState } from "react";

import { api } from "../../api";

interface UploadItem {
  id: string;
  name: string;
  progress: number;
  error?: string;
}

/**
 * Drag-and-drop upload with per-file progress (WS-01 Phase 1 milestone,
 * PRD-Phase-1-Document-Ingestion FR-101/102).
 */
export function UploadDropzone() {
  const queryClient = useQueryClient();
  const [isDragging, setIsDragging] = useState(false);
  const [items, setItems] = useState<UploadItem[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const itemId = `${file.name}-${file.size}-${Date.now()}`;
      setItems((prev) => [...prev, { id: itemId, name: file.name, progress: 0 }]);

      try {
        const result = await api.uploadDocument(file, (percent) => {
          setItems((prev) => prev.map((item) => (item.id === itemId ? { ...item, progress: percent } : item)));
        });
        setItems((prev) => prev.filter((item) => item.id !== itemId));
        return result;
      } catch (error) {
        const message = error instanceof Error ? error.message : "Upload failed";
        setItems((prev) => prev.map((item) => (item.id === itemId ? { ...item, error: message } : item)));
        throw error;
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList) return;
      Array.from(fileList).forEach((file) => {
        upload.mutate(file);
      });
    },
    [upload]
  );

  return (
    <Paper
      variant="outlined"
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        handleFiles(event.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      sx={{
        p: 4,
        textAlign: "center",
        cursor: "pointer",
        borderStyle: "dashed",
        borderWidth: 2,
        borderColor: isDragging ? "primary.main" : "divider",
        backgroundColor: isDragging ? "action.hover" : "background.paper",
        transition: "border-color 0.15s ease, background-color 0.15s ease",
      }}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="application/pdf"
        hidden
        onChange={(event) => handleFiles(event.target.files)}
      />
      <Typography variant="h6" gutterBottom>
        Drop PDF documents here
      </Typography>
      <Typography variant="body2" color="text.secondary">
        or click to browse
      </Typography>

      {items.length > 0 && (
        <Stack spacing={1.5} sx={{ mt: 3, textAlign: "left" }}>
          {items.map((item) => (
            <Box key={item.id} onClick={(event) => event.stopPropagation()}>
              <Typography variant="body2" noWrap>
                {item.name}
              </Typography>
              {item.error ? (
                <Alert severity="error" sx={{ mt: 0.5 }}>
                  {item.error}
                </Alert>
              ) : (
                <LinearProgress variant="determinate" value={item.progress} sx={{ mt: 0.5 }} />
              )}
            </Box>
          ))}
        </Stack>
      )}
    </Paper>
  );
}
