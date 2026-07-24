import { Alert, AlertTitle, Box, Button, Container } from "@mui/material";
import { Component, ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  public static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  public render() {
    if (this.state.hasError) {
      return (
        <Container maxWidth="sm">
          <Box sx={{ mt: 6 }}>
            <Alert severity="error">
              <AlertTitle>Application error</AlertTitle>
              Something went wrong while rendering the UI.
            </Alert>
            <Button sx={{ mt: 2 }} variant="contained" onClick={() => window.location.reload()}>
              Reload
            </Button>
          </Box>
        </Container>
      );
    }

    return this.props.children;
  }
}
