# ADR-007 — Redis as Cache and Message Broker

- **Status:** Accepted
- **Date:** 2026-07-24
- **Decision Makers:** Project Team

---

# Context

The Contract Review MVP requires a low-latency infrastructure component for asynchronous task delivery and selected ephemeral data.

Celery needs a supported broker through which FastAPI or orchestration components can enqueue background jobs and workers can receive them.

The system may later benefit from short-lived caching, distributed locks, rate-limiting counters, or progress signals. These concerns must remain separate from authoritative document and review data stored in PostgreSQL.

---

# Decision

Use **Redis** as:

1. the Celery message broker; and
2. an optional cache and ephemeral coordination store.

Redis is not the primary database and must not hold the only copy of business-critical state.

The initial MVP may also use Redis as the Celery result backend when short-lived task-result retrieval is required. Durable job status and domain outcomes must still be persisted in PostgreSQL.

---

# Responsibility Boundaries

Redis may store:

- Celery broker messages;
- short-lived task results;
- cache entries;
- expiring idempotency keys;
- distributed locks where necessary;
- rate-limit counters;
- ephemeral progress indicators.

Redis must not be the sole store for:

- document metadata;
- OCR output;
- extraction results;
- review decisions;
- authoritative processing state;
- audit history.

---

# Rationale

Redis is selected because it provides:

- mature Celery integration;
- low-latency queue operations;
- simple Docker deployment;
- configurable key expiration;
- broad client support;
- useful primitives for cache and coordination concerns;
- lower operational complexity than introducing separate broker and cache technologies for the MVP.

Using one Redis service for the initial broker and bounded cache needs keeps Phase 0 simple while maintaining a clear path to split responsibilities later.

---

# Key and Data Management

- Use namespaced keys.
- Define expiration for every cache, lock, idempotency, and progress key unless persistence is explicitly justified.
- Do not serialize secrets into task messages.
- Pass identifiers and storage references instead of large document payloads.
- Configure task visibility and retry behavior to avoid premature redelivery.
- Treat cache misses as normal behavior.
- Application correctness must not depend on cache availability.

---

# Alternatives Considered

## RabbitMQ as Celery broker

Advantages:

- purpose-built message broker;
- mature delivery and routing semantics;
- strong Celery support.

Disadvantages:

- adds a separate infrastructure technology;
- caching would still require another component;
- higher operational overhead for the MVP.

Deferred. It remains a candidate if queue semantics or scale outgrow Redis.

## PostgreSQL-backed task queue

Advantages:

- fewer infrastructure components;
- durable relational state.

Disadvantages:

- additional polling and locking complexity;
- less natural integration with Celery;
- mixes task transport with authoritative persistence.

Rejected.

## Redis as the primary application database

Advantages:

- low latency;
- simple key-value access.

Disadvantages:

- poor fit for relational, durable, auditable application state;
- creates unacceptable data-loss and modeling risks.

Explicitly rejected.

---

# Consequences

## Positive

- Simple Celery integration.
- Low operational overhead in Docker Compose.
- One service supports queueing and bounded ephemeral concerns.
- Easy local health checking and inspection.

## Negative

- Redis broker semantics require careful Celery configuration.
- Broker, result backend, and cache workloads can contend for resources.
- Volatile or evicted data cannot be treated as authoritative.
- A single Redis instance is a local single point of failure.

---

# Operational Requirements

- Run Redis as a dedicated Docker Compose service.
- Configure a health check.
- Use explicit logical database numbers or key prefixes for broker, result, and cache concerns where supported.
- Apply memory limits and an intentional eviction policy before production use.
- Do not expose Redis publicly.
- Configure authentication for non-local environments.
- Monitor memory, connected clients, blocked clients, queue length, and evictions.
- Persist durable workflow status in PostgreSQL.

---

# Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Redis restart loses ephemeral data | Keep authoritative state in PostgreSQL and design tasks for retry |
| Large payloads consume memory | Queue identifiers and file references, not document bodies |
| Cache keys collide | Enforce namespaces |
| Broker and cache workloads interfere | Separate key spaces initially; split Redis instances if metrics justify it |
| Duplicate task delivery | Make Celery tasks idempotent |

---

# Acceptance Criteria

- Redis starts through Docker Compose.
- Redis health check passes.
- Celery worker connects to Redis.
- A test task can be published and consumed.
- Task messages contain identifiers rather than document binaries.
- Durable processing status remains in PostgreSQL.
- Cache and coordination keys use documented namespaces and expiration.
- Redis connection settings are documented in `.env.example`.

---

# Related Documents

- [[../MOC]]
- [[../prd/PRD-Phase-0-Foundation]]
- [[ADR-002-Docker-Compose]]
- [[ADR-006-PostgreSQL]]
- [[ADR-008-Celery]]
