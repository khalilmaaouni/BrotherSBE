# BrotherSBE for Infrastructure Engineers (AWS and Azure), design spec

Approved by the founder through question windows on 2026-07-30. Sibling spec:
`2026-07-30-data-engineer-book-design.md`. Parent program spec:
`2026-07-30-team-docs-collab-book-design.md`. Status: APPROVED DESIGN.

## Why this book exists

Infrastructure work is where an unproven claim costs the most: a migration that cannot be
reversed, a cutover with no rehearsal, a failover nobody tested until the night it was
needed. This book teaches BrotherSBE to the engineer who owns that risk, in the shape of a
real service: multi-tenant, ingestion pipelines feeding a warehouse, a microservice API
tier behind a load balancer, a search cluster, and multi-region failover, on AWS and Azure
side by side.

## Decisions taken (founder, 2026-07-30, via windows)

| Decision | Answer |
|---|---|
| Honesty for output this machine cannot produce | Runnable local core; every platform block labeled NOT EXECUTED HERE with its reason and the reader's command; every platform fact cited |
| Shape | Its own volume, reusing the base book's builder and replay harness |
| Estate | One generic multi-tenant commerce platform showing AWS and Azure variants side by side |
| Client anonymity | Zero client or project identifiers; enforced mechanically by `TestNoPrivateNameShips` on every run |
| Sequencing | Specced now, built after Loop 1 lands its builder and harness |

## Verified machine facts that shape this design (checked 2026-07-30)

`aws`, `az`, `kubectl`, `helm`, `terraform`, `docker`, `yq` are ALL ABSENT here;
`python3` 3.9.6 and `jq` are present, and Python's standard library has no YAML parser.
Consequence, and it turns out to be a gift: the estate is authored in the JSON forms these
tools genuinely accept, which the standard library can fully parse and validate.
Terraform reads `.tf.json` as an official alternative syntax, Kubernetes accepts JSON
manifests, Azure Data Factory pipelines are natively JSON, and Elasticsearch speaks JSON.
So the estate is really validated here, and the human-facing YAML equivalents are shown in
the prose beside their JSON twins.

## The estate: `docs/book-infra/estate/`

A generic multi-tenant commerce platform, no client identifiers:

- `ingestion/adf-pipeline.json` an Azure Data Factory pipeline (copy plus transform plus a
  failure path), with its AWS counterpart `ingestion/step-function.json`.
- `services/api-deployment.json`, `api-service.json`, `api-hpa.json` Kubernetes manifests
  in JSON for the microservice tier, including resource limits and a readiness probe, plus
  a deliberately missing limit in one variant for the review chapter to catch.
- `search/index-template.json` and `search/reindex.json` an Elasticsearch index template
  and a reindex request, the estate's migration-shaped change.
- `edge/alb.tf.json` and `edge/appgateway.tf.json` the load balancer in Terraform JSON for
  each cloud, including the listener rules a cutover changes.
- `regions/failover-runbook.md` plus `regions/slo.json` the multi-region plan and the
  service level objectives a decision is judged against.
- `validate_estate.py` the estate's own checker, standard library only: every manifest
  parses; every container declares resource limits and a probe (the missing-limit variant
  must FAIL by name); the reindex names a source and a destination; the load balancer files
  declare a health check; the SLO file carries a target and a window. Wired as
  `tools/test_sbe_book_infra.py`.

## Chapters, `docs/book-infra/`

Part I (01 to 03), for leads and product owners: the 2am problem, what evidence would have
prevented it, and what the gates refuse; reading `sbe status` on an infrastructure change.

Part II, the engineer core (04 to 10): the first loop on a service change; the destructive
change gate, where a Terraform plan is the evidence and the apply stays human because
production apply rights are law L14 and the tool cannot revoke a credential your shell
already holds; rehearsal for infrastructure, blue and green and canary as the honest form
of a reversibility receipt; Kubernetes rollouts, where the missing resource limit is caught
by the estate's own check and the reviewer sees the exact manifest line; the Elasticsearch
reindex as a migration with a rehearsal, row counts, and the value-checksum limit named;
the load balancer cutover as an approval-gated decision, with the typed-name refusal shown
real; multi-region failover as the decision that needs its own package, dependencies, and
blast radius written down before anyone is woken up.

Part III (11 to 12): coordinating with on-call and with a second engineer through one
vault, and where secrets never go (the no-credentials law, and why the tool asks for none);
then a cookbook of infrastructure-shaped recipes (new service, scaling change, reindex,
certificate or cutover window, incident, adopting an estate that has never been gated).

## Non-negotiables for the writers

Every platform command carries `NOT EXECUTED HERE` with its reason and the reader's exact
command. Every cloud fact, service name, and flag is cited to official documentation, never
from memory. Every BrotherSBE block is real re-executed output under the replay harness.
Nothing in the book instructs anyone to apply a production change from an agent, and the
apply-stays-human law is stated wherever a reader might wish otherwise. Maturity stays
INTERNAL-EVAL, and no chapter claims a real AWS or Azure estate has run this.

## Testing

`tools/test_sbe_book_infra.py`: the estate validates; the missing-limit variant FAILs by
name (calibrated); every chapter has one h1 and a Mermaid diagram; every platform block
carries its label, proven by a grep fixture so an unlabeled block fails the suite; the book
builds. Plus the replay harness over every BrotherSBE block, and every fixture calibrated
by breaking its control and watching red.
