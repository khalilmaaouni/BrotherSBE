# Research behind the booklet's persona and tools sections

Two multi-agent research runs, 8 August 2026. Every dossier was drafted by one
agent and then handed to a second agent whose brief was to REFUTE it, on the
stated assumption that any draft contains at least one invented product, one
stale name and one overclaim. Both runs returned NEEDS_CORRECTION on every
dossier, which is the expected result and the reason the pass exists.

Read the refutation before the draft. In these files the draft is under
`research` or `draft`, and what survived is under `verdict` or `checked`.

| File | Run | Agents | What it covers |
|---|---|---|---|
| `2026-08-08-personas-and-diagrams.json` | `wf_9f8093e7-ca8` | 13 | Five seats (data, backend, infrastructure, QA, technical BA) plus the team operating model, each researched then refuted; and 14 diagram concepts grounded in what survived |
| `2026-08-08-adf-sap-estate.json` | `wf_47153fa9-c6c` | 6 | The ADF plus SAP Integration Suite estate: the SAP ingestion path, Azure DevOps and CI/CD, and where SAP data becomes a reported number |

## The finding that outranks the booklet

**SAP is blocking the ODP RFC API to third-party clients, and that includes
Azure Data Factory's SAP CDC connector.** Verbatim from the Microsoft Learn
page `sap-change-data-capture-introduction-architecture`, read 8 August 2026:

> A recent update of SAP Note 3255746 announces a security patch that blocks
> incoming calls to the ODP RFC API from third-party clients including Azure
> Data Factory's SAP CDC connector.

Microsoft names four replacements and only one of them has shipped:

| Alternative | Status as Microsoft states it |
|---|---|
| Mirroring for SAP Datasphere in Fabric | **Generally Available** |
| SAP Business Data Cloud Connect for Microsoft Fabric | Announced at Ignite 2025, available later |
| Copy Job in Fabric for SAP with a Microsoft ABAP Add-on (does not use the ODP RFC API) | Publicly available at Microsoft Build 2026 |
| Third party partner solutions with Open Mirroring in Fabric | Partner ecosystem |

A second-source note, flagged as vendor-sourced rather than SAP-sourced and
therefore **UNVERIFIED** here: a Theobald page attributes the actual blocking
security update to SAP Note **3748819**, with **3731818** giving guidance to
temporarily opt out. Confirm those numbers against SAP's own note system
before acting on them; the Microsoft banner names only 3255746 and 3439624.

## What the refuters killed, by class

Provenance decayed far faster than mechanics. Almost every correction was a
vendor or ownership fact rather than a technical one, which is why the tools
section must carry a "checked on" date.

- **One fabrication.** Log4brains credited to a maintainer name that does not
  exist. The real author is thomvaill, Thomas Vaillant.
- **Six ownership changes.** dbt Labs into Fivetran (closed 1 June 2026),
  Dagster Labs into Prefect (July 2026), VoidZero into Cloudflare (June 2026),
  Graphite into Cursor/Anysphere (December 2025), GX Cloud into FICO with GX
  Core stewarded by Fivetran, Xray under Idera's Sembi brand. Styra wound down
  in August 2025 and OPA's creators went to Apple, so pairing OPA with Styra is
  a year stale.
- **Tools assigned jobs they cannot do.** Spectral does not support OpenAPI
  3.2. Snowflake Data Metric Functions cannot measure consumer query traffic
  (use `ACCESS_HISTORY`). ODCS and Obsidian enforce nothing on their own.
- **Licence and maturity overclaims.** Soda Core moved to Elastic License 2.0.
  OpenTelemetry logs are stable in only four SDKs. Atlas gates Snowflake and
  several others behind Pro. External Secrets Operator is CNCF sandbox with no
  2026 releases.
- **Two corrections that change BrotherSBE's own claims.** GitHub ruleset
  *Evaluate* mode is gated at organisation and enterprise level, so the
  advisory-then-enforcing rollout the booklet recommends is not universally
  available. And a job skipped by an `if:` condition satisfies a required
  status check, which is the same silent pass the act-one figure now draws.

## The silent failures worth building the booklet around

Each is documented by a vendor, not inferred.

- **SAP CDC Checkpoint Key collision.** State is keyed per source; a shared key
  means one source overwrites another's change-capture state. Both pipelines
  keep succeeding. Worse, the property is hidden entirely when run mode is
  *Full on every run*, so flipping run mode silently discards checkpoint
  identity.
- **Debug and triggered runs create different ODP subscriptions.** A change
  validated in debug can behave differently once published.
- **ADF publish drift.** Microsoft states the main branch is not
  representative of what is deployed, changes made through PowerShell or the
  SDK never enter Git, and non-Key-Vault linked services publish immediately
  regardless of branch.
- **Azure DevOps path filters that match nothing.** A path filter that does not
  begin with `/` or a wildcard silently matches nothing, and the policy still
  displays as enabled and blocking.
- **Bypass policies.** A user completing a pull request with bypass permission
  merges past failing policies while the failure still displays.
- **Triggers not stopped during deployment.** The shipped pre and post
  deployment script stops only *modified* triggers, so an unchanged trigger
  fires mid-deployment against half-rewritten datasets.
- **Auto Loader `_rescued_data`.** A type or case mismatch routes SAP columns
  into the rescue column rather than failing; a `SUM` over a silently null
  column still returns a number.
- **The client field.** Dropping `MANDT` unions two SAP clients into one figure
  the day a second client appears.
- **Language keys.** A text join without the language key multiplies every row
  by its translation count.

## Where the research is weakest, stated rather than hidden

- `help.sap.com` and `sap.com` render client side or return HTTP 403 to a plain
  fetch, so SAP capability naming came from SAP's own Feature Scope Description
  PDF (PUBLIC, dated 2025-09-04) rather than the live help portal. That PDF
  lists the capabilities as Cloud Integration, API Management, Graph, Open
  Connectors, Integration Advisor, Trading Partner Management, Integration
  Assessment, Migration Assessment and Data Space Integration. Several
  secondary sources still call Event Mesh a core capability; SAP's own document
  does not, and advanced event mesh appears through adapters.
- Several drafted scenarios were refuted as impossible as narrated (an inverted
  currency shift, an ARM dependency ordering that cannot occur, a Snowflake
  linked service property that does not exist). Do not lift a scenario from the
  `draft` half of these files without reading its refutation.
