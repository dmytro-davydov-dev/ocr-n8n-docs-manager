# ADR-005 — React, TypeScript, and Vite for the Frontend

- **Status:** Accepted
- **Date:** 2026-07-24
- **Decision Makers:** Project Team

---

# Context

The Contract Review MVP requires a browser application for document upload, processing-status visibility, extracted-data review, and eventual human approval workflows.

The frontend must provide:

- a typed and maintainable component model;
- fast local development;
- predictable API integration;
- routing and application-shell structure;
- server-state management;
- error handling;
- compatibility with Docker Compose;
- a foundation for an interactive contract-review workspace.

Phase 0 requires an application shell using React, TypeScript, Vite, Material UI, React Router, TanStack Query, an API client abstraction, and an error boundary.

---

# Decision

Use **React** with **TypeScript** and **Vite** for the frontend application.

The frontend is located under:

```text
apps/frontend/
```

The baseline stack is:

- React;
- TypeScript with strict type checking;
- Vite for development and production builds;
- Material UI for the component system;
- React Router for routing;
- TanStack Query for server-state synchronization;
- a generated or typed API client under `packages/api-client`;
- React Error Boundaries for unrecoverable rendering failures.

---

# Frontend Boundaries

The frontend communicates only with the FastAPI backend.

It must not:

- connect directly to PostgreSQL or Redis;
- invoke Celery tasks;
- call n8n directly;
- contain authoritative workflow state;
- duplicate backend business validation as the system of record.

The frontend may perform usability-oriented validation, but the backend remains authoritative.

---

# Rationale

React is selected because it supports a component-oriented interface and scales from the Phase 0 shell to a complex review workspace.

TypeScript provides:

- compile-time validation;
- safer refactoring;
- explicit component and API contracts;
- better integration with generated OpenAPI clients.

Vite provides:

- rapid startup and hot-module replacement;
- minimal configuration;
- efficient production builds;
- first-class TypeScript and React support;
- a good fit for containerized local development.

The combination is familiar, productive, and suitable for an MVP that may grow into a production-oriented reference implementation.

---

# State Management Strategy

Use different tools for different state categories:

- **TanStack Query** for remote server state, caching, retries, and invalidation;
- **React component state** for local transient state;
- **URL state** for navigation and shareable filters where appropriate;
- **Context** only for narrow cross-cutting concerns.

Do not introduce a global client-state library during Phase 0 unless a concrete requirement demonstrates the need.

---

# API Contract Strategy

FastAPI OpenAPI is the source of truth for the browser-facing API.

The frontend uses a typed client in:

```text
packages/api-client/
```

Generated contracts should not be manually edited. CI should detect contract drift where practical.

---

# Alternatives Considered

## Next.js

Advantages:

- integrated routing and server rendering;
- full-stack conventions;
- mature deployment ecosystem.

Disadvantages:

- server-side rendering is not required for the authenticated application workspace;
- introduces another server runtime;
- overlaps with FastAPI responsibilities;
- increases deployment and mental-model complexity for the MVP.

Rejected for the initial implementation.

## Angular

Advantages:

- comprehensive framework;
- strong conventions and dependency injection;
- built-in patterns for large applications.

Disadvantages:

- heavier framework surface;
- more ceremony than required for the MVP;
- less aligned with the intended lightweight application shell.

Rejected.

## Vue

Advantages:

- approachable component model;
- strong tooling;
- good TypeScript support.

Disadvantages:

- React better matches the team's chosen stack and intended reference architecture.

Rejected.

---

# Consequences

## Positive

- Fast local feedback through Vite.
- Strong typing across components and API boundaries.
- Mature ecosystem for forms, tables, document viewers, and testing.
- Clear separation between server state and local UI state.
- Straightforward Docker-based development.

## Negative

- React leaves architectural choices to the team.
- TypeScript types can drift from backend models unless generated.
- Large review screens require careful rendering and state design.
- Dependency selection must remain controlled.

---

# Implementation Rules

- Enable strict TypeScript mode.
- Organize code by feature or domain rather than only by technical file type.
- Use the shared API client instead of ad hoc `fetch` calls.
- Keep server state in TanStack Query.
- Define route-level error and loading states.
- Provide a top-level error boundary.
- Use accessible Material UI primitives.
- Do not embed backend business logic in components.
- Keep environment-specific values in Vite environment configuration.
- Test reusable components and critical user flows.

---

# Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| API types drift from backend | Generate the client from OpenAPI |
| Components become overly stateful | Separate view, query, and domain adapters |
| Unnecessary global state complexity | Start with Query, local state, URL state, and narrow Context |
| Large documents cause rendering problems | Use pagination, virtualization, and incremental loading when required |
| Build-time environment variables leak secrets | Only expose explicitly public frontend configuration |

---

# Acceptance Criteria

- The React application starts through Docker Compose.
- Vite serves the development application.
- TypeScript strict checks pass.
- Material UI application shell is rendered.
- React Router defines the initial route structure.
- TanStack Query is configured.
- The shared API client can call `/api/health`.
- A top-level error boundary is present.
- The frontend contains no direct integration with internal infrastructure services.

---

# Related Documents

- [[../MOC]]
- [[../prd/PRD-Phase-0-Foundation]]
- [[ADR-001-Monorepo]]
- [[ADR-003-Repository-Structure]]
- [[ADR-004-FastAPI]]
