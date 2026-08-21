# Implementation Plan: Engineering-to-Quotation-to-Manufacturing Flow

**Branch**: `001-engineering-quotation-flow` | **Date**: 2026-08-20 | **Spec**: `specs/001-engineering-quotation-flow/spec.md`

**Input**: Feature specification from `specs/001-engineering-quotation-flow/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Engineering module for Odoo 18 that captures a customer engineering work
order as a draft Bill of Materials (materials) and a draft Bill of
Quantities (services), sends the combined scope to the commercial
department for a single-markup, customer-facing price quotation (final
price only), and on customer approval generates a real `mrp.bom` +
Manufacturing Order (materials consumed from stock; BoQ services as
non-stock MO work lines), triggering Purchase RFQs for stock
shortages. Each engineering project is linked to a Project-module
project for construction timeline management. Scope is locked on send;
commercial "request revision" unlocks a new draft revision.

## Technical Context

**Language/Version**: Python 3.11 + Odoo 18 ORM/XML framework.

**Primary Dependencies** (Odoo 18 addons, declared in `__manifest__.py`):
- `base` — always required.
- `product` — material/service products, UoM, Standard Cost.
- `uom` — units of measure for BoM/BoQ lines.
- `sale` — `sale.order` as the customer-facing quotation vehicle.
- `stock` — material availability and consumption.
- `mrp` — `mrp.bom` + `mrp.production` (Manufacturing Order).
- `purchase` — Purchase RFQ generation for shortages.
- `project` — construction timeline (tasks, milestones, dependencies).

**Storage**: PostgreSQL via the Odoo ORM. No raw SQL.

**Testing**: Odoo `TransactionCase` in `tests/`; run via
`odoo-bin -c <cfg> -i engineering --test-enable --stop-after-init`.

**Target Platform**: Odoo 18 server on Linux (Python 3.11), PostgreSQL.

**Project Type**: Odoo addon module (`custom_addons/engineering/`).

**Performance Goals**:
- Spec SC-001: engineering draft scope (20 lines) created in <5 min.
- Spec SC-002: commercial quotation (cost+markup, customer-facing) in <2 min.
- MO generation on approval is a single user action; target <2 s for a
  50-line scope (deterministic, ORM-bounded).

**Constraints**:
- No raw SQL; use Odoo ORM mechanisms only (constitution).
- No `sudo()` without an inline justification comment (constitution).
- Standard Cost is the internal-cost source for both BoM and BoQ (Q2).
- One MO per approved quotation; multi-MO splitting out of scope (v1).
- Customer-facing quotation shows only final price (no line leakage).
- `mrp.bom` holds materials only; BoQ services are MO non-stock work
  lines, not `mrp.bom.line` components (Q4).
- FR-016 is enforced via Odoo hard `depends` at install time (clarify
  session 2 Q1); no runtime guard.
- On rejection, the project enters an explicit `rejected` state before
  returning to `draft` (clarify session 2 Q2).
- On revision, the old revision's `sale.order` is cancelled (audit);
  the new revision starts with `sale_order_id = False` and gets a
  fresh quotation on its next send (clarify session 2 Q3).
- The engineering quotation (`sale.order`) carries exactly one summary
  `sale.order.line` for a dedicated "Engineering Project" service
  product (qty=1, `price_unit = final_estimate_price`); no per-product
  BoM/BoQ detail on `sale.order.line` (clarify session 2 Q4).
- The generated `mrp.bom` references a single shared generic
  "Engineering Project" finished-good product (module data
  `data/product_data.xml`), reused across all projects (clarify
  session 2 Q5).

**Scale/Scope**: Single-company default; multi-company follows host
`res.company` rules. Engineering scope ~50 lines/order typical;
timeline ~20 tasks/project typical.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Single Responsibility per Artifact | ✅ Pass | Each new model owns one concept: `engineering.project` (order header), `engineering.bom` (material specs), `engineering.bom.line` (material line), `engineering.boq` (service scope), `engineering.boq.line` (service line), `engineering.quotation` (commercial doc). Quotation approval orchestration lives in a dedicated wizard/service method, not scattered across models. |
| II. Open/Closed via Odoo Inheritance | ✅ Pass | Extend `sale.order` via `_inherit` to add engineering-quotation fields/behavior (do not fork). Extend `project.project` via `_inherit` to link the engineering project. Generate `mrp.bom`/`mrp.production` via standard `create` + `action_confirm`, not by overriding MRP internals. Expose hook methods (`_compute_internal_cost`, `_generate_mo`) for downstream override. |
| III. Test-First (NON-NEGOTIABLE) | ✅ Pass | Every model method with logic has `TransactionCase` tests written first. `tests/__init__.py` imports all `TestX` classes. Demo data not required for tests (tests create own fixtures). Each US has contract+integration tests before implementation. |
| IV. Odoo Conventions & Security | ✅ Pass | Every new model declares `_name`, `_description`, `_order`, `_rec_name`/`_rec_name_search`. `security/ir.model.access.csv` has one row per model. User groups `engineering.group_engineering_user`, `engineering.group_commercial_user`. Views inherit (xpath) base `sale_order`/`project_project` forms. Manifest `version` = `18.0.1.0.0`. `_(...)` for all user-facing strings. FR-016 enforced by hard `depends` (Odoo convention), no runtime guard. |
| V. Simplicity, Observability & Versioning | ✅ Pass | YAGNI: no pre-built fields not required by a US. `_logger = logging.getLogger(__name__)` per file; INFO on business events (scope sent, quotation sent, rejected, approved, MO generated, RFQ triggered, revision requested), DEBUG for diagnostics. Manifest `version` `18.0.1.0.0` (MINOR for new feature in 18.0). No destructive migrations in v1. Shared finished-good product avoids per-project product clutter (Q5). |

**Gate verdict**: PASS — no violations. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/001-engineering-quotation-flow/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── engineering-scope.md      # BoM/BoQ model contract
│   ├── quotation-approval.md    # Quotation→MO orchestration contract
│   └── project-timeline.md      # Project-module link contract
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
custom_addons/engineering/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── engineering_project.py      # engineering.project
│   ├── engineering_bom.py          # engineering.bom + engineering.bom.line
│   ├── engineering_boq.py          # engineering.boq + engineering.boq.line
│   ├── engineering_quotation.py    # engineering.quotation (extends sale.order)
│   └── project_project.py         # extends project.project with eng link
├── wizard/
│   ├── __init__.py
│   ├── request_revision.py        # commercial "request revision" wizard
│   └── request_revision_views.xml
├── security/
│   ├── ir.model.access.csv
│   ├── security.xml               # groups: engineering_user, commercial_user
│   └── record_rules.xml           # multi-group record rules (if needed)
├── views/
│   ├── engineering_project_views.xml
│   ├── engineering_bom_views.xml
│   ├── engineering_boq_views.xml
│   ├── engineering_quotation_views.xml  # extends sale.order form
│   └── menus.xml
├── report/
│   └── quotation_report.xml        # customer-facing: final price only
├── data/
│   ├── sequence_data.xml           # ENG/BOQ/QUO sequences
│   └── product_data.xml           # shared "Engineering Project" finished-good + summary-line service product
├── demo/
│   └── demo.xml                    # demo engineering project + scope (NOT required by tests)
├── tests/
│   ├── __init__.py
│   ├── test_engineering_bom.py
│   ├── test_engineering_boq.py
│   ├── test_quotation_markup.py
│   ├── test_approval_generates_mo.py
│   ├── test_rfq_on_shortage.py
│   └── test_project_timeline.py
└── migrations/
    └── (none in v1)
```

**Structure Decision**: Single Odoo addon at
`custom_addons/engineering/` following the canonical Odoo 18 layout.
No frontend/backend split (Odoo is a monolithic web framework). Models
split by business concept (SRP); wizards for transactional actions;
security per group; tests per user story.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Table intentionally empty.