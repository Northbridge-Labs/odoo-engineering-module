# Quickstart: Engineering-to-Quotation-to-Manufacturing Flow

**Feature**: 001-engineering-quotation-flow
**Date**: 2026-08-20
**Odoo version**: 18.0

This guide documents runnable validation scenarios that prove the
feature works end-to-end. It is a validation/run guide, not an
implementation reference — see `tasks.md` (Phase 2) for implementation
steps and `data-model.md` / `contracts/` for model and behavior
details.

## Prerequisites

- Odoo 18 instance with the following addons installed and available:
  `base`, `product`, `uom`, `sale`, `stock`, `mrp`, `purchase`,
  `project`.
- The `engineering` module installed from `custom_addons/engineering/`.
- A test database (NOT production) — these scenarios create and modify
  real records.
- Two test users (or use admin, which has all groups):
  - An **engineering user** in group
    `Engineering / Engineering User`.
  - A **commercial user** in group
    `Engineering / Commercial User`.
- Test products (or create them in scenario 1):
  - Material products (`type = consumable` or `storable`) with a
    `standard_price > 0`.
  - Service products (`type = service`) with a `standard_price > 0`.

## Install the module

```bash
odoo-bin -c <your_config> -d <test_db> -i engineering \
  --test-enable --stop-after-init
```

Expected: install completes with no WARNING+ log lines; all
`tests/*` cases pass.

## Scenario 1 — Engineering drafts BoM + BoQ (US1)

Goal: an engineering user creates a project, adds material lines to a
BoM and service lines to a BoQ, and persists the drafts.

1. Log in as the engineering user.
2. Open `Engineering > Projects > New`. Fill `name`, `partner_id`
   (customer), save.
3. In the project's `Bill of Materials` tab, add 2 material lines
   (product, qty, UoM). Save.
4. In the project's `Bill of Quantities` tab, add 1 service line
   (service product, qty, UoM). Save.
5. Confirm both lists are persisted and editable.

**Expected**: project state = `draft`; BoM and BoQ totals computed from
Standard Cost; lists editable.

**Independent test**: no commercial/MRP/Project actions triggered.

## Scenario 2 — Commercial builds and sends customer-facing quotation (US2)

Prerequisite: Scenario 1 complete and scope sent to commercial (use
`Send to Commercial` on the project; confirm state =
`sent_to_commercial` and BoM/BoQ become read-only for engineering).

1. Log in as the commercial user.
2. Open the engineering project. Verify you can see BoM + BoQ with
   internal costs.
3. Open the linked quotation (`sale.order`). Set `markup_percent`
   (e.g. 15).
4. Verify `final_estimate_price = internal_cost * 1.15`.
5. Print/preview the **customer-facing** quotation report.

**Expected**: report shows ONLY project name, customer, and
`final_estimate_price`. NO line breakdown, NO markup details, NO BoM/
BoQ rows (SC-003).

**Edge check**: set a line product's `standard_price = 0`, recompute
internal cost → a warning listing that product appears (FR-015).

## Scenario 3 — Customer approval generates MO + RFQs (US3)

Prerequisite: Scenario 2 quotation sent (`state = sent`).

1. As commercial user, click **Approve** on the quotation.
2. Verify:
   - Quotation `state = sale`.
   - Engineering project `state = manufacturing`.
   - A `mrp.production` exists, linked from the project, with:
     - `mrp.bom.line` components matching the BoM materials.
     - `engineering.mo.service.line` entries matching the BoQ services
       (one per service line, `state = to_do`).
3. **Stock-sufficient check** (setup: enough stock for all materials):
   verify NO `purchase.order` (RFQ) was created.
4. **Stock-shortage check** (setup: insufficient stock for one
   material, re-run): verify exactly one `purchase.order` (draft RFQ)
   per shortage product, with the shortage quantity (FR-010).

**Expected**: one MO per approved quotation (FR-009); RFQs only for
shortages at exact shortage quantities (SC-005); services tracked as
work to perform, not consumed as stock (FR-011).

## Scenario 4 — Project module timeline (US4)

Prerequisite: Scenario 3 complete.

1. Open the engineering project. Click the **Project** smart button.
2. Verify a `project.project` opens, linked back to the engineering
   project.
3. Verify one `project.task` exists per BoQ service line (from
   Scenario 1), with the service product as planned work.
4. Add milestones and dependencies between tasks; move a milestone
   date and verify dependent tasks reschedule per standard Project
   rules.

**Expected**: construction timeline reachable in one click from the
engineering project (SC-006); tasks seeded from BoQ services only.

## Scenario 5 — Revision flow (edge case, FR-014)

1. From Scenario 2's `sent_to_commercial` state (before approval), as
   engineering user attempt to edit a BoM line → expect `UserError`
   (scope locked).
2. As commercial user, run the **Request Revision** wizard.
3. Verify: a new revision is created (`revision_number` increments),
   previous revision retained (`is_current_revision = False`), the
   previous revision's `sale.order` is cancelled (retained for audit,
   R13), the new revision starts with `sale_order_id = False`, project
   `state = draft`, BoM/BoQ editable again.

**Expected**: no silent edits after send (SC-007); revision preserves
audit trail; old quotation cancelled, new revision gets a fresh
quotation on its next send.

## Scenario 6 — Rejection then re-quote (FR-008, R12)

1. From Scenario 2's `sent` quotation, as commercial user click
   **Reject**.
2. Verify: `engineering.project.state = rejected` (auditable
   intermediate); `sale.order` cancelled; no MO created.
3. Run **Re-quote** on the project → `state = draft` (same revision);
   edit the scope, re-send to commercial → a fresh `sale.order` is
   created (R13/R14).

**Expected**: rejection is a queryable event; re-quote reuses the same
revision and produces a new quotation.

## Scenario 7 — Dependency-missing guard (FR-016)

1. In a database WITHOUT `mrp` installed, attempt to install the
   `engineering` module.

**Expected**: Odoo blocks install with a clear missing-dependency
message naming `mrp` (and `purchase`, `project`). The module's hard
`depends` enforces this at install time (R11); no runtime guard is
needed or present.

## Run the automated test suite

```bash
odoo-bin -c <your_config> -d <test_db> -i engineering \
  --test-enable --stop-after-init --log-level=:INFO
```

Expected: all `test_engineering_*` / `test_quotation_*` /
`test_approval_*` / `test_rfq_*` / `test_project_*` cases pass.

## References

- Spec: `specs/001-engineering-quotation-flow/spec.md`
- Data model: `specs/001-engineering-quotation-flow/data-model.md`
- Contracts: `specs/001-engineering-quotation-flow/contracts/`
- Research: `specs/001-engineering-quotation-flow/research.md`