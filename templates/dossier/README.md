# Dossier templates

Copy these into `design/<project>/` at the start of an engagement. The tier from
`sbe_intake.py` decides which are required. `sbe_design.py` checks completeness:
run it advisory while you work, and in CI with `--strict` to block a merge.

Order: purpose, process, architecture decision, technology map, data model,
diagrams, verification plan. Each is approved before the next begins.
