# Phase 0 Research: Engineering-to-Quotation-to-Manufacturing Flow

**Feature**: 001-engineering-quotation-flow
**Date**: 2026-08-20
**Status**: Complete — all Technical Context unknowns resolved.

## Research Tasks

### R1. Target Odoo version and runtime

- **Decision**: Odoo 18 (community/enterprise core equivalent for the
  models used) on Python 3.11, PostgreSQL.
- **Rationale**: `odoo/release.py` reports `version_info = (18, 0, 0,
  FINAL, 0, '')`; Python 3.11 is the active interpreter. Odoo 18 is the
  current stable series in this checkout.
- **Alternatives considered**: None — the host checkout determines the
  target. Pinning to 18 keeps the manifest `version` `18.0.x.y.z` per
  Odoo convention (constitution Principle IV).

### R2. Customer-facing quotation vehicle

- **Decision**: Extend `sale.order` via `_inherit` to create the
  engineering quotation. The customer-facing document is a customized
  `sale.order` report showing only the final project estimate price.
- **Rationale**: `sale.order` is Odoo's native quotation object with
  send/print/mail-template plumbing, partner linkage, and approval
  states (`draft` → `sent` → `sale`). Extending it (OCP) avoids
  rebuilding quotation lifecycle from scratch and keeps `sale`'s
  audit trail.
- **Alternatives considered**:
  - Custom `engineering.quotation` model duplicating send/approve
    states. Rejected — violates YAGNI (constitution V) and re-implements
    `sale`'s reviewed, secure flow.
  - `purchase.order` (wrong direction — vendor, not customer).
- **Caveat**: `sale.order` lines (`sale.order.line`) carry per-product
  detail. To meet SC-003 (100% no line leakage), the customer-facing
  report template MUST render only the single final-price line/summary,
  and the engineering BoM/BoQ detail is stored on the linked
  `engineering.project` (not on `sale.order.line` exposed to the
  customer report).

### R3. Internal cost source

- **Decision**: Standard Cost (`product.product.standard_price` /
  `product.template.standard_price`) for both BoM materials and BoQ
  services.
- **Rationale**: Resolved in clarify Q2. Standard Cost is the
  company-managed stable baseline consistent with MRP consumption
  valuation; matches constitution's "no surprises" pricing intent and
  FR-015 (warn, never silent zero).
- **Alternatives considered**: Average cost (mixed old/new stock),
  last vendor price (volatile), per-line selectable (over-engineered
  for v1). All rejected via Q2.

### R4. Markup computation

- **Decision**: Single markup percentage field on the engineering
  quotation; final price = (Σ BoM standard cost + Σ BoQ standard cost)
  × (1 + markup).
- **Rationale**: Resolved in clarify Q3. Single markup keeps the
  customer-facing quotation to one number (SC-003) and minimizes
  configuration (YAGNI). Per-list/per-line markup explicitly out of v1.
- **Alternatives considered**: Per-list markup, per-line markup — both
  rejected via Q3 as v1 out-of-scope.

### R5. Manufacturing Order generation

- **Decision**: The engineering BoM/BoQ are a staging scope. On
  approval, the module creates a real `mrp.bom` (or links an existing
  template-derived one) whose `mrp.bom.line` components are the BoM
  materials, then creates and confirms a `mrp.production` from it. BoQ
  services are attached to the MO as non-stock work lines via a custom
  `engineering.mo.service.line` model (or `mrp.production` One2many
  extension) so they are tracked as work to be performed, not as
  stockable consumption.
- **Rationale**: Resolved in clarify Q4. `mrp.production` requires a
  real `mrp.bom` to drive material consumption and the standard
  `action_confirm`/`_action_compute_consumption` flow. Putting
  services into `mrp.bom.line` is wrong because services are not
  stockable components and would be consumed as materials. Carrying
  them as a separate non-stock work-line list preserves SRP and OCP
  (we extend `mrp.production` with a One2many, we do not fork MRP
  internals).
- **Alternatives considered**:
  - Treat engineering BoM as the `mrp.bom` directly (services as
    `mrp.bom.line` with a flag). Rejected — services would be consumed
    as stockable components, contradicting FR-011.
  - Two separate `mrp.bom`s (materials, services-as-phantom). Rejected
    — phantom components still drive stock semantics; services are
    work, not components.
  - No `mrp.bom`; MO created with manually-added raw components.
    Rejected — bypasses MRP's BoM-driven consumption and RFQ
    triggering, contradicting FR-009/FR-010.
- **Implementation note**: To trigger RFQs for shortages, the standard
  `mrp.production` `action_confirm` → run procurement / reordering
  rules path is used. The module does NOT manually create
  `purchase.order` records; it relies on MRP→stock→purchase
  procurement. Tests verify RFQs appear for exact shortage quantities.

### R6. Purchase RFQ triggering

- **Decision**: Rely on Odoo's standard procurement/reordering-rule
  path: MO confirm → stock moves → procurement → `purchase.order`
  (RFQ) for shortage quantities.
- **Rationale**: Constitution Principle IV (Odoo conventions) and II
  (OCP — use, don't fork). Manually creating RFQs would duplicate
  reviewed procurement logic and break under reordering-rule config.
- **Alternatives considered**: Manual RFQ creation in the approval
  handler. Rejected — violates OCP and couples engineering code to
  purchase internals.
- **Test strategy**: Test setups configure a reordering rule or rely on
  MRP's default `make_to_order` route for the shortage product; assert
  exactly one `purchase.order` (draft RFQ) per shortage product with
  the shortage quantity. This is integration-tested against a fresh
  test DB with `mrp` + `purchase` + `stock` installed.

### R7. Engineering scope state and revision

- **Decision**: `engineering.project` carries a `state` field
  (`draft` → `sent_to_commercial` → `approved` → `manufacturing`).
  BoM/BoQ records inherit edit-lock semantics from the project state:
  editable in `draft`; read-only once `sent_to_commercial` unless a
  commercial user triggers the "request revision" wizard, which
  creates a new draft revision (`revision_number` increments, previous
  revision retained with `is_current_revision = False`).
- **Rationale**: Resolved in clarify Q5. Lock-on-send enforces FR-014
  (no silent edits). Revision wizard preserves audit trail (previous
  version retained) and keeps a single current revision (avoids
  concurrent-draft complexity, out of v1 scope).
- **Alternatives considered**:
  - Permanent lock; any change requires a brand-new project/quotation.
    Rejected — discards audit linkage to the original scope.
  - Soft warning, no lock. Rejected — contradicts FR-014.
- **State machine**:
  ```text
  draft --send_to_commercial--> sent_to_commercial
  sent_to_commercial --request_revision--> draft (new revision)
  sent_to_commercial --customer_approve--> approved
  approved --generate_mo--> manufacturing
  sent_to_commercial --customer_reject--> draft (same revision, re-quote)
  ```

### R8. Project-module link for construction timeline

- **Decision**: Extend `project.project` via `_inherit` with a
  One2many/Many2one link to `engineering.project`. On MO generation,
  the module creates (or links) a `project.project` and seeds initial
  tasks from the approved BoQ service lines (each service → one task;
  material lines do not seed tasks — they are procurement-tracked).
  Milestones and dependencies are managed by the standard Project
  module UI.
- **Rationale**: Constitution Principle II (OCP — extend
  `project.project`, don't fork) and IV (use Odoo's project
  scheduling). Seeding tasks from BoQ services directly ties the
  timeline to the approved service scope (SC-006).
- **Alternatives considered**:
  - Build a custom scheduling engine. Rejected — out of v1 scope
    (Assumptions).
  - Seed tasks from both BoM and BoQ. Rejected — materials are
    procurement-tracked via MRP/stock, not project tasks; mixing
    would duplicate tracking.
- **Test strategy**: After approval + MO generation, assert a
  `project.project` exists linked to the engineering project, and one
  `project.task` exists per BoQ service line, reachable from the
  engineering project form (SC-006).

### R9. Security model

- **Decision**: Two user groups, declared in `security/security.xml`:
  - `engineering.group_engineering_user` — create/edit BoM and BoQ in
    `draft` state; cannot price or send quotation.
  - `engineering.group_commercial_user` — view scope, compute cost,
    apply markup, send/approve quotation, request revision.
  Access rights in `ir.model.access.csv` grant CRUD per group per
  model. Record rules (if multi-engineer isolation is needed) deferred
  to a follow-up — v1 uses group-level access only.
- **Rationale**: Constitution Principle IV (security compliance, least
  privilege). The two-role split matches the spec's actors
  (engineering team vs commercial department) and enforces FR-014's
  "only commercial may request revision".
- **Alternatives considered**: Single `engineering.group_user` with
  full access. Rejected — would let engineering silently edit after
  send, violating FR-014.

### R10. Test-First enforcement

- **Decision**: Per constitution Principle III, every model method with
  non-trivial logic gets a `TransactionCase` test written and shown to
  fail BEFORE implementation. Tests live in `tests/` with
  `tests/__init__.py` importing each `TestX`. Demo data
  (`demo/demo.xml`) is for demonstration only and MUST NOT be required
  by any test (tests create their own products, partners, scopes).
- **Rationale**: Constitution Principle III (non-negotiable).
- **Test list** (maps to user stories):
  - `test_engineering_bom.py` — US1: draft BoM create/edit/lock.
  - `test_engineering_boq.py` — US1: draft BoQ create/edit/lock;
    services distinguishable from materials.
  - `test_quotation_markup.py` — US2: internal cost from Standard Cost,
    markup formula, customer-facing report shows only final price.
  - `test_approval_generates_mo.py` — US3: approval → real `mrp.bom` +
    `mrp.production`, BoQ services as non-stock work lines.
  - `test_rfq_on_shortage.py` — US3: shortage → exactly one RFQ per
    shortage product at shortage quantity.
  - `test_project_timeline.py` — US4: linked `project.project` + tasks
    seeded from BoQ services.

### R11. FR-016 dependency-missing enforcement

- **Decision**: Odoo hard `depends` in `__manifest__.py`
  (`['base','product','uom','sale','stock','mrp','purchase','project']`)
  is the clear-message mechanism. Odoo blocks install/uninstall with a
  clear message at install time, so the unsupported configuration
  cannot exist. No runtime guard in the approval handler.
- **Rationale**: Resolved in clarify session 2 Q1. Odoo's hard
  `depends` is the idiomatic, constitution-Principle-IV-compliant
  mechanism. A runtime guard would be unreachable dead code (the
  module cannot be installed without its dependencies).
- **Alternatives considered**:
  - Runtime graceful degradation (UserError on approve if MRP/Purchase
    missing). Rejected — impossible with hard depends; unreachable.
  - Soft/optional deps with runtime checks. Rejected — loses Odoo's
    install-time safety and contradicts constitution Principle IV.

### R12. Rejected-quotation state

- **Decision**: `engineering.project.state` includes an explicit
  `rejected` value. The state machine is
  `sent_to_commercial → rejected → draft`: on rejection the project
  enters `rejected` (auditable/queryable), then a separate action
  returns it to `draft` for re-quotation on the same revision.
- **Rationale**: Resolved in clarify session 2 Q2. An explicit
  `rejected` state makes rejection a queryable event for audit and
  reporting, at minimal cost. Returning straight to `draft` loses the
  rejection signal.
- **Alternatives considered**:
  - Drop `rejected`; reject returns directly to `draft`. Rejected —
    loses the auditable rejection event.
  - `rejected` as terminal (no re-quote). Rejected — contradicts the
    re-quote edge case.
- **State machine update** (replaces R7's machine):
  ```text
  draft --send_to_commercial--> sent_to_commercial
  sent_to_commercial --request_revision--> draft (new revision)
  sent_to_commercial --customer_approve--> approved
  approved --generate_mo--> manufacturing
  sent_to_commercial --customer_reject--> rejected
  rejected --re_quote--> draft (same revision)
  ```

### R13. Sale order behavior across revisions

- **Decision**: On commercial "request revision", the previous
  revision's `sale.order` (quotation) is cancelled (retained for
  audit). The new revision starts with `sale_order_id = False` and
  receives a fresh quotation on its next `action_send_to_commercial()`.
- **Rationale**: Resolved in clarify session 2 Q3. Keeps exactly one
  active quotation per revision, avoids two live quotations for the
  same scope, and matches the "previous retained for audit" intent.
- **Alternatives considered**:
  - New revision inherits/copies the old `sale.order` as a draft.
    Rejected — couples revisions to a stale quotation; loses the clean
    "fresh quotation per send" flow.
  - Both quotations stay open; commercial picks which to send.
    Rejected — ambiguity, two live quotations for one scope.

### R14. Engineering quotation sale.order.line content

- **Decision**: The engineering quotation (`sale.order`) carries
  exactly one summary `sale.order.line` for a dedicated "Engineering
  Project" service product with `product_uom_qty = 1` and
  `price_unit = final_estimate_price`. No per-product BoM/BoQ detail
  on `sale.order.line`.
- **Rationale**: Resolved in clarify session 2 Q4. Satisfies
  `sale.order`'s structural requirement (at least one line to total),
  keeps exactly one line (trivial to verify zero leakage per SC-003),
  and the customer report renders only that line's total. Per-product
  detail never enters `sale.order.line`.
- **Alternatives considered**:
  - No `sale.order.line`; custom total field bypassing line totals.
    Rejected — fights `sale.order`'s structure; breaks standard `sale`
    reporting/totals.
  - One line per BoM+BoQ item hidden from the customer report by
    template. Rejected — leakage risk; SC-003 requires structural
    non-exposure, not template-only hiding.

### R15. MRP finished-good product for the generated mrp.bom

- **Decision**: A single shared generic "Engineering Project"
  finished-good product, created once as module data
  (`data/product_data.xml`) and reused by every generated `mrp.bom`.
  Per-project identity is carried on `engineering.project`, not on the
  MRP product.
- **Rationale**: Resolved in clarify session 2 Q5. Avoids creating a
  throwaway product per project (clutter), keeps the MO's finished good
  consistent and queryable, and matches YAGNI (constitution Principle
  V) — one product serves all projects. The same product doubles as
  the summary-line service product on `sale.order.line` (R14), so one
  `data/product_data.xml` record serves both purposes (finished good
  for MRP; summary line for `sale`).
- **Alternatives considered**:
  - Auto-create a finished-good product per engineering project.
    Rejected — product master clutter; one-off products with no
    reuse.
  - Per-project dummy product with no real identity. Rejected — same
    clutter problem; harder to query "all engineering MOs".

## Open Items

None. All Technical Context `NEEDS CLARIFICATION` items resolved by
the two clarify sessions (Q1–Q5 each) and the research above (R1–R15).