# BrotherSBE regression evals

Each eval is a real failure class as a fixture, a planted defect, and an
assertion that the matching hard gate catches it. Run them:

```
python3 evals/run_evals.py
```

A release is blocked if any eval regresses (the script exits nonzero). This is
the mechanism behind the claim that the gates are proven, not asserted: they are
tested against the exact defect classes the operating record produced. Every
fixture is generalized and carries no private data.
