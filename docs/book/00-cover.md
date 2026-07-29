# BrotherSBE for Dummies

This book is for backend, data, and infrastructure engineers, and for the
business analysts and project managers who work beside them. Part I needs no
terminal at all.

## Who this book assumes you are

You do not need to know BrotherSBE already. You do need to care whether a
claim in a change is actually backed by evidence, because that is the one
thing this whole product exists to check.

## What this book will not claim

This book will not say BrotherSBE is proven at scale. Everything here is
INTERNAL-EVAL: it has been run and checked inside this project, not battle
tested across many teams yet, and every chapter says so again wherever it
matters rather than once at the front and never again.

This book will not paste a command's output from memory. Every terminal
block in these pages is real output, produced by actually running the
command, and the book's own build check re-executes each one and rejects the
page if the tool's live output ever drifts from what is printed here.

This book will not describe a feature that does not exist in the shipped
command line yet. Any capability still ahead of the current release is
marked "ships in a later loop" beside the sentence that names it, so a
reader can tell today's tool from tomorrow's plan.

This book will not turn an absence of evidence into a quiet pass. Where a
number, a status, or a record is missing, the book shows NO-DATA and names
what would fill it, the same rule the product itself applies to every claim
it makes.

## How to read it

Part I is for BAs and PMs: what the product guarantees, and how to read its
status without opening a terminal. Part II is the engineer core: one worked
example, a small nightly pipeline and its API, followed end to end through
an install, a loop, a gate, and the team coordinating around it. Part III is
a cookbook: one page per common task, with the exact commands and what the
gates will refuse.
