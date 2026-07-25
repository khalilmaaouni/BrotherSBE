# Dossier templates

Copy these into `design/<project>/` at the start of an engagement. The tier from
`sbe_intake.py` decides which are required. `sbe_design.py` checks completeness:
run it advisory while you work, and in CI with `--strict` to block a merge.

Order: purpose, process, architecture decision, technology map, data model,
diagrams, verification plan. Each is approved before the next begins.

## The unfilled marker

Every template carries one `SBE-TEMPLATE-UNFILLED` comment under its title. While
it is there, `sbe_design.py placeholder` FAILs and names the file. Delete it when
the section is your own design.

That is deliberate. The example content is a coherent order-fulfilment system, and
it passes the other four checks as written, so without the marker the fastest route
to a green `--strict` run was to copy seven files describing someone else's system
and change nothing. A copied, unedited dossier is not a design, and the gate now
says so instead of blessing it.

```
$ cp templates/dossier/*.md design/my-project/
$ python3 tools/sbe_design.py placeholder design/my-project
BROTHERSBE DESIGN CHECKS  (advisory unless --strict; NO-DATA is never a pass)
  placeholder FAIL     still the shipped template, unedited: 01-purpose.md, 02-process.md, 03-adr.md, 04-technology-map.md, 05-data-model.md, 06-diagrams.md, 07-verification.md; each carries its SBE-TEMPLATE-UNFILLED marker, which the template says to delete once the section is your own design
```
