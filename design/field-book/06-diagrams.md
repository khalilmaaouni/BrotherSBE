# 06. Diagrams

Every node below names an entity declared in `05-data-model.md` or a component
declared in the Components section of this file.

## Context

```mermaid
flowchart LR
  BoundSource -->|parsed by| GeneratedSection
  GeneratedSection -->|recorded in| SourceBinding
  GeneratedSection -->|embedded in| Chapter
  Chapter -->|grouped into| Part
  Part -->|assembled into| Book
  Chapter -->|carries| Stamp
```

## Entity relationship

```mermaid
erDiagram
  Book ||--|{ Part : contains
  Part ||--|{ Chapter : contains
  Chapter ||--o{ GeneratedSection : embeds
  Chapter ||--|| Stamp : carries
  GeneratedSection ||--|{ SourceBinding : records
  SourceBinding }o--|| BoundSource : names
  GeneratedSection ||--|| DriftVerdict : yields
```

## Components

These are runtime components, not entities, and are declared here rather than
in the data model on purpose.

- **Author**: the human editing a Chapter and running the Generator. Declared
  here because the sequence below names them, and a diagram node that traces to
  nothing declared is exactly what the traceability check exists to catch.
- **Generator**: `src/brothersbe/book.py` in render mode, invoked as `sbe book`.
- **DriftCheck**: the same module in verify mode, invoked as `sbe book --check`.
- **Renderer**: one function per generated section (commands, roles, checks,
  laws, limits), each declaring the BoundSource files it reads.
- **HtmlEmitter**: the single-file offline HTML writer.
- **CI**: `.github/workflows/brothersbe-gates.yml`, which runs DriftCheck under
  `--strict`.

```mermaid
flowchart TD
  BoundSource --> Renderer
  Renderer --> GeneratedSection
  Renderer --> SourceBinding
  Generator --> Renderer
  Generator --> HtmlEmitter
  Chapter --> HtmlEmitter
  HtmlEmitter --> Book
  SourceBinding --> DriftCheck
  BoundSource --> DriftCheck
  Stamp --> DriftCheck
  DriftCheck --> DriftVerdict
  DriftVerdict --> CI
```

## The generate and verify sequence

```mermaid
sequenceDiagram
  participant Author
  participant Generator
  participant Renderer
  participant BoundSource
  participant Chapter
  participant SourceBinding
  participant DriftCheck
  participant CI

  Author->>Generator: sbe book
  Generator->>Renderer: render each section
  Renderer->>BoundSource: read and parse
  BoundSource-->>Renderer: items, or a parse failure
  Renderer->>Chapter: write between markers
  Renderer->>SourceBinding: record path and sha256
  CI->>DriftCheck: sbe book --check --strict
  DriftCheck->>BoundSource: recompute sha256
  DriftCheck->>SourceBinding: compare recorded sha256
  DriftCheck->>Stamp: compare against VERSION
  DriftCheck-->>CI: DriftVerdict, exit code on FAIL only
```
