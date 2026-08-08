# The backend engineer's deep dive

## One engagement, told completely

This chapter follows one engineer through one real change, start to
finish, using commands chapters five through nine already introduced, plus
a few new ones: a payments-adjacent order flow gains a customer-facing
export endpoint.

Today, a partner who wants a day's regional totals gets them by email:
support runs the API by hand, copies the JSON it prints, and pastes it into
a spreadsheet. The engineer's job is one function that lets the partner's
own system call the export directly. Small code; the question of who else
can now reach this data is why the whole loop applies.

Every command below is the real `sbe` binary from this repository, pointed
at a scratch copy of the estate with `--cwd`, exactly as chapters five
through nine already do.

## Intake scores T2, and the engineer argues it up

Five answers, for a change that adds a new interface but changes no
existing contract's behavior and breaks nothing reversible:

```bash
rm -rf /tmp/sbe-book-ch13 /tmp/sbe-book-ch13-repo-sbe-T01
mkdir -p /tmp/sbe-book-ch13/dossier
printf 'y\nn\ny\nn\nsome\n' | bin/sbe intake /tmp/sbe-book-ch13/dossier
```

```
Does this change a data model, an API contract, or a file interface others depend on? (y/n) Does it cross a service, system, or team boundary? (y/n) Is it reversible in under an hour? (y/n) Does it touch money, partner data, personal data, or production state? (y/n) How many downstream consumers break if it is wrong? (none/some/many) tier T2 (artifacts required: 01, 02, 03, 05, 06, 07) written to /tmp/sbe-book-ch13/dossier/00-intake.json
To override this tier, edit that file and set all three fields: "tier" (the tier you are moving to), "override" (the same tier, declaring the move), and "override_reason" (at least 3 words and 12 characters). A move with any of the three missing or disagreeing FAILs the design check as an edit rather than an override.
```

T2, from `changes_contract`. But the fourth answer was `n`, and that is too
quick: the export hands a partner's own revenue numbers to an outside
caller for the first time, which is partner data by any honest reading. The
engineer raises the tier by hand, the way L15
(`references/laws-overrides-and-waivers.md`) requires: `tier` and
`override` set to the same value, plus a reviewable reason.

```bash
python3 - <<'EOF'
import json
p = "/tmp/sbe-book-ch13/dossier/00-intake.json"
d = json.load(open(p))
d["tier"] = "T3"
d["override"] = "T3"
d["override_reason"] = "this hands a partner's own revenue numbers to a brand new external caller"
json.dump(d, open(p, "w"), indent=2, sort_keys=True)
EOF
bin/sbe design artifacts /tmp/sbe-book-ch13/dossier
```

```
BROTHERSBE DESIGN CHECKS  (advisory unless --strict; NO-DATA is never a pass; WAIVED is not a pass either)
  scope      -        read 1 dossier under /tmp/sbe-book-ch13/dossier (.); 0 of 0 director(y/ies) directly under /tmp/sbe-book-ch13/dossier contributed no dossier
  dossier: . (under /tmp/sbe-book-ch13/dossier)
  artifacts  FAIL     tier T3 requires 01, 02, 03, 04, 05, 06, 07; missing: 01-purpose.md, 02-process.md, 03-adr.md, 04-technology-map.md, 05-data-model.md, 06-diagrams.md, 07-verification.md; declared override raising the tier to T3 from computed T2, reason: this hands a partner's own revenue numbers to a brand new external caller; examined . under /tmp/sbe-book-ch13/dossier [severity: gate]
```

The override took: T3 owes one more artifact than T2 did, and none exist
yet. A tier is a claim, not evidence; raising it honestly only raises how
much evidence is owed.

## Why arguing down is refused

Suppose a teammate, later, edits the tier back toward T2 without touching
`override`, hoping it quietly moves:

```bash
python3 - <<'EOF'
import json
p = "/tmp/sbe-book-ch13/dossier/00-intake.json"
d = json.load(open(p))
d["tier"] = "T2"
json.dump(d, open(p, "w"), indent=2, sort_keys=True)
EOF
bin/sbe design artifacts /tmp/sbe-book-ch13/dossier
```

```
BROTHERSBE DESIGN CHECKS  (advisory unless --strict; NO-DATA is never a pass; WAIVED is not a pass either)
  scope      -        read 1 dossier under /tmp/sbe-book-ch13/dossier (.); 0 of 0 director(y/ies) directly under /tmp/sbe-book-ch13/dossier contributed no dossier
  dossier: . (under /tmp/sbe-book-ch13/dossier)
  artifacts  FAIL     00-intake.json declares override 'T3' but records tier 'T2'; an override moves the tier field itself, so complete the edit by setting "tier" to 'T3' as well, or clear "override" to keep tier 'T2'. Two disagreeing tier fields cannot be audited; examined . under /tmp/sbe-book-ch13/dossier [severity: gate]
```

The refusal is about a field left behind, not about direction: a genuinely
reviewable move down runs through the same code path as a move up
(`tools/sbe_design.py` prints "lowering" or "raising" from one branch), but
a stored tier that disagrees with its own `override` field is an
undeclared edit, refused every time, either direction. The fix is the one
already on file: set `tier` back to `T3`, matching `override`.

## The dossier: seven artifacts, two worth reading

All seven get written next, then checked strict:

````bash
python3 - <<'EOF'
import json
p = "/tmp/sbe-book-ch13/dossier/00-intake.json"
d = json.load(open(p))
d["tier"] = "T3"
json.dump(d, open(p, "w"), indent=2, sort_keys=True)
EOF
cat > /tmp/sbe-book-ch13/dossier/01-purpose.md <<'EOF'
# Purpose

## What this changes

A partner today gets a day's regional totals by email: support runs
`api.py` by hand and pastes the JSON into a spreadsheet. This adds an
export function so the partner's own system can call it directly, as CSV.

## Why now

Every hand-run copy risks the wrong day, or the wrong partner's rows,
reaching the wrong reply. The export puts partner revenue one external
caller away from a route this API has never exposed before.

## Stakeholders

The partner calling it, the support team who stops running it by hand, and
whoever audits this API's data handling.
EOF
cat > /tmp/sbe-book-ch13/dossier/02-process.md <<'EOF'
# Process

## How this gets built

The export lands as its own function in `api.py`, reviewed against this
dossier, then landed through `sbe task open` and `sbe task close`.

## Who signs off

The reviewer confirms the export returns what `api.py` already serves.
EOF
cat > /tmp/sbe-book-ch13/dossier/03-adr.md <<'EOF'
# ADR: where the export capability lives

## Criteria

Operational load for a two-person team, how much isolation the export
needs, and how easily the next endpoint can reuse it.

## Rejected alternatives

- A standalone export service: right at four deploying teams, wrong today;
  one more deployable for one endpoint is load this team has nowhere to
  put.
- Bolting the handler into the existing request loop: fastest to ship, but
  the next feature needing the same totals would copy the logic, not call
  it.

## Decision

Add the export as its own function inside `api.py`, behind one interface,
rather than a new service or code pasted into the handler.

## Consequences

`api.py` gains one more responsibility, and `test_estate.py` gains the
coverage for it. Nothing about the deployment shape changes.

## What would flip this

Crossing four deploying teams, or needing the export to keep serving
partners while the rest of the API is down.
EOF
cat > /tmp/sbe-book-ch13/dossier/04-technology-map.md <<'EOF'
# Technology map

| Layer | Touched |
|---|---|
| `api.py` | gains one export function |
| `orders.csv`, `daily_totals.json` | read only |
| `test_estate.py` | one new test |

No new technology, no new datastore.
EOF
cat > /tmp/sbe-book-ch13/dossier/05-data-model.md <<'EOF'
# Data model

## Entities

- Partner: system of record: the partner directory this API reads.
- RegionTotal: system of record: `orders.csv`, aggregated into
  `daily_totals.json`.

## Relationships

- Partner to RegionTotal: one-to-many. The Partner's system can now call
  the export directly.
EOF
cat > /tmp/sbe-book-ch13/dossier/06-diagrams.md <<'EOF'
# Diagrams

## Context

```mermaid
flowchart LR
  Part[Partner] -->|GET export| Api[api.py export function]
  Api -->|reads today's rows| Reg[RegionTotal]
  Api -->|CSV response| Part
```

The arrow back to the Partner did not exist before this change.
EOF
cat > /tmp/sbe-book-ch13/dossier/07-verification.md <<'EOF'
# Verification

| claim | check | when |
|---|---|---|
| the export returns the same rows `api.py` serves for that date | `python3 test_estate.py` | before merge |
| the export refuses a date the pipeline has not run yet | `python3 test_estate.py` | before merge |
| the export does not change the existing `GET /totals` contract | `python3 test_estate.py` | before merge |
| the existing tests still pass with the export added | `python3 test_estate.py` | before merge |
EOF
bin/sbe design /tmp/sbe-book-ch13/dossier --strict | grep -E "^(  artifacts|  adr|  datamodel|  diagrams|  placeholder)"
````

```
  artifacts  PASS     tier T3: every required artifact present, carrying content, and naming subject matter the rest of this dossier also names; declared override raising the tier to T3 from computed T2, reason: this hands a partner's own revenue numbers to a brand new external caller; examined . under /tmp/sbe-book-ch13/dossier [severity: gate]
  adr        PASS     2 distinct rejected alternatives (each explicitly rejected in its own text, or listed beside an identified chosen option), each carrying at least 2 words and 8 characters of its own text (that the text says why the option lost, rather than restating its name, is human review), and criteria, decision, consequences and flip condition each carry content; examined . under /tmp/sbe-book-ch13/dossier [severity: gate]
  datamodel  PASS     2 entities, each with a system of record; 1 relationship line(s) read, each carrying cardinality; examined . under /tmp/sbe-book-ch13/dossier [severity: gate]
  diagrams   PASS     3 diagram node(s) in flowchart, all traceable: 2 to entities in 05-data-model.md, 0 to declared components, 0 to declared lifecycle states, 1 to a system of record an entity names; tokens read as diagram syntax rather than as nodes: flowchart LR (the diagram declaration: type and direction); examined . under /tmp/sbe-book-ch13/dossier [severity: gate]
  placeholder PASS     7 artifact(s) present, none still carrying an unfilled-template marker; examined . under /tmp/sbe-book-ch13/dossier [severity: gate]
```

Every check reads PASS, and `artifacts` quotes the override back. Two
artifacts, read straight off disk:

```bash
sed -n '/^## What this changes/,/^## Why now/p' /tmp/sbe-book-ch13/dossier/01-purpose.md | sed '$d'
```

```
## What this changes

A partner today gets a day's regional totals by email: support runs
`api.py` by hand and pastes the JSON into a spreadsheet. This adds an
export function so the partner's own system can call it directly, as CSV.

```

```bash
sed -n '/^## Rejected/,/^## Decision/p' /tmp/sbe-book-ch13/dossier/03-adr.md | sed '$d'
sed -n '/^## What would flip this/,$p' /tmp/sbe-book-ch13/dossier/03-adr.md
```

```
## Rejected alternatives

- A standalone export service: right at four deploying teams, wrong today;
  one more deployable for one endpoint is load this team has nowhere to
  put.
- Bolting the handler into the existing request loop: fastest to ship, but
  the next feature needing the same totals would copy the logic, not call
  it.

## What would flip this

Crossing four deploying teams, or needing the export to keep serving
partners while the rest of the API is down.
```

> Expert note: contract change discipline. Nothing here changes the shape
> `GET /totals` returns; the export is an addition, and
> `07-verification.md` says so as a test, not a sentence taken on faith. A
> genuine breaking change, one that removes a field or an operation an
> existing consumer reads, belongs in its own change with its own
> migration window, never folded into an addition touching the same file.

## The architecture decision, run for real

`03-adr.md` decided to keep the export inside the existing process rather
than spin up a second service. That decision came from `sbe decide`, the
architecture shape table chapter twelve's cookbook points at:

```bash
printf '2\nstrong\nmedium\nlow\n' | bin/sbe decide shape
```

```
deploying_teams (Independently deploying teams. Services below four teams usually cost more than they return.): consistency (Strong consistency across a service boundary is expensive and often accidental.): ops_maturity (On-call, tracing, and CI maturity. Without them a distributed estate is undebuggable.): failure_isolation (Does one component failing have to leave the others running?): 
Recommendation: modular monolith
Alternatives: monolith, services
Decided by:
  - deploying_teams=2 favours modular monolith, monolith
  - consistency=strong favours monolith, modular monolith
  - ops_maturity=medium favours modular monolith, services
  - failure_isolation=low favours monolith, modular monolith
What would flip this: Cross four independently deploying teams, or need one module to fail without the others while ops maturity is high, and revisit this decision.
```

Two teams, strong consistency, medium ops maturity, low need for one part
to fail without the rest: `modular monolith` wins, and `monolith` and
`services` are the two the ADR names and rejects. The flip condition is the
same sentence the ADR's own "What would flip this" carries. The table did
not write the ADR; it gave the same conclusion a second, independent way to
be reached.

## The plan, derived mechanically

`sbe plan` reads the dossier's own structures, no invention allowed, and
turns them into a task graph:

```bash
bin/sbe plan /tmp/sbe-book-ch13/dossier --write | grep -E "^(BROTHERSBE PLAN|  derive|sbe_plan:)"
```

```
BROTHERSBE PLAN  (verdicts are PASS, FAIL, NO-DATA; absent evidence is NO-DATA and never a pass; an empty plan never exits 0)
  derive         -        wrote 08-plan.json with 5 task(s) derived from the dossier
sbe_plan: 0 FAIL, 4 NO-DATA, 5 PASS across 9 check(s)
```

5 tasks, 0 FAIL, all 9 validation checks either PASS or an honest NO-DATA.
One writer task, `T01`, quotes the ADR's decision sentence and owns
`api.py` and `test_estate.py`, the two paths it names. Four reviewer
tasks, `T02` through `T05`, one per verification row, own nothing and each
carry `python3 test_estate.py`. The `compatibility` check reads PASS
because one row names the existing contract; without that, it would FAIL
rather than assume silence means safety. `migration` and `calculation`
read NO-DATA because nothing here is a migration and no claim carries a
number to derive twice, correct, not a gap. `graph` reads NO-DATA for a
reason worth sitting with: the planner only serializes two *writer* tasks
that own the same path; it never draws an edge saying "verify only after
you build," so nothing mechanically stops a reviewer task from starting
before `T01` lands. That ordering is still the human's job.

## The task registry, and the work pair

`sbe task open` and `sbe task close`, chapter seven's registry, still sit
underneath everything. `sbe work` sits on top of it: one branch, one git
worktree, per task, so an engineer writes without anyone else's edits
landing in the same tree by accident. Seeding a clean copy of the estate
first, the same reason as every scratch demo in this book:

```bash
ROOT="$(pwd)"
rm -rf /tmp/sbe-book-ch13/repo /tmp/sbe-book-ch13/repo-sbe-T01
mkdir -p /tmp/sbe-book-ch13/repo
cd /tmp/sbe-book-ch13/repo
git init -q
git config user.email "estate@example.invalid"
git config user.name "Estate Seed"
cp "$ROOT/docs/book/estate/pipeline.py" .
cp "$ROOT/docs/book/estate/api.py" .
cp "$ROOT/docs/book/estate/test_estate.py" .
git add pipeline.py api.py test_estate.py
export GIT_AUTHOR_NAME="Estate Seed" GIT_AUTHOR_EMAIL="estate@example.invalid"
export GIT_COMMITTER_NAME="Estate Seed" GIT_COMMITTER_EMAIL="estate@example.invalid"
export GIT_AUTHOR_DATE="2026-07-01T00:00:00" GIT_COMMITTER_DATE="2026-07-01T00:00:00"
git commit -q -m "seed the export-endpoint demo with a copy of the estate"
BASE="$(git rev-parse HEAD)"
echo "base commit $BASE"
```

```
base commit 5eb044aac3d05693f0d662caf42eeca95fb96e94
```

```bash
"$ROOT/bin/sbe" work start T01 --plan /tmp/sbe-book-ch13/dossier/08-plan.json --cwd /tmp/sbe-book-ch13/repo
```

```
sbe work start: the plan records no baseCommit, so the branch is created at HEAD: UNPINNED, not a commit the plan was derived against
sbe task open: T01 is open. unnamed (writer) owns 2 path(s): api.py, test_estate.py. Base 5eb044aac3d0. Close runs the diff postcondition against exactly this declaration.
sbe work start T01: branch sbe/dossier/T01 at 5eb044aac3d0, worktree /private/tmp/sbe-book-ch13/repo-sbe-T01, registry record open.
acceptance criteria:
  - Add the export as its own function inside `api.py`, behind one interface, rather than a new service or code pasted into the handler.
verification commands:
  (none recorded on this task)
dossier sources:
  - 03-adr.md#decision
```

`sbe work start` printed `sbe task open` itself: one registry, two front
doors. The worktree is a fresh checkout, isolated from the main copy. The
edit itself, in that worktree: `export_totals_csv`, calling the existing
`get_totals` and reformatting its rows, plus two new tests:

```bash
WT=/tmp/sbe-book-ch13/repo-sbe-T01
python3 - "$WT" <<'PATCH'
import sys
path = sys.argv[1] + "/api.py"
text = open(path).read()
old = '''    return 200, {"date": date, "rows": rows}, "ok"


if __name__ == "__main__":
    status, body, _note = get_totals(sys.argv[1] if len(sys.argv) > 1 else "2026-07-01")
    sys.stdout.write("%d %s\\n" % (status, json.dumps(body, sort_keys=True)))
    sys.exit(0 if status == 200 else 1)'''
new = '''    return 200, {"date": date, "rows": rows}, "ok"


def export_totals_csv(date):
    """The partner-facing export: get_totals's own rows, as CSV text."""
    status, body, note = get_totals(date)
    if status != 200:
        return status, body, note
    lines = ["date,region,total_eur"]
    for row in body["rows"]:
        lines.append("%s,%s,%s" % (row["date"], row["region"], row["total_eur"]))
    return 200, "\\n".join(lines) + "\\n", note


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else "2026-07-01"
    if len(sys.argv) > 2 and sys.argv[2] == "--csv":
        status, body, _note = export_totals_csv(date)
        sys.stdout.write(body if status == 200 else
                         "%d %s\\n" % (status, json.dumps(body, sort_keys=True)))
        sys.exit(0 if status == 200 else 1)
    status, body, _note = get_totals(date)
    sys.stdout.write("%d %s\\n" % (status, json.dumps(body, sort_keys=True)))
    sys.exit(0 if status == 200 else 1)'''
assert old in text
open(path, "w").write(text.replace(old, new, 1))
PATCH
python3 - "$WT" <<'PATCH'
import sys
path = sys.argv[1] + "/test_estate.py"
text = open(path).read()
old = '''    def test_the_api_refuses_before_the_pipeline_ran(self):
        out = subprocess.run([sys.executable, os.path.join(HERE, "api.py"),
                              "2026-07-01"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        self.assertIn("run pipeline.py first", out.stdout)


if __name__ == "__main__":'''
new = '''    def test_the_api_refuses_before_the_pipeline_ran(self):
        out = subprocess.run([sys.executable, os.path.join(HERE, "api.py"),
                              "2026-07-01"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        self.assertIn("run pipeline.py first", out.stdout)

    def test_the_export_matches_what_the_api_already_serves(self):
        refused = subprocess.run([sys.executable, os.path.join(HERE, "api.py"),
                                  "2026-07-01", "--csv"], capture_output=True, text=True)
        self.assertEqual(refused.returncode, 1)
        self._pipeline("2026-07-01")
        served = subprocess.run([sys.executable, os.path.join(HERE, "api.py"),
                                 "2026-07-01"], capture_output=True, text=True)
        exported = subprocess.run([sys.executable, os.path.join(HERE, "api.py"),
                                   "2026-07-01", "--csv"], capture_output=True, text=True)
        self.assertEqual(exported.returncode, 0)
        body = json.loads(served.stdout.split(" ", 1)[1])
        for row in body["rows"]:
            line = "%s,%s,%s" % (row["date"], row["region"], row["total_eur"])
            self.assertIn(line, exported.stdout)


if __name__ == "__main__":'''
assert old in text
open(path, "w").write(text.replace(old, new, 1))
PATCH
(cd "$WT" && python3 test_estate.py 2>&1 | sed -E 's/[0-9]+\.[0-9]+s/<N.NNNs>/')
```

```
test_a_date_with_no_orders_writes_no_rows (__main__.TestEstate) ... ok
test_the_api_refuses_before_the_pipeline_ran (__main__.TestEstate) ... ok
test_the_api_serves_what_the_pipeline_wrote (__main__.TestEstate) ... ok
test_the_export_matches_what_the_api_already_serves (__main__.TestEstate) ... ok
test_the_pipeline_totals_by_region (__main__.TestEstate) ... ok

----------------------------------------------------------------------
Ran 5 tests in <N.NNNs>

OK
```

Five tests, all green: the new one checks the refusal and the match in one
pass, the same shape chapter nine's own test used. Now the finish, twice,
refused both times, for two different and equally real reasons:

```bash
"$ROOT/bin/sbe" work finish T01 --cwd /tmp/sbe-book-ch13/repo
```

```
  VIOLATION  daily_totals.json
  VIOLATION  orders.csv
sbe work finish T01: FAIL. 2 changed path(s) outside the declaration, named above; closure is refused. Close with --force --who --why to record a disposition, never to make this clean.
```

Running the suite regenerated the pipeline's own output files inside the
worktree, and `T01` never declared ownership of them. The registry does not
know or care that these are "just" generated data; it reads the diff, sees
two paths outside the declaration, and refuses, exactly the way chapter
seven's stray `rogue-note.txt` was refused. The fix is the same one: remove
what the task never claimed, then ask again.

```bash
rm -f /tmp/sbe-book-ch13/repo-sbe-T01/daily_totals.json /tmp/sbe-book-ch13/repo-sbe-T01/orders.csv
"$ROOT/bin/sbe" work finish T01 --cwd /tmp/sbe-book-ch13/repo
```

```
sbe work finish T01: NO-DATA. The record carries no verification command, so no receipt can answer for the work and closure is refused.
```

This is the finish refusal without a receipt, and it names a real limit:
`T01` came from the ADR's own decision sentence, and prose carries no
command, so the planner gave it nothing to verify against. `sbe work
finish` will never close `T01` clean; the verification lives on `T02`
through `T05`, the reviewer tasks the table derived. `T01` closes through
the older, plainer registry instead, asking only whether the diff matches
the declaration:

```bash
"$ROOT/bin/sbe" task close T01 --cwd /tmp/sbe-book-ch13/repo
```

```
  IN-SCOPE   api.py
  IN-SCOPE   test_estate.py
sbe task close T01: PASS. 2 changed path(s), all inside the declaration. Closed clean.
```

The engineer commits on the branch and merges it in, a plain git operation
this tool does not perform and never will:

```bash
cd /tmp/sbe-book-ch13/repo-sbe-T01
git add api.py test_estate.py
export GIT_AUTHOR_NAME="Engineer A" GIT_AUTHOR_EMAIL="engineer-a@example.invalid"
export GIT_COMMITTER_NAME="Engineer A" GIT_COMMITTER_EMAIL="engineer-a@example.invalid"
export GIT_AUTHOR_DATE="2026-07-02T00:00:00" GIT_COMMITTER_DATE="2026-07-02T00:00:00"
git commit -q -m "add the partner-facing CSV export to api.py"
cd /tmp/sbe-book-ch13/repo
git merge --ff-only sbe/dossier/T01 -q
CLEAN_HEAD="$(git rev-parse HEAD)"
echo "landed $CLEAN_HEAD"
```

```
landed 9615e906d0b0c2bff5291974ca55f4eb9f868f25
```

```mermaid
sequenceDiagram
  participant E as engineer
  participant R as .sbe/tasks.json
  participant W as worktree sbe/dossier/T01
  E->>R: work start T01
  R-->>E: branch + worktree created
  E->>W: edit api.py, test_estate.py; run tests
  E->>R: work finish T01
  R-->>E: FAIL, VIOLATION daily_totals.json, orders.csv
  E->>W: remove the generated files
  E->>R: work finish T01
  R-->>E: NO-DATA, no verification command
  E->>R: task close T01
  R-->>E: PASS, closed clean
  E->>E: commit; git merge into main
```

> Expert note: when to split a change. Everything above landed as one task
> because the ADR named one decision. A change big enough to need two
> genuinely independent decisions, say, the export function and a separate
> rate limit in front of it, is a sign to write two dossiers, not one T3
> with two ADRs stapled together. The tell is the plan: if `sbe plan
> --write` would have to invent a task the dossier's structures do not
> support, the dossier is describing more than one change.

## The evidence, and what four gates say about it

One receipt covers the claim every verification row in this dossier makes:

```bash
mkdir -p /tmp/sbe-book-ch13/repo/.sbe/evidence
rm -f /tmp/sbe-book-ch13/repo/daily_totals.json /tmp/sbe-book-ch13/repo/orders.csv
"$ROOT/bin/sbe" evidence run --out /tmp/sbe-book-ch13/repo/.sbe/evidence/export-receipt.json --covers api.py --covers test_estate.py --cwd /tmp/sbe-book-ch13/repo -- python3 test_estate.py 2>/dev/null | sed -E 's/[0-9]+\.[0-9]+s/<N.NNNs>/'
```

```

sbe evidence run: FREE FORM run: no registered check, so this receipt is advisory and satisfies no required policy check
sbe evidence run: receipt written to /tmp/sbe-book-ch13/repo/.sbe/evidence/export-receipt.json. Trust LOCAL-ADVISORY (this receipt was minted for a free-form command rather than a check registered in .sbe/checks.yml, so nothing outside the caller says which check it is. Free-form evidence is advisory whatever else is true of it). Command exited 0 in <N.NNNs>, over 2 covered file(s) from explicit --covers. Declared check kind(s): none, so this receipt clears no design, gate or score obligation. stdout and stderr are recorded as digests only. argv held 0 secret-shaped token(s) and was recorded verbatim.
```

`sbe evidence show` prints the receipt back verbatim; the lines below are
the ones that matter, none of them wall-clock or hash noise:

```bash
"$ROOT/bin/sbe" evidence show /tmp/sbe-book-ch13/repo/.sbe/evidence/export-receipt.json | grep -E "^(trust|command|argv redacted|base commit|head commit|covers)"
```

```
trust          LOCAL-ADVISORY (this receipt was minted for a free-form command rather than a check registered in .sbe/checks.yml, so nothing outside the caller says which check it is. Free-form evidence is advisory whatever else is true of it)
command        python3 test_estate.py
argv redacted  no (0 secret-shaped token(s) matched; the command above is verbatim)
base commit    5eb044aac3d05693f0d662caf42eeca95fb96e94
head commit    80460e92b661cfaaf65b99e783b93617bd108643
covers         explicit --covers (2 file(s))
```

Now the four hard gates, read together, one line each:

```bash
"$ROOT/bin/sbe" gate /tmp/sbe-book-ch13/repo
```

```
BROTHERSBE HARD GATES  (advisory unless --strict; NO-DATA is never a pass; WAIVED is not a pass either)
  numbers   NO-DATA  no numbers-manifest found; if this change presents no decision figure that is correct, else add one; no numbers-manifest.json read under /tmp/sbe-book-ch13/repo; 1 of 1 director(y/ies) directly under /tmp/sbe-book-ch13/repo contributed no numbers-manifest.json (.sbe) [severity: gate]
  migration NO-DATA  no migration in this change, or no migration-receipt.json; no migration-receipt.json read under /tmp/sbe-book-ch13/repo; 1 of 1 director(y/ies) directly under /tmp/sbe-book-ch13/repo contributed no migration-receipt.json (.sbe) [severity: gate]
  approval  NO-DATA  no APPROVAL file and no Approved-by trailer; if this change touches no money or partner path that is correct; no APPROVAL read under /tmp/sbe-book-ch13/repo; 1 of 1 director(y/ies) directly under /tmp/sbe-book-ch13/repo contributed no APPROVAL (.sbe) [severity: gate]
  ran       NO-DATA  no ran-receipt.json; a SQL or pipeline change is not done until its check executed and left a receipt; no ran-receipt.json read under /tmp/sbe-book-ch13/repo; 1 of 1 director(y/ies) directly under /tmp/sbe-book-ch13/repo contributed no ran-receipt.json (.sbe) [severity: gate]

sbe gate: 0 decision package(s) written: no FAIL and no WAIVED line was printed above. A package records a decision somebody has to carry, and a PASS or a NO-DATA is not one.
```

`numbers`, `migration`, and `ran` are honest absences: nothing here
presents a decision figure, touches a migration, or runs a SQL or pipeline
check, so NO-DATA is correct, not a weaker answer. `approval` is worth
pausing on: its own sentence says "if this change touches no money or
partner path, that is correct," and this dossier's whole T3 override argues
the opposite. The gate does not know that; it reads this commit's own files
and trailers, and this commit carries neither an `APPROVAL` file nor a
trailer. That is the honest gap left open here, on purpose: the dossier's
claim and the gate's evidence are two different things, and closing it for
real means adding the `APPROVAL` file or `Reviewed-in` trailer chapter
eight walks through, bound to this exact commit, before the change
ships.

## Convergence, on a drifted-scope example

`sbe converge` checks a range of commits against the dossier's plan, not
against the diff alone:

```bash
rm -f /tmp/sbe-book-ch13/dossier/09-convergence.json
"$ROOT/bin/sbe" converge /tmp/sbe-book-ch13/dossier --base "$BASE" --head "$CLEAN_HEAD" --cwd /tmp/sbe-book-ch13/repo
```

```
SCOPE         PASS
  PASS            2 changed file(s), every one owned by a plan task or named by the dossier
CONTRACTS     NO-DATA
  NO-DATA         no contract-shaped file changed in this range
DATA          NO-DATA
  NO-DATA         no migration-shaped file changed in this range
ARCHITECTURE  NO-DATA
  NO-DATA         architecture comparison is name-level only; no new top-level directory appeared in this range
VERIFICATION  PASS
  PASS            python3 test_estate.py has a sealed receipt bound to 9615e906d0b0

FINAL PASS  (dossier ../dossier, 5eb044aac3d0..9615e906d0b0)
not examined (NO-DATA, named rather than counted clean): CONTRACTS, DATA, ARCHITECTURE
```

Clean. Now the drift: one more commit lands on top, a stray note nobody
declared anywhere, the kind of thing that slips into a branch between
"done" and "merged":

```bash
echo "reminder: ask finance about Q3 numbers" > scratch-notes.txt
git add scratch-notes.txt
export GIT_AUTHOR_NAME="Engineer A" GIT_AUTHOR_EMAIL="engineer-a@example.invalid"
export GIT_COMMITTER_NAME="Engineer A" GIT_COMMITTER_EMAIL="engineer-a@example.invalid"
export GIT_AUTHOR_DATE="2026-07-02T00:20:00" GIT_COMMITTER_DATE="2026-07-02T00:20:00"
git commit -q -m "add scratch-notes.txt"
"$ROOT/bin/sbe" converge /tmp/sbe-book-ch13/dossier --base "$BASE" --head "$(git rev-parse HEAD)" --cwd /tmp/sbe-book-ch13/repo
```

```
SCOPE         REVIEW-REQUIRED
  REVIEW-REQUIRED scratch-notes.txt changed but no plan task owns it and no dossier artifact names it: unplanned but potentially legitimate
CONTRACTS     NO-DATA
  NO-DATA         no contract-shaped file changed in this range
DATA          NO-DATA
  NO-DATA         no migration-shaped file changed in this range
ARCHITECTURE  NO-DATA
  NO-DATA         architecture comparison is name-level only; no new top-level directory appeared in this range
VERIFICATION  FAIL
  FAIL            the receipt for python3 test_estate.py binds to 9615e906d0b0, not the assessed head 112dcc3917bf: stale evidence from another commit

FINAL FAIL  (dossier ../dossier, 5eb044aac3d0..112dcc3917bf)
not examined (NO-DATA, named rather than counted clean): CONTRACTS, DATA, ARCHITECTURE
```

Two things broke at once, and neither is a false alarm. SCOPE catches the
file nobody planned, by name. VERIFICATION catches something sharper: the
one real receipt this dossier has is bound to the commit before the drift,
not the one convergence was asked to assess. The same receipt that made
VERIFICATION read PASS a moment ago now reads FAIL, because evidence bound
to a commit stops being evidence for any other commit, no matter how small
the gap between them.

## `pr verify`, shown honestly

`sbe pr verify` checks a pull request's own approval evidence on GitHub,
live. This book runs the real command and shows the real refusal; it does
not verify an actual pull request, because there is no pull request behind
this scratch repository, and because the reference machine this project is
built on has no GitHub token configured, same as most CI runners:

```bash
env -u GITHUB_TOKEN -u GH_TOKEN PATH=/usr/bin:/bin "$ROOT/bin/sbe" pr verify 412 --repo example-org/order-flow --cwd /tmp/sbe-book-ch13/repo 2>&1 | grep -E "^(sbe pr verify:|token source:|  PR EXISTS|  INDEPENDENT APPROVAL|FINAL)"
```

```
sbe pr verify: example-org/order-flow #412
token source: none found
  PR EXISTS              NO-DATA       no token was found in GITHUB_TOKEN or GH_TOKEN and gh auth token supplied none; export GITHUB_TOKEN or run gh auth login, then re-run
  INDEPENDENT APPROVAL   NO-DATA       no token was found in GITHUB_TOKEN or GH_TOKEN and gh auth token supplied none; export GITHUB_TOKEN or run gh auth login, then re-run
FINAL NO-DATA  no token was found in GITHUB_TOKEN or GH_TOKEN and gh auth token supplied none; export GITHUB_TOKEN or run gh auth login, then re-run
```

Every one of the nine controls this command checks reads NO-DATA for the
same honest reason: no token, so zero network requests were made, stated
plainly in the command's own docstring. This is not a weaker check standing
in for a real one; it is the real check, reporting the true state of this
machine, on a pull request that does not exist. Wired into CI with a token,
`PR EXISTS` and the rest would read a real verdict against a real head
commit; here, the honest answer is that nothing was checked.

> Expert note: what `sbe impact` reads from a diff. Run on this same range
> it shows two `UNMEASURED` lines, not two `PASS` lines: its detectors look
> for specific shapes (a migration path, raw SQL DDL, a partner-path
> pattern, an OpenAPI file), and plain code like `api.py` matches none of
> them. `UNMEASURED` means "not examined," never folded into a false PASS.
> And `read_intake` (`src/brothersbe/impact.py`) recomputes the declared
> tier from the intake's five answers alone; it never reads `override`.
> After an override, `sbe impact` compares against the tier the answers
> alone give, not the tier a human moved to. Reconcile against the tier a
> human declared with `sbe design`'s own re-derivation, the one that
> printed "raising" earlier, not with this command.

> Expert note: the migration triplet and rehearsal against a restore.
> Nothing here touches one, so `gate migration` read NO-DATA.
> `gate_migration` (`tools/sbe_gate.py`, line 825) demands three things at
> once: a forward leg marked `ran_against_restore: true`, a reverse leg
> carrying the same mark plus a `rehearsal_run_id`, and matching
> `row_counts` before the forward ran and after the reverse undid it. A
> migration tested only forward, against a database with last night's
> backup untouched, proves the migration runs; it says nothing about
> whether reversing it gets the row counts back, which is the whole point
> of rehearsing against a restore.

## The day shape

What the engineer typed this morning: five answers, honestly, then one
override, written down with a reason. What they will never type again for
this change: the tier itself, which the design check re-derives from the
answers every time it runs, so a hand-edited number is caught, not trusted.

```mermaid
flowchart LR
  Intake["intake: T2"] --> Override["override: T3"]
  Override --> Dossier["7 artifacts: design --strict PASS"]
  Dossier --> Decide["decide: modular monolith"]
  Decide --> Plan["plan: T01 + 4 reviewers"]
  Plan --> Work["work: finish refused twice"]
  Work --> TaskClose["task close: PASS"]
  TaskClose --> Evidence["evidence run: sealed receipt"]
  Evidence --> Gates["4 gates: 3 NO-DATA, 1 gap"]
  Gates --> Converge["converge: PASS, FAIL on drift"]
  Converge --> PR["pr verify: honest NO-DATA"]
```

Nothing on that diagram was invented for the demo. Every arrow is a
command a working engineer runs, in this order, because each one reads
what the last one actually did rather than trusting a sentence about it.
The tier came from five answers, not a feeling. The architecture came from
a table, not a preference. The plan came from the dossier's own words, not
a guess at intent. The receipt came from a command that ran, not a claim
that it ran. And the one gap left open, the missing `APPROVAL` evidence,
stays open on the page rather than quietly closed, because that is exactly
what an honest run of this loop looks like the moment before somebody adds
it.
