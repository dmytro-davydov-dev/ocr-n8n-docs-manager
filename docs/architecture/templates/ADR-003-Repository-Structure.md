# ADR-003 — Repository Structure

- **Status:** Accepted
- **Date:** 2026-07-24
- **Decision Makers:** Project Team

---

# Context

The Contract Review MVP is maintained as a monorepo and contains several distinct concerns:

- React frontend;
- FastAPI backend and Celery worker;
- shared API client code and generated contracts;
- n8n workflow definitions;
- Docker and database infrastructure;
- document-processing fixtures;
- product, architecture, and operational documentation.

Without an explicit repository layout, these concerns can become mixed together, ownership becomes unclear, and cross-stack changes become harder to review. The project also uses its Markdown documentation as an Obsidian knowledge base, so documentation paths and links must remain stable and predictable.

The repository structure must support the Phase 0 requirements of reproducible local development, clear service boundaries, documentation as code, and straightforward onboarding.

---

# Decision

Adopt a stable, responsibility-oriented repository structure with application code under `apps/`, reusable packages under `packages/`, workflow assets under `n8n/`, infrastructure under `infra/`, and project knowledge under `docs/`.

The approved high-level structure is:

```text
contract-review-mvp/
├── README.md
├── docker-compose.yml
├── Makefile
├── .env.example
├── .gitignore
│
├── apps/
│   ├── frontend/
│   │   ├── src/
│   │   ├── public/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── package.json
│   │
│   └── backend/
│       ├── app/
│       ├── migrations/
│       ├── tests/
│       ├── scripts/
│       ├── Dockerfile
│       └── pyproject.toml
│
├── packages/
│   └── api-client/
│       ├── src/
│       ├── tests/
│       └── package.json
│
├── n8n/
│   ├── workflows/
│   ├── credentials.example/
│   └── README.md
│
├── infra/
│   ├── postgres/
│   │   └── init/
│   ├── docker/
│   └── scripts/
│
├── docs/
│   ├── MOC.md
│   ├── vision/
│   ├── architecture/
│   │   ├── Progress.md
│   │   └── templates/
│   ├── adr/
│   ├── prd/
│   ├── implementation/
│   ├── frontend/
│   ├── backend/
│   ├── docker/
│   ├── database/
│   ├── security/
│   ├── testing/
│   └── observability/
│
├── fixtures/
│   ├── documents/
│   └── expected-results/
│
└── data/
    └── .gitkeep
```

The `data/` directory is only a local mount point when needed. Runtime documents and generated artifacts are not committed to Git.

---

# Directory Responsibilities

## `apps/frontend`

Owns the browser application:

- React, TypeScript, and Vite configuration;
- pages, components, routes, and frontend state;
- browser-facing API integration;
- frontend unit and component tests;
- frontend Docker image.

The frontend communicates only with the FastAPI backend. It does not connect directly to PostgreSQL, Redis, Celery, or n8n.

## `apps/backend`

Owns the application API and processing implementation:

- FastAPI endpoints;
- domain and application services;
- SQLAlchemy models and repositories;
- Alembic migrations;
- Celery tasks and worker entry points;
- OCR, extraction, and LLM adapters;
- backend tests and operational scripts.

The API and worker may share backend modules, but they run as separate processes and Docker Compose services.

## `packages/api-client`

Owns frontend-consumable API contracts and client code:

- OpenAPI-generated types;
- generated or maintained API client functions;
- contract-focused tests.

This package must not contain backend business logic or duplicate database models.

## `n8n`

Owns version-controlled workflow definitions and workflow documentation:

```text
n8n/workflows/contract-review-orchestrator.json
```

This directory must not contain exported credentials, secrets, production webhook URLs, or document payloads.

## `infra`

Owns local infrastructure support that does not belong to an individual application:

- PostgreSQL initialization scripts;
- Docker helper files;
- environment bootstrap scripts;
- local infrastructure utilities.

The canonical `docker-compose.yml` remains at the repository root because it coordinates the complete stack.

## `docs`

Owns the project knowledge base:

- PRDs;
- ADRs;
- architecture and implementation plans;
- progress tracking;
- security, testing, observability, frontend, backend, database, and Docker notes;
- reusable documentation templates.

`docs/MOC.md` is the main Obsidian navigation entry point. Documentation should use stable relative or Obsidian-style links.

## `fixtures`

Owns non-sensitive test inputs and deterministic expected outputs:

- synthetic or legally distributable PDF samples;
- malformed and edge-case documents;
- expected extraction results.

Real client contracts, personal data, API credentials, and proprietary documents must not be committed.

---

# Root-Level Files

Only files that govern the complete repository should be placed at the root.

Required root files include:

```text
README.md
docker-compose.yml
Makefile
.env.example
.gitignore
```

Additional root-level configuration is permitted only when it applies across the monorepo, for example CI configuration or an editor configuration.

Application-specific configuration remains inside the owning application.

---

# Naming Conventions

- Directories use lowercase kebab-case where multiple words are required.
- ADR files use `ADR-NNN-Short-Title.md`.
- PRD files use `PRD-Phase-N-Short-Title.md`.
- ADR and PRD identifiers are immutable once published.
- n8n workflows use descriptive kebab-case filenames.
- Python modules use `snake_case`.
- TypeScript source files follow the frontend package convention consistently.
- Generated files must be clearly identifiable and should not be manually edited unless explicitly documented.

---

# Dependency Rules

The repository layout defines architectural boundaries, not only file organization.

Allowed dependency direction:

```text
frontend → api-client
frontend → FastAPI over HTTP

FastAPI → application/domain modules
Celery worker → application/domain modules

FastAPI → PostgreSQL / Redis / n8n adapters
Celery worker → PostgreSQL / Redis / document storage
n8n → internal FastAPI endpoints
```

Disallowed dependencies include:

- frontend importing backend source code;
- frontend connecting directly to infrastructure services;
- n8n containing core OCR or business logic;
- infrastructure scripts importing application internals;
- shared packages depending on concrete applications;
- documentation duplicating executable source code as a second implementation.

---

# Runtime Data and Generated Artifacts

The following must not be committed:

- uploaded contracts;
- OCR images and temporary page renders;
- extracted contract text containing private data;
- local PostgreSQL or Redis data;
- n8n runtime state;
- LLM prompts or responses containing document content;
- `.env` files and secrets;
- generated logs;
- Python virtual environments and JavaScript dependency directories.

Persistent runtime data is stored in Docker named volumes or ignored local directories.

---

# Alternatives Considered

## Organize primarily by technology at the root

Example:

```text
frontend/
backend/
database/
docker/
```

### Advantages

- Initially simple.
- Fewer nesting levels.

### Disadvantages

- Does not scale well when more applications or shared packages are added.
- Makes the distinction between deployable applications and support assets less explicit.
- Encourages root-directory growth.

Rejected.

## Organize primarily by product feature

Example:

```text
documents/
ocr/
review/
```

### Advantages

- Strong feature locality.

### Disadvantages

- Difficult across Python and TypeScript toolchains.
- Complicates independent application builds and Docker images.
- Creates ambiguous ownership of infrastructure and shared contracts.

Rejected for the repository level. Feature-oriented organization may still be used inside each application.

## Separate repositories

### Advantages

- Strong technical isolation.
- Independent access and release control.

### Disadvantages

- Conflicts with ADR-001.
- Harder atomic changes and local integration.
- More duplicated configuration and documentation.

Rejected for the MVP.

---

# Consequences

## Positive

- Clear ownership and service boundaries.
- Predictable locations for code, workflows, infrastructure, and documentation.
- Easier onboarding and code review.
- Stable Obsidian links and documentation navigation.
- Straightforward Docker build contexts.
- Supports generated API clients without coupling frontend and backend source trees.
- Reduces accidental commitment of runtime documents and secrets.

## Negative

- More directories exist before all of them contain substantial content.
- Contributors must understand and enforce dependency rules.
- Some cross-cutting changes touch multiple directories.
- The backend application and Celery worker share a source tree, which requires disciplined module boundaries.

---

# Enforcement

Repository structure is enforced through:

- pull-request review;
- `.gitignore` rules;
- CI checks for formatting, tests, and generated artifacts;
- documented ownership and dependency rules;
- stable ADR and PRD naming;
- updates to `docs/MOC.md` when documentation is added or moved.

Moving a major directory or changing ownership boundaries requires a new ADR or an explicit superseding amendment to this ADR.

---

# Acceptance Criteria

- The project root matches the approved high-level layout.
- Frontend and backend build contexts are isolated under `apps/`.
- n8n workflow JSON is stored under `n8n/workflows/`.
- PostgreSQL initialization scripts are stored under `infra/postgres/init/`.
- ADRs and PRDs are stored under `docs/adr/` and `docs/prd/`.
- `docs/MOC.md` links to all Phase 0 ADRs and PRDs.
- Runtime document data and secrets are excluded from Git.
- `docker compose up --build` works without relying on files outside the repository.
- No application violates the documented dependency rules.

---

# Future Evolution

The structure may evolve by adding directories such as:

```text
packages/shared-types/
packages/config/
infra/kubernetes/
infra/terraform/
docs/runbooks/
```

Such additions should preserve the existing ownership model. A repository split should occur only when independent teams, release cycles, or deployment boundaries make it operationally necessary.

---

# Related Documents

- [[../MOC]]
- [[../architecture/Progress]]
- [[../prd/PRD-Phase-0-Foundation]]
- [[ADR-001-Monorepo]]
- [[ADR-002-Docker-Compose]]
- [[ADR-004-FastAPI]]
- [[ADR-005-React]]
- [[ADR-006-PostgreSQL]]
- [[ADR-007-Redis]]
- [[ADR-008-Celery]]
- [[ADR-009-n8n]]
