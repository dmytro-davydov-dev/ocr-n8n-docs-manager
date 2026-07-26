# Tech Glossary

**Status:** Accepted
**Date:** 2026-07-26
**Owner:** Product & Engineering

---

# Purpose

This page explains, in plain language, the technical terms and abbreviations used elsewhere in this knowledge base. It's written for readers who aren't engineers — if you hit an unfamiliar term in the [[vision/Vision]], a PRD, or an ADR, look for it here first. Each entry below is its own heading, so other pages link straight to a specific definition. See [[MOC]] for where each of these concepts is used in the project.

---

# AI & Document Understanding

### AI

**AI (Artificial Intelligence)** is software that performs tasks — like reading a document and pulling out key facts — that would normally require a person to read and understand it.

### OCR

**OCR (Optical Character Recognition)** is the technology that converts a picture of text (a scanned or photographed page) into actual, searchable text a computer can read. Without OCR, a scanned contract is just an image — no different to a computer than a photo of a cat.

### CV

**CV (Computer Vision)** is the broader field of teaching software to "see" and interpret images and documents. OCR is one specific application of computer vision.

### ML

**ML (Machine Learning)** is a way of building software that learns patterns from examples (data) rather than being explicitly programmed rule by rule. OCR engines and language models are both built using machine learning.

### LLM

An **LLM (Large Language Model)** is the kind of AI model (like the ones behind ChatGPT) that reads and generates human language. In this project, an LLM reads the OCR'd contract text and proposes structured fields — who the parties are, key dates, amounts, clauses, obligations.

### Prompt

A **prompt** is the instructions given to an LLM telling it what to do — for example, "read this contract text and extract the parties, dates, and key clauses as JSON." This project keeps prompts as versioned files so results stay reproducible.

### Embedding

An **embedding** is a way of converting a piece of text into a list of numbers that captures its *meaning*, not just its words. Two passages about the same topic end up with similar numbers even if they use different wording — this is what makes semantic search possible.

### Chunking

**Chunking** means splitting a long document into smaller pieces (chunks) before generating embeddings for it. Models work better, and search results are more precise, when they operate on a paragraph rather than an entire contract at once.

### RAG

**RAG (Retrieval-Augmented Generation)** is a technique where an AI answers a question by first *retrieving* the most relevant passages from your own documents, then using an LLM to write an answer grounded in those passages — with citations back to the source, instead of the model just making something up from memory.

### Semantic Search

**Semantic search** is search based on meaning rather than exact keyword matches — "cancellation terms" can find a clause that says "termination rights" even though the words don't match.

### Hybrid Search

**Hybrid search** (also called hybrid retrieval) combines classic keyword search with semantic (meaning-based) search into one ranked result, to get the precision of keywords and the flexibility of meaning-based matching.

### Vector Database

A **vector database** is a database built to store and quickly search embeddings (the "meaning" numbers described above). This project uses pgvector, an extension that adds this capability directly to PostgreSQL.

---

# How the Product Is Put Together

### API

An **API (Application Programming Interface)** is the set of "doors" one piece of software uses to ask another piece of software to do something — for example, the frontend calling the backend to upload a document. You never see it directly, but it's how the pieces of this product talk to each other.

### REST API

A **REST API** is a common style of API that uses standard web requests (the same underlying technology as loading a webpage) to read and write data.

### Webhook

A **webhook** is an automatic notification one system sends to another when something happens — e.g., the backend "pings" a workflow tool the moment a document finishes uploading, instead of that tool having to constantly check.

### JSON

**JSON** is a simple, structured text format for exchanging data between systems — the extracted contract fields, for instance, are represented in JSON before being saved.

### SQL

**SQL** is the language used to ask a database questions and give it instructions ("store this," "find that").

### ORM

An **ORM (Object-Relational Mapping)** is a programming layer that lets developers work with database records as familiar code objects instead of writing raw SQL by hand.

### Idempotent

**Idempotent** is a fancy word for "safe to repeat." An idempotent process gives the same end result whether it runs once or several times by accident — important for automated pipelines that might retry after a hiccup.

### Audit Log

An **audit log** (or audit trail) is a permanent, append-only record of every meaningful change (who uploaded what, who edited a field, who approved a review, and when). It can be added to but never rewritten, which is what makes it trustworthy.

### Workstream

A **workstream** is a persistent area of ownership (e.g., "Frontend" or "Backend and Data") that spans the whole project, as opposed to a phase, which is a slice of *functionality* delivered by several workstreams working together.

---

# The Tools Behind the Scenes

### React

**React** is the toolkit used to build the web pages you interact with (the upload screen, review screen, and so on).

### Vite

**Vite** is the tool that assembles and serves the frontend code during development, in the background.

### FastAPI

**FastAPI** is the toolkit used to build the backend — the service that stores data and enforces the rules of the application.

### PostgreSQL

**PostgreSQL** is the database where all application data (documents, reviews, audit history) is permanently stored.

### Redis

**Redis** is a very fast, temporary data store used here as the messaging system between the backend and the background workers.

### Celery

**Celery** is the system that runs the heavy, slow work (OCR, calling the AI model, generating embeddings) in the background, so uploading a document doesn't make you sit and wait.

### n8n

**n8n** is a workflow-automation tool that sequences the steps of the pipeline (upload → OCR → extraction → embedding) and watches for anything stuck or failed.

### Docker

**Docker** packages each piece of the application (frontend, backend, database, etc.) into a self-contained unit so it runs the same way on any computer.

### Docker Compose

**Docker Compose** starts every one of those Docker units together with one command, wiring them up to talk to each other.

### pgvector

**pgvector** is the PostgreSQL extension that turns the regular database into a vector database, so embeddings can be stored and searched right alongside the rest of the application's data.

---

# Project Documents & Process

### MVP

An **MVP (Minimum Viable Product)** is the smallest version of the product that's still genuinely useful end to end — here, upload → OCR → AI extraction → human review → search.

### PRD

A **PRD (Product Requirements Document)** describes *what* a phase of the product should do and why, before it's built.

### ADR

An **ADR (Architecture Decision Record)** is a short document explaining a specific technical decision (e.g., "why we chose PostgreSQL") and the trade-offs considered, so future readers understand the reasoning, not just the outcome.

### CI

**CI (Continuous Integration)** refers to automated checks (tests, etc.) that run every time code changes, to catch problems before they reach the live product.

### MOC

**MOC (Map of Content)** is the Obsidian term for an index page that links out to every other document in the knowledge base — [[MOC]] is this project's homepage for documentation.

---

# Related Documents

- [[MOC]]
- [[vision/Vision]]
- [[vision/Goals]]
