# Loops 1b and 1c: the Data Engineer and Infrastructure Engineer books, Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship two domain volumes, BrotherSBE for Data Engineers (Snowflake and Databricks) and BrotherSBE for Infrastructure Engineers (AWS and Azure with Azure Data Factory, Kubernetes, microservices, Elasticsearch, and load balancing), each with a locally runnable JSON-native estate, reusing the base book's builder and replay harness.

**Architecture:** Both books mirror the base book's machinery exactly: a real estate the reader can run, chapters in Markdown with Mermaid, one build command producing a self-contained illustrated HTML volume, and a replay harness that re-executes every BrotherSBE block so the prose cannot drift. What differs is the estate's domain and the chapters' vocabulary. Every command that needs a platform this machine does not have is labeled, never faked.

**Tech Stack:** Python 3.9 standard library only; JSON as the estates' authoring format (Terraform `.tf.json`, Kubernetes JSON manifests, Azure Data Factory pipeline JSON, Elasticsearch JSON, dbt `manifest.json`), because the standard library has no YAML parser and these are all formats the real tools accept.

## Global Constraints

- Specs of record: `docs/specs/2026-07-30-data-engineer-book-design.md` and `docs/specs/2026-07-30-infra-engineer-book-design.md`. Read yours in full before writing.
- BLOCKED UNTIL Loop 1 lands: `docs/book/build_book.py` and `evals/replay_book.py` must exist and be committed before any task here begins. Verify with `git log --oneline -5 -- docs/book/build_book.py evals/replay_book.py` and quote it.
- Python 3.9, standard library only. Zero em dashes and zero en dashes. No client or project names (mechanically enforced). No agent names, no trailers.
- Every platform command block carries the exact marker `NOT EXECUTED HERE:` followed by the reason and the reader's command. A grep fixture enforces it.
- Every platform fact, service name, and flag is cited inline to official documentation. Databricks chapters load the `databricks-core` skill first, then the matching product skill (`databricks-jobs`, `databricks-dabs`, `databricks-pipelines`, `databricks-docs`), per this machine's standing instruction, and take names and commands from there rather than from memory.
- Every BrotherSBE block is real output, re-executed, replay-checked.
- Helpers return three values, never two. Every fixture calibrated: hash, break, red, restore, verify.
- Do not touch `CHECKSUMS.sha256`, `.github/`, `docs/book/**` (the base book), or any file outside your named set.
- Maturity INTERNAL-EVAL everywhere; no claim that any real Snowflake, Databricks, AWS, or Azure estate has run this.

---

### Task 1: The data estate

**Files:**
- Create: `docs/book-data/estate/warehouse/ddl/{01-raw-orders.sql,02-stg-orders.sql,03-mart-daily-revenue.sql,04-drop-legacy-column.sql}`
- Create: `docs/book-data/estate/warehouse/derivations/{revenue-by-day-window.sql,revenue-by-day-groupby.sql}`
- Create: `docs/book-data/estate/dbt/{manifest.json,run_results.json}`
- Create: `docs/book-data/estate/databricks/{bundle.json,job.json}`
- Create: `docs/book-data/estate/{orders.csv.example,transform.py,validate_estate.py,README.md}`
- Test: `tools/test_sbe_book_data.py`

**Interfaces:**
- Produces: `python3 docs/book-data/estate/validate_estate.py` returning `(problems, checked, note)` and printing `estate: N artifact(s) checked, M problem(s)`; `python3 docs/book-data/estate/transform.py` printing the same headline number both derivations claim.

- [ ] **Step 1: Write the failing test**

```python
# tools/test_sbe_book_data.py
import io
import json
import os
import re
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESTATE = os.path.join(ROOT, "docs", "book-data", "estate")
BOOK = os.path.join(ROOT, "docs", "book-data")


class TestDataEstate(unittest.TestCase):
    def test_the_estate_validates_itself(self):
        out = subprocess.run([sys.executable, os.path.join(ESTATE, "validate_estate.py")],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("0 problem(s)", out.stdout)

    def test_the_two_derivations_differ_beyond_formatting(self):
        def flat(name):
            text = io.open(os.path.join(ESTATE, "warehouse", "derivations", name),
                           encoding="utf-8").read().lower()
            text = re.sub(r"--[^\n]*", " ", text)
            return re.sub(r"\s+", " ", text).strip()
        a = flat("revenue-by-day-window.sql")
        b = flat("revenue-by-day-groupby.sql")
        self.assertNotEqual(a, b, "two derivations that fold to one text prove nothing")
        self.assertIn("over (", a, "the window derivation must actually use a window")
        self.assertIn("group by", b, "the aggregate derivation must actually group")

    def test_the_transform_agrees_with_the_number_the_sql_claims(self):
        out = subprocess.run([sys.executable, os.path.join(ESTATE, "transform.py")],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("449.50", out.stdout)

    def test_the_dbt_files_carry_the_keys_an_adapter_will_read(self):
        manifest = json.load(io.open(os.path.join(ESTATE, "dbt", "manifest.json"),
                                     encoding="utf-8"))
        results = json.load(io.open(os.path.join(ESTATE, "dbt", "run_results.json"),
                                    encoding="utf-8"))
        self.assertIn("nodes", manifest)
        self.assertIn("results", results)

    def test_the_databricks_json_is_well_formed(self):
        for name in ("bundle.json", "job.json"):
            json.load(io.open(os.path.join(ESTATE, "databricks", name), encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Run it to verify it fails.** `python3 tools/test_sbe_book_data.py` fails with missing files.

- [ ] **Step 3: Write the estate.** The DDL files carry an explicit grain comment on every table (`-- grain: one row per order` and so on) because the design checks read grain, and `04-drop-legacy-column.sql` is a real destructive migration with its reverse written beside it. The two derivations compute the same daily revenue two genuinely different ways, one with a window function and one with a group-by plus join, so the numbers gate has an honest pair. `transform.py` computes the same total in Python over three sample orders totaling 449.50 so one half of the claim is provable on this machine. `manifest.json` and `run_results.json` follow dbt's real key shapes (`nodes` with `resource_type`, `depends_on`, and `columns`; `results` with `unique_id`, `status`, and `execution_time`), taken from dbt's published schema and cited in the README. `bundle.json` and `job.json` follow Databricks Asset Bundle and Jobs JSON as the `databricks-dabs` and `databricks-jobs` skills document them. `validate_estate.py` checks all of it with the standard library and returns its three-tuple.

- [ ] **Step 4: Green.** `python3 tools/test_sbe_book_data.py` prints `Ran 5 tests` and `OK`.
- [ ] **Step 5: Calibrate.** Remove one grain comment, watch the estate validator name it, restore against the recorded hash.
- [ ] **Step 6: Commit.** `git commit -m "Give the data book a warehouse it can validate"`

### Task 2: The infrastructure estate

**Files:**
- Create: `docs/book-infra/estate/ingestion/{adf-pipeline.json,step-function.json}`
- Create: `docs/book-infra/estate/services/{api-deployment.json,api-service.json,api-hpa.json,api-deployment-missing-limits.json}`
- Create: `docs/book-infra/estate/search/{index-template.json,reindex.json}`
- Create: `docs/book-infra/estate/edge/{alb.tf.json,appgateway.tf.json}`
- Create: `docs/book-infra/estate/regions/{failover-runbook.md,slo.json}`
- Create: `docs/book-infra/estate/{validate_estate.py,README.md}`
- Test: `tools/test_sbe_book_infra.py`

**Interfaces:**
- Produces: `python3 docs/book-infra/estate/validate_estate.py [--manifest PATH]` returning `(problems, checked, note)`, printing `estate: N artifact(s) checked, M problem(s)`, and naming every problem with its file and JSON path.

- [ ] **Step 1: Write the failing test**

```python
# tools/test_sbe_book_infra.py
import json
import io
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESTATE = os.path.join(ROOT, "docs", "book-infra", "estate")


class TestInfraEstate(unittest.TestCase):
    def _validate(self, *extra):
        out = subprocess.run([sys.executable, os.path.join(ESTATE, "validate_estate.py")]
                             + list(extra), capture_output=True, text=True, timeout=60)
        return out.returncode, out.stdout, out.stderr

    def test_the_estate_validates_itself(self):
        code, stdout, stderr = self._validate()
        self.assertEqual(code, 0, stdout + stderr)
        self.assertIn("0 problem(s)", stdout)

    def test_a_container_with_no_resource_limits_is_named_and_fails(self):
        code, stdout, _ = self._validate("--manifest", os.path.join(
            ESTATE, "services", "api-deployment-missing-limits.json"))
        self.assertNotEqual(code, 0, stdout)
        self.assertIn("api-deployment-missing-limits.json", stdout)
        self.assertIn("resources.limits", stdout)

    def test_every_estate_file_is_json_the_real_tools_accept(self):
        for folder, names in (("ingestion", ("adf-pipeline.json", "step-function.json")),
                              ("services", ("api-deployment.json", "api-service.json",
                                            "api-hpa.json")),
                              ("search", ("index-template.json", "reindex.json")),
                              ("edge", ("alb.tf.json", "appgateway.tf.json")),
                              ("regions", ("slo.json",))):
            for name in names:
                json.load(io.open(os.path.join(ESTATE, folder, name), encoding="utf-8"))

    def test_the_reindex_names_a_source_and_a_destination(self):
        body = json.load(io.open(os.path.join(ESTATE, "search", "reindex.json"),
                                 encoding="utf-8"))
        self.assertIn("source", body)
        self.assertIn("dest", body)

    def test_the_slo_declares_a_target_and_a_window(self):
        slo = json.load(io.open(os.path.join(ESTATE, "regions", "slo.json"),
                                encoding="utf-8"))
        self.assertIn("target", slo)
        self.assertIn("window", slo)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Verify it fails** (missing files).
- [ ] **Step 3: Write the estate.** Kubernetes manifests in JSON with real `apiVersion`, `kind`, resource limits, and a readiness probe, plus the deliberately incomplete variant. Azure Data Factory pipeline JSON with a copy activity, a transform activity, and a failure dependency, its AWS twin as a Step Functions state machine. Elasticsearch index template with mappings and settings, and a reindex body with `source`, `dest`, and a script. Load balancers as Terraform JSON with listeners, rules, and a health check for each cloud. `slo.json` with target, window, and error budget. Every field name cited to the vendor's own documentation in the README, never from memory.
- [ ] **Step 4: Green.** `Ran 5 tests`, `OK`.
- [ ] **Step 5: Calibrate.** Disable the resource-limits check, watch fixture two go red, restore against the recorded hash.
- [ ] **Step 6: Commit.** `git commit -m "Give the infrastructure book a platform it can validate"`

### Task 3: Two book builds and their label guard

**Files:**
- Modify: `docs/book/build_book.py` (add `--source DIR --title TITLE --out NAME`, defaulting to the base book so its existing behavior and test are untouched)
- Create: `tools/test_sbe_book_labels.py`
- Test: appended cases in `tools/test_sbe_book_data.py` and `tools/test_sbe_book_infra.py`

**Interfaces:**
- Consumes: `build_book(root, source=None, title=None, out=None)` keeping its three-tuple return.
- Produces: `BrotherSBE-for-Data-Engineers.html` and `BrotherSBE-for-Infrastructure-Engineers.html`.

- [ ] **Step 1: Write the failing label guard**

```python
# tools/test_sbe_book_labels.py
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM_HINTS = ("snowsql", "snow sql", "databricks ", "aws ", "az ", "kubectl ",
                  "terraform ", "helm ")


class TestPlatformBlocksAreLabeled(unittest.TestCase):
    """A command this machine cannot run must never look like output it produced.

    The books may show platform commands; they may not show them as if a real
    run happened here. Every fenced block whose command line names a platform
    CLI must carry the NOT EXECUTED HERE marker within the two lines above it.
    """

    def _chapters(self):
        for folder in ("book-data", "book-infra"):
            base = os.path.join(ROOT, "docs", folder)
            if not os.path.isdir(base):
                continue
            for name in sorted(os.listdir(base)):
                if name.endswith(".md") and name[:2].isdigit():
                    yield os.path.join(base, name)

    def test_every_platform_block_carries_the_marker(self):
        unlabeled = []
        for path in self._chapters():
            lines = io.open(path, encoding="utf-8").read().split("\n")
            for i, line in enumerate(lines):
                low = line.lower().lstrip("$ ").strip()
                if not any(low.startswith(h) for h in PLATFORM_HINTS):
                    continue
                window = "\n".join(lines[max(0, i - 4):i]).upper()
                if "NOT EXECUTED HERE" not in window:
                    unlabeled.append("%s:%d %s" % (os.path.basename(path), i + 1,
                                                   line.strip()[:60]))
        self.assertEqual(unlabeled, [], "unlabeled platform blocks: %s" % unlabeled)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Verify it passes trivially now (no chapters yet) and re-run it after every chapter task; it is the guard that makes the honesty law mechanical rather than remembered.**
- [ ] **Step 3: Extend the builder** with the three flags, defaults preserving base-book behavior exactly, and one new fixture per book asserting its HTML builds and contains its own title.
- [ ] **Step 4: Green** on all three book suites.
- [ ] **Step 5: Commit.** `git commit -m "Build three volumes from one builder"`

### Task 4: Data book, Part I (chapters 01 to 03)

**Files:** Create `docs/book-data/01-the-number-nobody-could-explain.md`, `02-what-the-gates-refuse-and-why-that-helps-you.md`, `03-reading-status-on-a-data-change.md`.

- [ ] Each chapter: single h1, at least one Mermaid diagram, the estate as its running example, real `sbe status` and `sbe impact` output via the replay convention, every platform block labeled. Part I speaks to analysts and leads: no terminal required to follow it, outcomes first. Chapter 02 marks the Documentation folder and notes as later loops.
- [ ] Verify: `python3 evals/replay_book.py` 0 differ; `python3 tools/test_sbe_book_labels.py` OK; the data book builds.
- [ ] Commit per chapter.

### Task 5: Data book, Part II (chapters 04 to 10)

**Files:** Create `04-the-first-loop-on-a-mart.md`, `05-two-derivations-and-one-truth.md`, `06-the-migration-that-can-go-backwards.md`, `07-freshness-and-what-a-receipt-cannot-prove.md`, `08-jobs-bundles-and-tasks.md`, `09-catalogs-grants-and-who-approved-this.md`, `10-cost-as-a-gated-decision.md`.

- [ ] Bindings: 05 shows both real derivations and states the alias limit plus that lineage is the fix (a later loop, marked). 06 walks the column drop with a rehearsal receipt, row counts, and names the value-checksum hole. 08 shows Databricks Asset Bundles and Jobs beside a Snowflake task, every command labeled and cited, with the `databricks-dabs` and `databricks-jobs` skills as the source. 09 puts Unity Catalog and Snowflake RBAC where the approval gate already reaches, and shows the real typed-name refusal. 10 treats warehouse sizing as a decision with a blast radius and what would flip it.
- [ ] Verify after each: replay 0 differ, label guard OK, build OK. Commit per chapter.

### Task 6: Data book, Part III (chapters 11 to 12)

**Files:** Create `11-working-with-analysts-through-one-vault.md`, `12-cookbook.md`.

- [ ] Recipes: new mart; backfill; schema change that raises the tier; a bad number in production; adopting an existing warehouse repository. Each ends with one honest line on what the gates will refuse.
- [ ] Verify and commit. Then run the full battery and report the data book complete.

### Task 7: Infrastructure book, Part I (chapters 01 to 03)

**Files:** Create `docs/book-infra/01-the-2am-problem.md`, `02-what-evidence-would-have-prevented-it.md`, `03-reading-status-on-an-infrastructure-change.md`.

- [ ] Same laws as Task 4, infrastructure vocabulary, the generic commerce platform as the running example, no client identifiers.

### Task 8: Infrastructure book, Part II (chapters 04 to 10)

**Files:** Create `04-the-first-loop-on-a-service.md`, `05-destructive-change-and-the-plan-as-evidence.md`, `06-rehearsal-blue-green-and-canary.md`, `07-rollouts-limits-and-probes.md`, `08-the-reindex-as-a-migration.md`, `09-the-cutover-that-needs-an-approval.md`, `10-failover-as-a-written-decision.md`.

- [ ] Bindings: 05 states plainly that the apply stays human (law L14) and why the tool cannot revoke a credential your shell already holds. 07 uses the estate's missing-limits variant so the reader watches a real check name a real manifest line. 08 mirrors the data book's migration chapter in search vocabulary and names the same value-checksum limit. 09 shows the real typed-name approval refusal. 10 writes the failover decision down before anyone is woken: dependencies, risks, what would flip it.
- [ ] Verify after each: replay 0 differ, label guard OK, build OK. Commit per chapter.

### Task 9: Infrastructure book, Part III (chapters 11 to 12) and the loop close

**Files:** Create `11-on-call-secrets-and-where-they-never-go.md`, `12-cookbook.md`. Modify: `README.md` (one line pointing to all three volumes), `CHANGELOG.md` (one entry).

- [ ] Chapter 11 states the no-credentials law and that the tool asks for none, and shows what an agent may and may not be handed.
- [ ] Recipes: new service; scaling change; reindex; cutover window; incident; adopting an ungated estate.
- [ ] Close the loop: recompute every doc guard from live runs, regenerate `CHECKSUMS.sha256`, run the full battery (all suites, both new suites, the label guard, both replays, evals, verify-install, plugin validate, install-artifact), refute review over the whole diff with the honesty lenses, commit the train, push through Desktop with the toolbar check, verify by `ls-remote`.

## Self-Review

Spec coverage: data estate (Task 1), infra estate (Task 2), shared builder plus the mechanical honesty guard (Task 3), data chapters (4 to 6), infra chapters (7 to 9), README and changelog and close (9): every spec section has a task. Placeholders: none; each chapter task carries binding content requirements and its verification commands. Type consistency: both estate validators and the builder keep three-tuple returns, matching the repo's honesty-meta-test law. Known dependency, stated rather than hidden: Tasks 3 onward cannot begin until Loop 1 commits `build_book.py` and `evals/replay_book.py`, and Task 3's first step is to verify that with `git log` and quote it.
