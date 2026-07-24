# ADR-008 — Celery for Background Processing

- **Status:** Accepted
- **Date:** 2026-07-24
- **Decision Makers:** Project Team

---

# Context

Document ingestion, PDF processing, OCR, chunking, and AI extraction are long-running or CPU-intensive operations. They may fail transiently, require retries, and must not block FastAPI request workers.

The MVP needs a background-processing mechanism that:

- integrates with Python processing libraries;
- uses Redis as the broker;
- supports retries and task routing;
- runs as a separate Docker Compose service;
- can be initiated from FastAPI and n8n;
- supports observable and idempotent processing;
- can later scale by adding workers.

---

# Decision

Use **Celery** for asynchronous background processing.

Celery workers run from the backend codebase under:

```text
apps/backend/
```

Redis is the initial broker. PostgreSQL stores authoritative job and workflow state.

Celery owns execution of background tasks. n8n owns cross-step workflow orchestration. FastAPI owns business rules, public APIs, and persisted application state.

---

# Processing Boundary

Celery tasks perform bounded units of work such as:

- validating or inspecting uploaded files;
- extracting text from native PDFs;
- rasterizing pages;
- running OCR;
- chunking extracted text;
- invoking AI extraction;
- generating derived artifacts;
- persisting task outcomes through application services.

Celery tasks must not encode the complete business workflow as an opaque task chain when that workflow is intended to be visible and managed in n8n.

---

# Task Contract Rules

Each task must:

- accept identifiers and small metadata, not file binaries;
- load input from durable shared storage;
- validate the current processing state;
- be safe to retry;
- persist durable outcomes in PostgreSQL;
- emit structured logs with correlation identifiers;
- distinguish retryable from terminal failures;
- record the implementation or model version when relevant.

Task names and payloads are internal contracts and must be versioned carefully.

---

# Rationale

Celery is selected because it offers:

- mature Python ecosystem integration;
- established Redis broker support;
- retries and exponential backoff;
- task routing and worker queues;
- concurrency controls;
- a familiar model for CPU-bound and I/O-bound background jobs;
- straightforward Docker deployment;
- future horizontal worker scaling.

It keeps Python-heavy OCR and AI execution close to the libraries that implement it.

---

# Idempotency and Delivery Semantics

Celery delivery should be treated as **at least once**.

Tasks must therefore tolerate duplicate execution.

Idempotency is achieved through:

- persisted processing-stage records;
- unique constraints or idempotency keys;
- deterministic artifact paths;
- state checks before performing work;
- transactional updates where required.

Acknowledgement and visibility-timeout settings must be chosen according to task duration.

---

# Retry Strategy

- Retry transient network, provider, and infrastructure failures.
- Do not automatically retry invalid input or deterministic validation failures.
- Use bounded retries with exponential backoff and jitter.
- Persist the final failure state in PostgreSQL.
- Allow operator or user-triggered retry through FastAPI.
- Preserve enough diagnostic context for troubleshooting without storing secrets.

---

# Alternatives Considered

## FastAPI background tasks

Advantages:

- built into the framework;
- minimal setup.

Disadvantages:

- tied to the API process;
- weak durability and retry support;
- unsuitable for heavy or long-running work;
- difficult to scale independently.

Rejected.

## n8n Code nodes for all processing

Advantages:

- visual workflow;
- fewer explicit worker components.

Disadvantages:

- poor fit for complex, testable Python processing;
- difficult dependency and resource management;
- business and processing code becomes embedded in workflows.

Rejected.

## Dramatiq or RQ

Advantages:

- simpler APIs;
- suitable Python worker models.

Disadvantages:

- Celery has broader routing, retry, and operational capabilities;
- Celery better matches the intended growth path.

Rejected for the initial implementation.

---

# Consequences

## Positive

- API requests remain responsive.
- Processing can be retried and scaled independently.
- Python OCR and AI dependencies remain in the worker environment.
- Work can be routed to specialized queues in later phases.
- Clear execution boundary between orchestration and processing.

## Negative

- Distributed-task failure modes must be handled.
- Duplicate delivery is possible.
- Worker observability and queue monitoring are required.
- Long tasks require careful timeout and acknowledgement configuration.
- Deployment includes another long-running service.

---

# Queue Strategy

Start with a default queue during Phase 0.

Introduce specialized queues only when resource isolation is needed, for example:

```text
default
pdf
ocr
ai
```

Queue proliferation without an operational requirement is discouraged.

---

# Operational Requirements

- Worker starts through Docker Compose.
- Worker health is represented through process and broker checks.
- Structured logs include task ID, document ID, workflow ID, attempt, and duration.
- Time limits are configured per task class.
- Graceful shutdown permits in-flight task handling.
- Queue length, active tasks, failures, retries, and duration are observable.
- Worker concurrency is conservative for CPU-heavy OCR tasks.
- Document files are accessed through the shared storage contract.

---

# Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Duplicate execution | Idempotent tasks and database constraints |
| Worker crash during processing | Late acknowledgement where appropriate and retry-safe tasks |
| OCR tasks exhaust CPU or memory | Dedicated queue and controlled concurrency |
| Tasks remain stuck | Time limits, monitoring, and explicit failure state |
| Task payload changes break old messages | Keep payloads small and version contracts |

---

# Acceptance Criteria

- Celery worker starts through Docker Compose.
- Worker connects to Redis.
- A Phase 0 test task is published and executed.
- Task success and failure are logged structurally.
- A durable job record can be updated in PostgreSQL.
- Retry behavior is demonstrated for a transient failure.
- Task payloads contain identifiers rather than file binaries.
- Responsibilities between FastAPI, Celery, and n8n are documented.

---

# Related Documents

- [[../MOC]]
- [[../prd/PRD-Phase-0-Foundation]]
- [[ADR-004-FastAPI]]
- [[ADR-006-PostgreSQL]]
- [[ADR-007-Redis]]
- [[ADR-009-n8n]]
