# Read me first

BrotherSBE reviews engineering design work and reports what it checked.

## What it does

Two things, both mechanical.

**It checks design artifacts before you build.** Five checks over a directory of
markdown files: are the artifacts your change's tier requires present and filled
in, does the decision record carry rejected alternatives and a flip condition,
does every entity name its system of record, does every diagram node trace to
something declared elsewhere, is any file still the shipped template.

**It checks four verification receipts after you build.** Numbers (a figure was
re-derived independently against a pinned snapshot), migration (forward and
reverse both ran against a restored copy and the row counts match), approval (an
approval is bound to something stronger than a name typed in a box), ran (a check
actually executed, with a zero exit and a nonzero duration).

There is also a linter for the code patterns that swallow errors: bare except,
except-then-pass, discarded subprocess result, conflict-skipping upsert.

## What it refuses to do

It refuses to print PASS over evidence it did not examine. That is the whole
product. Concretely, and each of these is a run made in this repository:

- An absent receipt is `NO-DATA`, never PASS. So is a receipt that exists and
  records nothing.
- A receipt that exists and cannot be parsed is `FAIL`, because a broken claim is
  not an absent one.
- A field holding `TODO`, `TBD`, `pending`, `n/a` or `???` is not an answer.
  `snapshot_id: "TODO"` fails and the message quotes the value.
- A second derivation that is the first query re-pasted with a comment on the end
  fails, and the message says so in those words.
- A check that crashes is reported as a FAIL carrying the exception, never as a
  missing line.
- A waiver prints as `WAIVED`, never as PASS, and the run tells you a waiver
  happened.
- A code scan where every finding was waived reports `NO-DATA`, not clean.

Every verdict line states its own limits inline. They are long on purpose. Read
one and you know exactly what was and was not asserted.

Every verdict also names its own scope. A design run opens with a `scope` line
saying how many dossiers it read under the directory you named and how many
directories directly under it contributed nothing, and each verdict repeats the
dossier it examined. The hard gates name the receipt files they read and list the
directories that produced none. A verdict you cannot attribute to a file is a
verdict you cannot check.

## What it will NOT do for you

- It does not know whether your design is good. It knows whether the artifact is
  complete and internally consistent. "Did this alternative really lose for the
  reason written" is human judgement, and the tool says so in its own PASS line.
- It does not enforce anything until you wire `--strict` into CI. Locally it
  prints verdicts and exits 0.
- It does not resolve a `Reviewed-in:` id against anything. That path is
  `NO-DATA` by design, and the tool tells you it is a pointer, not a control.
- It does not notice that a change *needed* an approval. It only verifies one
  that was declared.
- It does not prove two derivations are independent. It proves their text
  differs. Renaming an alias passes. The PASS sentence says exactly that.
- It does not open a network connection, call an API, or read a model.
- It writes nothing outside the directory you point it at (plus the vault path,
  if you set one).

## The one command that proves it works on your machine

From the clone:

```
python3 evals/run_evals.py
```

Every check is run against the defect it exists to catch. Real output from this
machine, last line:

```
536 evals: 536 passed, 0 regressions.
```

Exit code 0. It exits nonzero if any check stops catching its defect. The case
count moves as the suite grows, so read the "0 regressions" and not the total.

## Ten more minutes?

`01-install-and-first-run.md` is the install, verified end to end. Then read the
file for your role:

| Role | File | Built around |
|---|---|---|
| Backend | `10-backend-engineer.md` | Idempotency keys on a POST endpoint |
| Data | `11-data-engineer.md` | A daily revenue mart, with its data model |
| Infrastructure | `12-infrastructure-architect.md` | Two-region active-passive, with the technology map and the decision record |
| ETL | `13-etl-builder.md` | Nightly partner settlement load, with its verification receipts |

Then `20-what-it-will-not-tell-you.md` before you trust a green run, and
`30-adopting-it-on-a-team.md` before you put it in CI.
