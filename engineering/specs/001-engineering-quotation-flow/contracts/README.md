# Contracts: Engineering-to-Quotation-to-Manufacturing Flow

**Feature**: 001-engineering-quotation-flow
**Date**: 2026-08-20

This feature has no external HTTP/RPC API — it is an Odoo addon whose
"contracts" are the in-ORM model interfaces (methods other code/views
may call) and the report/document contracts (what users see). The
following files document each contract:

- `engineering-scope.md` — BoM/BoQ model contract (US1).
- `quotation-approval.md` — Quotation → MO orchestration contract
  (US2, US3).
- `project-timeline.md` — Project-module link contract (US4).

Contracts are specified at the method-signature + behavior level so
that downstream modules can extend (OCP) and tests can verify
behavior.