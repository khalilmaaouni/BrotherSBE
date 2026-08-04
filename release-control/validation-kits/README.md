# Human Validation Kits, plain-language guide

Khalil, this page explains what is in this folder, why it exists, and what it changes about
when BrotherSBE 1.0.0 can ship. No engineering background needed to read it.

## What this folder is

The release readiness review for BrotherSBE 1.0 found one thing no amount of internal testing
can prove on its own: whether the product actually works for a real person who has never seen
it before, and for real engineers checking real mistakes, in real projects nobody on the team
wrote. The review calls this dimension D13, "independent and external validation", and it
currently scores 1.0 out of 5 against a required 5.0 out of 5. It is the lowest score of any
dimension in the whole review, and the review marks it a release blocker.

This folder contains everything needed to run that missing validation: a step-by-step script
for five first-time users, a step-by-step script for five experienced engineers reviewing
planted mistakes, a list of six different kinds of projects to test against, a form to record
results in a way a computer can check, and a live note-taking template for whoever runs each
session.

## What it is not

This folder is preparation, not execution. Nobody has run a study yet. No participant has been
recruited yet. Every result field in these files is empty on purpose, waiting to be filled in
once real sessions happen.

## Why it can't happen tonight

Running these studies means finding real people (five who have never touched BrotherSBE, and
five experienced engineers) and setting aside real time with each of them. That is scheduling
and recruiting work, not something a coding session can do at midnight. These kits exist so
that whenever you do have people lined up, whoever runs the session has a complete script to
follow and never has to guess what to do or invent a question on the spot.

## What is founder-gated

Three things need you specifically, not an engineer or an automated tool:

1. **Recruiting the participants.** Ten real people, none of whom have worked on BrotherSBE.
2. **Deciding when to run it.** These kits are ready whenever you are; nothing else blocks
   starting.
3. **The final go or no-go.** Even after every session runs and every number is filled in, a
   human still has to look at the results and decide the release moves forward. That decision
   is never a script's to make.

## What stays true until these studies run

Two plain facts, and they will not change no matter how good the rest of the product looks:

- The "independent and external validation" score (D13) stays stuck at its current low mark.
  A strong score everywhere else does not average this away; the review is explicit that one
  failed requirement holds the whole release back, no matter how well everything else scores.
- **BrotherSBE cannot be tagged as version 1.0.0, the finished, stable release, until these
  studies run and pass.** This is not a soft guideline. It is one of the hard stop conditions
  the release review sets for calling the product done.

## What is in each file

- `beginner-study.md`: the exact script for five sessions with people who have never used
  BrotherSBE, what to watch for, and the bar they need to clear.
- `engineer-study.md`: the exact script for five sessions with experienced engineers, using
  projects with mistakes planted on purpose, and the bar they need to clear.
- `estate-matrix.md`: the six different kinds of projects (a small Python service, a
  Node/TypeScript service, a data project, a database migration project, a mixed project with
  several parts, and one deliberately booby-trapped project) the product needs to prove itself
  against.
- `metrics.json`: a form built for a computer to read, so once the studies run, someone can
  check the pass/fail bar automatically instead of eyeballing it.
- `session-log-template.md`: the notes template whoever runs a session fills in live, with a
  timestamp on every line, so the record is trustworthy on its own.

## What to do with this folder next

Nothing right now. When you are ready to schedule the studies, hand `beginner-study.md` and
`engineer-study.md` to whoever will run the sessions, point them at this README first, and let
them follow the scripts as written. Come back to this folder once results are in; that is the
moment the D13 score and the 1.0.0 decision can move.
