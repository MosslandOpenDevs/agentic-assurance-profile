# Diagnostic catalog acceptance decisions

> **INTERNAL REPOSITORY DECISION DATA — NOT A PUBLIC OR RUNTIME CONTRACT**

This directory is reserved for a future, append-only acceptance decision about
the diagnostic catalog candidate under [`../`](../). **No such decision has
been made.** The candidate's `acceptance_binding: null`,
`implementation_parity_authorized: false`, and `runtime_ready: false` values
stand; nothing here grants acceptance, parity, or runtime use.

## Status (v0.5 recovery mode)

The earlier `verifier-first` acceptance contract — a large
`scripts/verify_diagnostic_catalog_acceptance.py`, its test, and the detailed
record-shape and binding spec that previously filled this file — was
**removed**. It policed an acceptance record that does not exist, built ahead
of the decision that would give it meaning; that inverted the order and is the
kind of scaffolding v0.5 is deliberately shedding.

A real diagnostic-catalog acceptance, when it is actually scheduled, will be
**record-first with a named human owner**: the decision and its process facts
are recorded first, by an accountable maintainer, and any verifier is written
afterward and only if it earns its keep. The prior contract and verifier remain
in Git history if that work is ever revived.
