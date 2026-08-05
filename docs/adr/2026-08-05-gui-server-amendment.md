# ADR: a loopback-only GUI workspace amends the no-server promise

Date: 2026-08-05. Status: accepted, gate LP-0301. Docs-only lane: no GUI code
ships in this change.

## Context

`SECURITY.md`, `docs/THREAT_MODEL.md`, `README.md`, and
`design/final-release-program/01-purpose.md` all promise, in close to
identical wording, that BrotherSBE has "no analytics, no account, and no
server." That claim is not prose someone could quietly let rot: it is a hard
gate. `tools/test_sbe.py`'s `TestAuditableSurface.test_the_zero_network_property_holds_by_ast`
AST-parses every file under `tools/`, `src/brothersbe/`, `hooks/`,
`scripts/`, `bin/sbe`, and `install.sh`, and fails if any of them, other than
the one allow-listed exception `src/brothersbe/prverify.py`, imports
`urllib`, `requests`, `socket` or `http`.

The founder has twice ratified keeping that promise as written. On
2026-08-04, `docs/release-1.0/FABLE-PLAN-REVIEW.md` section 8 records: "Founder
decision, 2026-08-04: keep the no-server promise... Gate 4 is amended
accordingly and the GUI is deferred past 1.0." The accepted replacement was
PT-3 (`docs/plans/2026-08-04-parity-triage-verdict.md`): a deterministic
visual map generated from `sbe status --json` as a static artifact, no
server, no loopback socket, nothing the AST test forbids. That work landed
and it remains the right answer for the problem it solves: a page that shows
the same state the command line prints, regenerated on demand.

Gate LP-0301, opened 2026-08-05, is a narrower and separate request: a
workspace a person can leave open and interact with across a working
session, not a page regenerated and reloaded after each command. A static
template cannot do that by construction; it has no channel back to a running
session and no way to reflect a change without a full regeneration and a
manual reload. The founder's recorded 2026-08-05 decision reopens the no-server
promise specifically for this shape of surface, and specifically at the
loopback boundary: no REMOTE server, no outbound network traffic from any GUI
code, and a process that binds `127.0.0.1` and nothing else is authorized.

This ADR records that decision and its shape. It does not write
`src/brothersbe/gui/server.py`; it reserves that exact path so a future lane
can build to it without re-litigating whether the security boundary permits
it.

## Criteria

Named, in the order they were weighed:

- **Boundary.** What must stay impossible even after this amendment: any
  BrotherSBE code reaching a network address other than the two exceptions
  already named in `SECURITY.md` (`sbe pr verify`'s GitHub call, `install.sh`'s
  git remotes). A workspace reachable from a second device, a workspace that
  phones a vendor, or a workspace an unauthenticated local process can drive
  are all outside this boundary regardless of how convenient any of them
  would be to build.
- **Auditability.** The promise document's own instruction, "you can verify
  this yourself," must keep being true after the amendment: a reader who runs
  the grep `SECURITY.md` gives them must see the true state of the tree, not
  a claim that quietly drifted from what is on disk.
- **Blast radius.** How many files gain network capability by this decision.
  The answer this ADR commits to is exactly one, named by its exact path, not
  by directory: `src/brothersbe/gui/*` other than `server.py` stays banned,
  so a second file cannot inherit the exception by living next to the first.
- **Reversibility.** How the gate closes again if the workspace is abandoned
  or the decision is reversed: deleting one allowlist entry and one file, not
  unwinding a distributed system.
- **Standing constraints unchanged by this decision.** Python 3.9 standard
  library only (no new dependency to reach for a "just use a real framework"
  shortcut), and the existing two named network exceptions keep their own
  scope untouched.

## Options considered

### Rejected: keep the generated page only (PT-3, the 2026-08-04 decision)

`sbe status --json` already generates a deterministic static map into
`skills/help/map-template.html`, and it satisfies the letter of the no-server
promise perfectly: no socket, no process left running, nothing the AST test
forbids. It was the right call for the problem it was built to solve, and
this ADR does not undo it.

It is the wrong shape for what LP-0301 asks for. A static file has no channel
back into a running session: it cannot reflect a change in status without
someone re-running the generator and reloading the page by hand, it cannot
accept an input and act on it (there is nothing on the other end to receive
one), and "workspace" implies something a person leaves open and returns to,
which a regenerate-and-reload artifact structurally is not. Extending the
template generator further (more computed slots, a client-side poll of a
file that nothing refreshes) would spend real engineering effort building an
increasingly elaborate simulation of a live surface without ever becoming
one, and the drift risk PT-3 was built to close (a model deriving the page by
hand and disagreeing with the command line) would return the moment the
simulation grew a hand-authored refresh path of its own.

### Rejected: a cloud or remote UI (a hosted dashboard, first-party or
third-party)

A hosted web app reachable over the network would give the workspace
something loopback cannot: reachability from a second device, and state that
survives the local machine being off. Both are real capabilities, genuinely
wanted by some future ask, and rejected here on the same boundary criterion
that governs everything else in this document.

A remote UI is not a bigger version of a loopback server; it is a different
class of thing this project has stated, repeatedly and specifically, that it
will not be. "No account" fails outright: a hosted service needs one, even if
BrotherSBE's own code never asks for a password, because a URL an operator
did not run themselves implies a party that operates it. "You can verify this
yourself" fails too: `SECURITY.md`'s audit story is a local grep the reader
runs against code they have on disk; a remote server's code is not on that
disk, by definition, so the entire "don't take our word for it, check" method
this project uses everywhere else stops working for exactly the surface that
would be doing the most with the user's session data. And the standard-library,
zero-dependency, zero-hosting-infrastructure posture that lets a solo user
audit 34,627 lines with one grep does not survive contact with a deployment
pipeline, a TLS certificate, and a party who operates the box. Reachability
from a second device is a real want; it does not clear the boundary this ADR
was written to hold, and nothing about "the local option should also be
convenient across devices" changes that a remote party then holds a copy of
this session's state.

## Decision

Amend the promise from "no server" to "no remote server; a loopback-only
workspace is authorized," concretely:

- `SECURITY.md`'s promise paragraph is rewritten (this lane) to state the new
  boundary and point back to this ADR, and the audit-grep prose is rewritten
  so a reader running the grep today still finds it true: the reserved path
  does not exist yet, so it produces no hit, and the prose says so rather
  than implying a hit that is not there.
- `tools/test_sbe.py`'s zero-network AST scan (this lane) gains one named
  allowlist entry, the exact path `src/brothersbe/gui/server.py`, which does
  not exist in this tree, so the scan's behavior against the real repository
  is unchanged today. The scan is also extended to walk
  `src/brothersbe/gui/` recursively rather than stopping at the top level of
  `src/brothersbe/`, so any OTHER file placed under `gui/` stays banned by
  the same rule as every other file in the tree; the allowlist covers one
  path, not one directory. A red-first regression test proves this directly:
  a planted `import socket` in a scratch copy's `gui/api.py` (not
  `server.py`) is caught by the scan, and the same planted import in
  `gui/server.py` itself is not, so the boundary the allowlist draws is
  exercised in both directions rather than asserted in prose alone.
- `docs/KNOWN-LIMITS.md` (this lane) records the boundary change honestly,
  including which other shipped documents still state the pre-amendment
  wording verbatim and are out of scope for this lane.
- No GUI code is written here. Building `src/brothersbe/gui/server.py` is a
  separate, future lane, and it inherits this ADR's boundary rather than
  reopening it: bind `127.0.0.1` only, never `0.0.0.0`, no outbound call of
  its own, no analytics, no account. That lane still owes its own threat
  model for what a loopback listener specifically exposes (unauthenticated
  local processes, browser-based CSRF against a listening port, and so on);
  this ADR authorizes the boundary, it does not clear that work.

## Consequences

LP-0301 is unblocked to build the loopback workspace in a future lane without
re-arguing whether the security posture permits it; that argument is settled
here, once, with the reasoning attached.

The auditable surface gains exactly one reserved exception. Until
`src/brothersbe/gui/server.py` exists, the cost is purely documentary: one
allowlist entry and some amended prose that a reader can plainly see refers
to something not yet built. Once it exists, the cost becomes real: one file a
human must read with more scrutiny than the rest, because the AST scan will
no longer flag what it imports. That file becomes the single place the
zero-network property does not hold, named, exact-path, singular, by design.

This lane does not update `docs/THREAT_MODEL.md`, `README.md`, or
`design/final-release-program/01-purpose.md`, all three of which still state
the pre-amendment "no server" wording verbatim outside this lane's owned
files. That is a known, named drift, not an oversight silently left for a
reader to discover: `docs/KNOWN-LIMITS.md` records it so it stays visible
until a follow-up lane reconciles the wording.

## What would flip this

If a future ask needs the workspace reachable from a second device, or
needs its state to outlive the local machine being off, this ADR's
authorization does not extend there. That is the cloud-or-remote-UI option
rejected above, and moving to it is a new founder decision, on the same
precedent this ADR itself follows: a ratified boundary is reversed only by
Khalil awake, never inferred from a document or a lane that wants the
convenience.

If `src/brothersbe/gui/server.py` is built and later abandoned, the allowlist
entry and the amended prose in `SECURITY.md` should be removed the same day
the file is, per this ADR's own reversibility criterion, so the scan does not
carry a live exception naming dead code.
