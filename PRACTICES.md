# Practices

This file is advice, and says so. Nothing here is enforced by a check. It is here
because it is true and useful, not because it can be verified. The laws, which do
carry enforcement points, are in [SKILL.md](SKILL.md).

The split is deliberate. A rule stated in a prompt is not a control; a control is a
check that runs. Mixing the two makes the law file feel stronger than it is, which is
the failure mode this split exists to prevent. So: laws name machinery, practices
admit they are judgment.

## Judgment that resists tabulation

- Naming: a name that needs a comment to explain it is the wrong name.
- Cohesion: code that changes together belongs together, whatever the layer diagram says.
- When to split a service: split along the axis where two teams disagree about deploy
  cadence, not along nouns. The decision table in `tables/architecture.json` scores the
  shape question; it does not tell you where the seam runs.
- Estimation: give a range and the assumption that would break it, never a single number.
- Reading before writing: the fastest way through unfamiliar code is to read its tests first.
- Deleting: code that is not called is not an asset. Removing it is cheaper than
  carrying it, and the test suite is the check on whether you were right.

## Working with people

- A stakeholder who cannot describe the failure mode has not finished describing the
  requirement.
- Write the summary for the person who was not in the room.
- When a decision is reversed, record why, not just what. The ADR template has a place
  for this ("What would flip this"); using it well is judgment, having it is law.
- Bad news travels first. A failed gate reported late costs more than the failure.
- Disagreement is cheap in review and expensive in production. Say the objection while
  the design is still a document.

## How a practice becomes a law

When someone builds a check for one of these, it stops being advice: it moves into
SKILL.md in the law form (WHEN, INPUTS, RULE, OUTPUT, ENFORCED BY) with the new check
named on the enforcement line, and it ships with a fixture in `evals/` proving the check
catches the defect it claims to catch. That promotion rides a reviewed pull request, the
same as any other law change. Until then it stays here, where it is honest.
