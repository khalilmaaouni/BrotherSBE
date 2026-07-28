# MANIFEST-extraction.md

Mechanical extraction of SKILL.md's six phases and sixteen of its nineteen laws into
`references/*.md`, verbatim. What stayed in SKILL.md, and why, is recorded below the
table rather than left to be inferred from what is missing.

The method is the sibling repository's: slice exact line ranges out of the source file,
write them unaltered under a title, a `LOAD WHEN:` line and a pointer back, then compare
the concatenation of the extracted bodies against the concatenation of the source ranges,
character for character. Nothing was hand-copied and nothing was reworded, so "verbatim"
is a measurement here rather than an intention.

## Reference files

Line ranges are 1-indexed and inclusive, against SKILL.md as it stood before the split
(git object `cb8e31f:SKILL.md`, 61227 bytes, 319 lines). "Lines" and "approx tokens"
count only the verbatim body: the added title, `LOAD WHEN` and pointer lines are
excluded, and tokens are the body's characters divided by 4, the same arithmetic the
sibling's manifest uses.

| Target path | Source sections | Source lines | Lines (body) | Approx tokens | LOAD WHEN |
|---|---|---|---|---|---|
| `references/phases-purpose-and-process.md` | Phases 1, 2 | 49-68 | 20 | 263 | LOAD WHEN: a design is starting and the purpose brief or the process map is being written or reviewed. |
| `references/phases-architecture-and-data.md` | Phases 3, 4 | 69-108 | 40 | 647 | LOAD WHEN: the shape of the system is being decided, a technology map is being written, or a data model is being taken from conceptual to logical to physical. |
| `references/phase-expression.md` | Phase 5 | 109-136 | 28 | 478 | LOAD WHEN: a diagram is being drawn or changed, or the dossier's documentation is being written. |
| `references/phase-verification.md` | Phase 6 | 137-148 | 12 | 216 | LOAD WHEN: the gates are about to run, or a verification plan is being written. |
| `references/laws-tier-and-artifacts.md` | L1, L2 | 167-180 | 14 | 1914 | LOAD WHEN: a task is being tiered from its intake answers, or the dossier is being checked for the artifacts its tier requires. |
| `references/laws-design-artifacts.md` | L3, L4, L5 | 181-201 | 21 | 3340 | LOAD WHEN: an architecture decision record, a data model, or a diagram is being written or reviewed. |
| `references/laws-hard-gates.md` | L7, L8, L9, L10 | 209-236 | 28 | 2174 | LOAD WHEN: a figure that could reach a decision is produced, a schema migration is part of the change, the change touches money or a partner path, or a SQL, pipeline or reconciliation change is about to be called done. |
| `references/laws-decision-tables.md` | L12 | 244-250 | 7 | 587 | LOAD WHEN: a decision table is consulted, or a recommendation from one is about to be reported. |
| `references/laws-parallel-writers.md` | L13 | 251-257 | 7 | 713 | LOAD WHEN: any writer (agent, subagent, or parallel session) is about to be dispatched against a worktree, or a fence is being written or closed. |
| `references/laws-overrides-and-waivers.md` | L15, L16 | 265-278 | 14 | 1240 | LOAD WHEN: the computed tier is about to be overridden, or an instruction, a deadline or a convenience would skip a hard gate. |
| `references/laws-closing-and-review.md` | L17, L18, L19 | 279-299 | 21 | 800 | LOAD WHEN: a session is ending, a milestone is landing, or work is about to be reviewed, scored or judged. |

Every `LOAD WHEN:` line above is word for word the "Load when this is true" cell of that
file's row in SKILL.md's routing table, checked by string equality across all eleven
files, so the table and the files cannot drift into disagreeing about when a file is
owed.

## What stayed in SKILL.md, and the rule that decided it

| Kept | Source lines | Chars | Why it is always on |
|---|---|---|---|
| Frontmatter, the identity and register, the spine | 1-48 | 3307 | The register (engineer peer to peer) and the spine's six-step invocation sequence are the triage that routes everything else. Nothing can be routed by a file that has not been read. |
| The law form, and severity | 149-166 | 1075 | WHEN, INPUTS, RULE, OUTPUT, ENFORCED BY is the grammar every reference file is written in, and the severity paragraph is how any verdict line is read. |
| L6, the four forcing conditions | 202-208 | 1153 | Triggered by a condition, not an act: an ambiguity, a contradiction, a hard-gate collision or a disproven assumption, at any phase and any tier. |
| L11, silent-failure lints | 237-243 | 3409 | Triggered by "source is written or changed", which is most of the job. |
| L14, blast radius | 258-264 | 1474 | Triggered by a command being about to be applied rather than drafted, which is the moment it is too late to go and read about it. |
| What is not law | 300-320 | 1310 | The amendment rule and the byte ceiling govern every session that proposes a change to this file. |

The rule, stated once so the next split does not have to guess: a law stays in the
always-on core when an agent could fail to LOAD it because it never noticed the trigger.
Every other law and every phase announces itself (a tier is being computed, an ADR is
being written, a figure is being produced, a writer is being dispatched, a session is
closing), and the routing table catches those. Three laws pass that test, and they are
the three the core keeps whole rather than summarized. That is a deliberate divergence
from the sibling, whose core carries a summarized floor instead; PARITY.md records it.

Two of those retentions are also load-bearing for tooling outside this file's fence, and
would have had to stay even if the rule had said otherwise. `evals/run_evals.py`
(the case `the-lint-numbers-this-repository-prints-are-the-numbers-it-computes`) opens
SKILL.md and recomputes the waived-hit and clean-file counts that L11's text states about
this repository's own lint run, and `tools/test_sbe.py` reads SKILL.md's own byte ceiling
out of the What-is-not-law section. Both would have gone quiet, or gone red, over a
SKILL.md that no longer held those sentences.

## Verification: nothing lost, nothing reworded

Method: for each reference file, split the body off at the pointer line and compare it
by string equality against the exact source line range, read from the pre-split git
object rather than from the working tree. Then sum.

```
SKILL.md before                         : 61227 chars
extracted verbatim into references/     : 49483 chars
retained verbatim in SKILL.md           : 11728 chars
newlines between the 17 source blocks   :    16 chars
sum                                     : 61227 chars
difference from the source              :     0 chars
```

The 16 characters are the newline that separated each of the 17 contiguous blocks from
the next in the source file; they are named rather than rounded away, because a
reconciliation that needs an unexplained remainder has not reconciled anything.

Per-file result of the string comparison: all eleven EXACT. Per-block result for the six
retained ranges: five present in the new SKILL.md character for character.

The sixth, What-is-not-law, carries the one deliberate edit in this change and is
recorded here rather than hidden inside a "verbatim" claim: the byte ceiling that section
names for SKILL.md drops from 68,000 to 18,000, and the sentence now says the ceiling
governs the part loaded on every invocation. A 68,000-byte ceiling over a 14,848-byte
core would let the file grow back to four and a half times its size with nothing
complaining, which is the ceiling's own argument used against it. `tools/test_sbe.py`
reads the number out of the sentence, so the claim and the assert still cannot disagree.

## Cross-references noted

- Law numbers are unchanged, and SKILL.md's routing table carries a column naming which
  file holds which law, so an `L9` written in `docs/`, in `DIGEST.md` or in
  `LAWS-REFERENCE.md` still resolves.
- Pointers that named SKILL.md together with a law number, in files outside this fence
  (`docs/KNOWN-LIMITS.md`, `docs/HOW-IT-WORKS.md`, `docs/DESIGN.md`, the guides) now name
  a file that holds the law's number in a table rather than the law's text. Nothing
  breaks mechanically; the pointers are one hop longer until they are updated.
- `DIGEST.md` and `LAWS-REFERENCE.md` were updated in the same change: the digest's
  header and its post-compaction line now say where the full law lives, and
  LAWS-REFERENCE.md's opening paragraph names SKILL.md plus its references as the law.

## What this did not do

- No reference file is loaded by any tool. The routing table is read by an agent, and
  nothing verifies that an agent loaded the file its situation called for. The split
  reduces what is always in context; it does not enforce what is read.
- Nothing recomputes this manifest. It is a record of one migration, checked at the time
  by string equality against the pre-split object, not a gate that runs again.
