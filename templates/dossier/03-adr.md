# 03. Architecture decision record

<!-- SBE-TEMPLATE-UNFILLED 03-adr: this section is still the shipped example.
     Replace it with your own design, then delete this comment. While it is
     here, `sbe_design.py placeholder` FAILs and names this file. -->

## Context
What forced this decision, in three sentences or fewer.
Example: order volume is growing past what one database transaction per
checkout can absorb reliably, and the warehouse needs new orders within
minutes, not the next business day. Something has to change about how an
order reaches the warehouse.

## Criteria
The named criteria that decide it, with the value observed on this estate.
Example: deploying teams = 2 (checkout and warehouse), consistency = eventual
is acceptable, ops maturity = low (no dedicated on call for messaging
infrastructure today), failure isolation = high (a warehouse outage must
never block a sale at checkout).

## Options considered

### Rejected: Synchronous API call from checkout to warehouse
Ties checkout latency to the warehouse system's availability: a warehouse
outage would fail every order at the point of sale. Failure isolation is
the criterion that kills this option.

### Rejected: Nightly batch file drop
Meets the low ops maturity criterion but fails the freshness requirement:
the warehouse needs new orders within minutes, and a nightly batch means
today's orders stay invisible until tomorrow.

## Decision
Checkout publishes each confirmed order to a queue, and the warehouse
system consumes from that queue on its own schedule.

## Consequences
This costs one more moving part to build and monitor. It makes checkout
resilient to warehouse outages, since a stalled consumer just backs up the
queue instead of failing the sale. It makes exactly once delivery hard: the
warehouse must de duplicate by order id.

## What would flip this
The observable condition that means revisit. A decision record without
this is a tombstone.
Example: if ops maturity rises enough to run a message broker's on call
rotation, and the warehouse comes to need sub second freshness, revisit
toward a change data capture stream instead of a polled queue.
