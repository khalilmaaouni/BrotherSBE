---
slug: web-and-apps
title: Scenario, websites and applications
part: "5"
verified-against: 1.0.0-rc.28
---

# Scenario, websites and applications

The honest headline first: **if your work is purely presentational, this is not
the tool you are missing.** A marketing site, a component library, a design
system. Everything comes back T0, nothing is owed, and you should reach for a
design and accessibility toolchain instead.

It becomes the right tool the moment the application has something behind it,
which is most applications after week three.

## Where a web or app project actually crosses the line

- The app calls an API you also own, and you are about to change its shape.
- There is a database, and you are about to migrate it.
- The app reports a number to a user: a balance, a total, a count, a streak.
- Authentication, payments, personal data, file upload, or a partner API.
- The client caches, and cache invalidation is now a correctness question.

Each of those turns a presentational change into a contract or data change,
and the intake will say so without being asked.

## The number-on-a-screen case

This one surprises teams. A figure rendered in an interface is a figure that
reaches a decision, and it inherits the numbers gate.

> The account screen shows "Available balance". It is computed client-side by
> subtracting pending holds from the ledger balance returned by the API.

That is a second derivation living in the client, which is exactly the
condition the numbers gate exists for, and almost nobody writes it down. Either
the server owns the number and the client renders it, or both derivations are
declared and reconciled. Choosing silently is how a user sees a balance that
no system agrees with.

## Day one

```bash
mkdir -p design/checkout-redesign
python3 tools/sbe_intake.py design/checkout-redesign
```

A visual redesign of a checkout: does it change a contract, does it touch
money? A pure layout change is T0 and owes nothing. The moment it changes the
order in which payment intent is created, it is T3.

Same feature, two very different answers, decided by five questions rather than
by how the work feels.

## What the design artifacts look like here

`01-purpose.md` carries the success criteria in observable terms, which for
interface work means a user-visible condition rather than a rendering claim.
"A user can complete checkout without leaving the page, and a failed payment
leaves no orphaned order" is checkable. "The checkout feels faster" is not.

`02-process.md` carries the states. An interface is a state machine and the
exception path is where it is worst: what the user sees when the network drops
between payment authorization and confirmation.

`05-data-model.md` matters as soon as the client holds state. Declare who owns
each entity, because a client cache that believes it owns `cart` while the
server also does is the same two-owners bug as any warehouse, with worse
symptoms.

## What is NOT covered, plainly

BrotherSBE has no opinion on visual design, typography, spacing, motion or
component structure. It ships no accessibility checker, no visual regression
suite, no Lighthouse integration and no browser driver. If a page is
inaccessible or ugly, nothing here notices.

Use a dedicated design and accessibility toolchain for that layer, and use
this one for the contracts and data underneath. They do not overlap, and
neither replaces the other.

## Verification that actually applies

The `ran` gate does. An end-to-end test that "passed" but exited in zero time
did not run, and the receipt records the duration for that reason.

`qa-reviewer` maps requirements and acceptance criteria to executable tests and
finds missing negative and non-functional coverage. On interface work the
missing coverage is almost always the failure path: the network error, the
declined card, the expired session.

## Week one and month one

**Week one.** Adopt on the repository that holds the API or the data layer, not
on the presentational package. Let the intake tell you which changes are
actually T1 and above.

**Month one.** Every number the interface displays has a declared owner. Every
contract change between client and server carries an ADR. The visual work
carries on exactly as it did, in its own toolchain, untouched.
