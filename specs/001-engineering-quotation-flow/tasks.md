---

description: "Task list for Engineering-to-Quotation-to-Manufacturing Flow feature implementation"
---

# Tasks: Engineering-to-Quotation-to-Manufacturing Flow

**Input**: Design documents from `specs/001-engineering-quotation-flow/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Test-First is NON-NEGOTIABLE per the project constitution (Principle III). Tests are included for every non-trivial model method and user story, written and shown to fail BEFORE implementation. In the Foundational phase, model skeletons (declarations only, no logic) are created first so the module installs and tests can import the ORM layer; failing tests are written next; full field logic + methods are implemented to turn tests green (Red→Green).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. The revision flow is labeled `[REV]` (derived from FR-014/edge cases, not a primary spec user story).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, REV)
- Setup/Foundational/Polish phases: NO story label
- Include exact file paths in descriptions

## Path Conventions

- Odoo addon root: `custom_addons/engineering/`
- Subpackages: `models/`, `wizard/`, `security/`, `views/`, `report/`, `data/`, `demo/`, `tests/`, `migrations/`
- Paths shown are relative to the addon root.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for the `engineering` Odoo 18 addon.

- [X] T001 Replace scaffold `custom_addons/engineering/__manifest__.py` with real manifest: `name=Engineering`, `summary`, `description`, `category=Services/Engineering`, `version=18.0.1.0.0`, `depends=['base','product','uom','sale','stock','mrp','purchase','project']` (hard `depends` enforces FR-016 at install time, no runtime guard), `data=[security/ir.model.access.csv, security/security.xml, security/record_rules.xml, data/sequence_data.xml, data/product_data.xml, views/menus.xml, views/engineering_project_views.xml, views/engineering_bom_views.xml, views/engineering_boq_views.xml, views/engineering_quotation_views.xml, wizard/request_revision_views.xml, report/quotation_report.xml]`, `demo=[demo/demo.xml]` in `custom_addons/engineering/__manifest__.py`
- [X] T002 [P] Create `custom_addons/engineering/models/__init__.py` importing `engineering_project`, `engineering_bom`, `engineering_boq`, `engineering_quotation`, `project_project` (stubs created in Phase 2); add module docstring
- [X] T003 [P] Create empty `custom_addons/engineering/wizard/__init__.py`, `custom_addons/engineering/report/__init__.py` (report is XML-only, no Python), and `custom_addons/engineering/tests/__init__.py` (imports all `TestX` classes as they are created)
- [X] T004 [P] Create `custom_addons/engineering/security/security.xml` defining groups `engineering.group_engineering_user` (Engineering User) and `engineering.group_commercial_user` (Commercial User) under `base.group_user` with implied hierarchy (commercial implies engineering for read access)
- [X] T005 [P] Create `custom_addons/engineering/data/sequence_data.xml` with sequences `eng.project` (format `ENG/%(year)s/%(range_y)s`), `eng.bom`, `eng.boq`
- [X] T006 [P] Create `custom_addons/engineering/data/product_data.xml` defining the shared `engineering.product_engineering_project` product (`product.template`/`product.product`): `name=Engineering Project`, `type=service`, `standard_price=0`, `list_price=0`; xml_id `engineering.product_engineering_project` (R15 — reused as both the `mrp.bom` finished good and the `sale.order.line` summary product, R14)

**Checkpoint**: addon skeleton complete; module installs with `-i engineering` (models are stubs/empty at this point; view files may be empty placeholders).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core model skeletons, security, and lock semantics that MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

**Test-First ordering note** (constitution Principle III, analyze D3 fix): model *skeletons* (declarations: `_name`, `_description`, `_order`, `_rec_name`, empty field stubs that allow the module to install and tests to import the ORM layer) are created first. Failing tests are written next. Full field logic + methods are implemented to turn tests green. Skeletons contain NO logic, so they do not violate Test-First.

### Foundational Models (skeletons)

- [X] T007 Create `engineering.project` skeleton in `custom_addons/engineering/models/engineering_project.py`: `_name='engineering.project'`, `_description='Engineering Project'`, `_order='revision_number desc, id desc'`, `_rec_name='name'`; field declarations only (no method logic): `name`, `partner_id`, `sale_order_id`, `project_id`, `mrp_production_id`, `state` (Selection: `draft`,`sent_to_commercial`,`approved`,`manufacturing`,`rejected` — note `rejected` is an auditable intermediate state per R12), `revision_number` (default 1), `is_current_revision` (default True), `active`, `company_id`, `bom_ids` (One2many to `engineering.bom`), `boq_ids` (One2many to `engineering.boq`); default `state='draft'`
- [X] T008 [P] Create `engineering.bom` skeleton in `custom_addons/engineering/models/engineering_bom.py`: `_name='engineering.bom'`, `_description='Engineering Bill of Materials'`, `_rec_name='name'`; field declarations only: `name`, `project_id` (required, ondelete cascade), `line_ids` (One2many to `engineering.bom.line`), `total_standard_cost` (compute, no logic yet), `company_id` (related), `state` (related to project)
- [X] T009 [P] Create `engineering.bom.line` skeleton in `custom_addons/engineering/models/engineering_bom.py` (same file): `_name='engineering.bom.line'`, `_description='Engineering BoM Line'`, `_order='id'`, `_rec_name='product_id'`; field declarations only: `bom_id`, `product_id`, `product_qty`, `product_uom_id`, `standard_cost` (compute), `line_cost` (compute)
- [X] T010 [P] Create `engineering.boq` skeleton in `custom_addons/engineering/models/engineering_boq.py`: mirror of `engineering.bom` (`_name='engineering.boq'`, `_description='Engineering Bill of Quantities'`, `_rec_name='name'`; `line_ids` → `engineering.boq.line`)
- [X] T011 [P] Create `engineering.boq.line` skeleton in `custom_addons/engineering/models/engineering_boq.py`: mirror of `engineering.bom.line` (`_name='engineering.boq.line'`, `_description='Engineering BoQ Line'`, `_rec_name='product_id'`)

### Foundational Tests (written to FAIL — Red)

- [X] T012 [P] Write failing tests in `custom_addons/engineering/tests/test_engineering_project.py`: `TestEngineeringProject(TransactionCase)` — create defaults (state=draft, revision_number=1, is_current_revision=True), `name` sequence assignment, `partner_id` required; import through `tests/__init__.py`
- [X] T013 [P] Write failing tests in `custom_addons/engineering/tests/test_engineering_bom.py`: `TestEngineeringBom(TransactionCase)` — line create blocked when project state != draft (FR-014); material product only (service product rejected, UserError); qty>0 enforced; `total_standard_cost` computes from line costs
- [X] T014 [P] Write failing tests in `custom_addons/engineering/tests/test_engineering_boq.py`: `TestEngineeringBoq(TransactionCase)` — service product only (material rejected, UserError); qty>0; `total_standard_cost`; lock on send

### Foundational Security

- [X] T015 Create `custom_addons/engineering/security/ir.model.access.csv` with one row per model (`engineering.project`, `engineering.bom`, `engineering.bom.line`, `engineering.boq`, `engineering.boq.line`): full CRUD for `group_engineering_user` on project/bom/boq in draft; read-only for `group_commercial_user` (write enforced via record rules in T016)
- [X] T016 [P] Create `custom_addons/engineering/security/record_rules.xml`: rule `engineering_bom_commercial_read_only_after_send` restricting commercial write on bom/boq when project state != draft; rule `engineering_project_engineering_edit_draft` restricting engineering write to draft state
- [X] T017 [P] Create `custom_addons/engineering/views/menus.xml`: top menu `Engineering` with submenus `Projects`, `Bill of Materials`, `Bill of Quantities`, `Quotations` (under Sales reuse), linking to action windows defined in US-phase view files

### Foundational Implementation (Green — make tests pass)

- [X] T018 Implement `engineering.project` create/defaults/sequence logic in `custom_addons/engineering/models/engineering_project.py` to make T012 pass
- [X] T019 Implement `engineering.bom.line` constraints + computes in `custom_addons/engineering/models/engineering_bom.py`: `product_id.type` must NOT be `service` (UserError); `product_qty > 0` (ValidationError); `standard_cost` = `product_id.standard_price`; `line_cost` = `product_qty * standard_cost`; `engineering.bom.total_standard_cost` = Σ line costs
- [X] T020 Implement `engineering.boq.line` constraints + computes in `custom_addons/engineering/models/engineering_boq.py`: `product_id.type` MUST be `service` (UserError if non-service); `product_qty > 0`; `standard_cost`/`line_cost` computes; `engineering.boq.total_standard_cost` = Σ line costs
- [X] T021 Implement `engineering.project._check_scope_editable()` in `custom_addons/engineering/models/engineering_project.py`: raise `UserError` if `state != 'draft'`; wire BoM/BoQ `create/write/unlink` to call `_check_editable()` → `project_id._check_scope_editable()` (FR-014)
- [X] T022 Run `odoo-bin -i engineering --test-enable --stop-after-init` and confirm T012–T014 pass (Red→Green)

**Checkpoint**: Foundation ready — `engineering.project`, BoM, BoQ skeletons + logic, security groups, lock semantics, and their tests green. User story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Engineering Drafts BoM & BoQ (Priority: P1) 🎯 MVP

**Goal**: An engineering user creates a project, drafts a materials BoM and a services BoQ, and persists them — fully independently of commercial/MRP/Project.

**Independent Test**: As engineering user, create a project, add 2 material lines + 1 service line, edit quantities, and save. No commercial/MRP/Project actions triggered. (See `quickstart.md` Scenario 1.)

### Tests for User Story 1 (write first, fail before implementation)

- [X] T023 [P] [US1] Add failing test in `custom_addons/engineering/tests/test_engineering_bom.py` for `action_send_to_commercial()` rejecting empty scope (both BoM and BoQ empty → UserError, FR-013)
- [X] T024 [P] [US1] Add failing test in `custom_addons/engineering/tests/test_engineering_bom.py` for `action_send_to_commercial()` succeeding with ≥1 line and transitioning state to `sent_to_commercial`; BoM/BoQ become read-only to engineering (FR-014)
- [X] T025 [P] [US1] Add failing test in `custom_addons/engineering/tests/test_engineering_boq.py` for BoQ line with `product_id.type != service` raising UserError (material-vs-service separation)

### Implementation for User Story 1

- [X] T026 [US1] Implement `engineering.project.action_send_to_commercial()` in `custom_addons/engineering/models/engineering_project.py`: validate non-empty scope (FR-013); set `state='sent_to_commercial'`; log INFO event `scope sent`
- [X] T027 [US1] Create view `custom_addons/engineering/views/engineering_project_views.xml`: form with header statusbar (`draft`→`sent_to_commercial`→`approved`→`manufacturing`→`rejected`), notebook tabs for `Bill of Materials` (`bom_ids` tree/form inline) and `Bill of Quantities` (`boq_ids` tree/form inline), smart-button placeholders for Quotation/MO/Project; `Send to Commercial` button visible to engineering group in draft state
- [X] T028 [US1] Create view `custom_addons/engineering/views/engineering_bom_views.xml`: `engineering.bom` form with editable `line_ids` tree (product, qty, UoM, standard_cost readonly, line_cost readonly) — tree editable only when parent project state=draft; action window + menu item under `Engineering > Bill of Materials`
- [X] T029 [US1] Create view `custom_addons/engineering/views/engineering_boq_views.xml`: parallel to BoM for `engineering.boq` / `engineering.boq.line`; menu under `Engineering > Bill of Quantities`
- [X] T030 [US1] Wire `Send to Commercial` button to `action_send_to_commercial()` in the project form (T027); verify tests T023/T024 pass

**Checkpoint**: User Story 1 fully functional and independently testable — engineering draft BoM+BoQ, send-to-commercial lock. (MVP deliverable.)

---

## Phase 4: User Story 2 - Commercial Builds Customer-Facing Quotation (Priority: P2)

**Goal**: A commercial user receives the locked scope, computes internal cost (Standard Cost), applies a single markup, generates a customer-facing quotation showing only the final price, and sends it.

**Independent Test**: Given a `sent_to_commercial` project with BoM+BoQ, a commercial user opens the linked quotation, sets markup, verifies final price formula, prints the customer report (only final price), and sends — no MO/Project triggered. (See `quickstart.md` Scenario 2.)

### Tests for User Story 2 (write first, fail before implementation)

- [X] T031 [P] [US2] Add failing test in `custom_addons/engineering/tests/test_quotation_markup.py`: `TestQuotationMarkup(TransactionCase)` — `_compute_internal_cost()` sums BoM+BoQ standard costs; raises validation error listing products with `standard_price==0` (FR-015); does NOT silently total zero
- [X] T032 [P] [US2] Add failing test in `custom_addons/engineering/tests/test_quotation_markup.py` for `_compute_final_estimate_price()` = `internal_cost * (1 + markup_percent/100)` (FR-006); recomputes on markup change
- [X] T033 [P] [US2] Add failing test in `custom_addons/engineering/tests/test_quotation_markup.py` for the engineering quotation carrying EXACTLY ONE `sale.order.line` (R14): `product_id == engineering.product_engineering_project.product_variant_id`, `product_uom_qty == 1`, `price_unit == final_estimate_price`; no per-product BoM/BoQ detail on `order_line`
- [X] T034 [P] [US2] Add failing test in `custom_addons/engineering/tests/test_quotation_markup.py` for customer-facing QWeb report `report/quotation_report.xml` rendering ONLY project name, customer, `final_estimate_price` — NO `order_line` / BoM / BoQ detail (SC-003)

### Implementation for User Story 2

- [X] T035 [US2] Create `engineering_quotation.py` in `custom_addons/engineering/models/` extending `sale.order` via `_inherit`: add fields `engineering_project_id`, `internal_cost` (compute, store=True), `markup_percent` (Float, default 0.0, `>=0` constraint), `final_estimate_price` (compute, store=True); implement `_compute_internal_cost()` (sum BoM+BoQ standard costs, warn on zero-cost products per FR-015), `_compute_final_estimate_price()` (FR-006); add to `models/__init__.py`
- [X] T036 [US2] Extend `action_send_to_commercial()` in `custom_addons/engineering/models/engineering_project.py` (T026): create a `sale.order` (engineering quotation) with `engineering_project_id` set and exactly ONE summary `sale.order.line` (`product_id=engineering.product_engineering_project.product_variant_id`, `product_uom_qty=1`, `price_unit=final_estimate_price`) — R14/R15; set `project.sale_order_id`; if `sale_order_id` already set (re-quote from `rejected`), reuse and reset `sale.order` to draft
- [X] T037 [US2] Keep the summary `sale.order.line.price_unit` in sync with `final_estimate_price` (override `_compute_final_estimate_price` write or `sale.order` `write`/`onchange` to update the line) so the `sale.order` total equals `final_estimate_price`
- [X] T038 [US2] Create view `custom_addons/engineering/views/engineering_quotation_views.xml`: inherit `sale.view_order_form` via `<xpath>` to add `engineering_project_id`, `internal_cost` (readonly), `markup_percent`, `final_estimate_price` fields in an `Engineering` group; keep the single summary `order_line` visible to commercial but labeled `Internal (not shown to customer)`; the customer report (T039) renders only the final price
- [X] T039 [US2] Create `custom_addons/engineering/report/quotation_report.xml`: QWeb template `engineering.report_quotation_document` inheriting `sale.report_saleorder_document` and overriding the lines section to render only a single row: project name + `final_estimate_price`; register report action `engineering.action_report_quotation` with `paperformat_id` from sale
- [X] T040 [US2] Override `sale.order.action_quotation_send` (or extend `action_send_quotation`) in `custom_addons/engineering/models/engineering_quotation.py` to attach `engineering.action_report_quotation` as the report; log INFO `quotation sent`; verify tests T031–T034 pass

**Checkpoint**: User Stories 1 AND 2 both work independently. Commercial quotation with single markup, single summary line (R14), customer-facing report with zero line leakage (SC-003).

---

## Phase 5: User Story 3 - Customer Approval Generates MO + RFQs (Priority: P3)

**Goal**: On customer approval, generate a real `mrp.bom` + `mrp.production` from BoM materials (using the shared finished-good product, R15), attach BoQ services as non-stock MO work lines, and let standard procurement trigger RFQs for shortages.

**Independent Test**: Given a `sent` quotation, approve it → one MO created from a generated `mrp.bom` matching BoM materials; BoQ services attached as `engineering.mo.service.line`; RFQs appear only for shortage materials at exact shortage quantity. No Project work triggered. (See `quickstart.md` Scenario 3.)

### Tests for User Story 3 (write first, fail before implementation)

- [X] T041 [P] [US3] Add failing test in `custom_addons/engineering/tests/test_approval_generates_mo.py`: `TestApprovalGeneratesMo(TransactionCase)` — approve quotation → `engineering.project.state='manufacturing'`, `mrp_production_id` set, one `mrp.production` exists, its `bom_id` is a real `mrp.bom` whose `bom_line_ids` match the engineering BoM material lines (product+qty+UoM), and the `mrp.bom.product_id` references `engineering.product_engineering_project` (R15)
- [X] T042 [P] [US3] Add failing test in `custom_addons/engineering/tests/test_approval_generates_mo.py` for BoQ services attached as `engineering.mo.service.line` entries on the MO (one per BoQ service line, `state='to_do'`), NOT as `mrp.bom.line` components (FR-011)
- [X] T043 [P] [US3] Add failing test in `custom_addons/engineering/tests/test_rfq_on_shortage.py`: `TestRfqOnShortage(TransactionCase)` — setup product with reordering rule / MTO route and insufficient stock; approve → exactly one `purchase.order` (draft RFQ) per shortage product with the shortage quantity (FR-010); with sufficient stock, no RFQ created
- [X] T044 [P] [US3] Add failing test in `custom_addons/engineering/tests/test_approval_generates_mo.py` for idempotency: re-calling `_generate_mo()` when `mrp_production_id` already set raises `UserError` (no duplicate MO)
- [X] T045 [P] [US3] Add failing test in `custom_addons/engineering/tests/test_reject_requote.py`: `TestRejectRequote(TransactionCase)` — from `sent`, reject → `engineering.project.state='rejected'` (R12, auditable intermediate), `sale.order` cancelled, no MO created; then `action_re_quote()` → `state='draft'` (same revision), scope editable; re-send creates a fresh `sale.order` (R13)

### Implementation for User Story 3

- [X] T046 [US3] Create `engineering.mo.service.line` model in `custom_addons/engineering/models/engineering_mo.py` (new file): `_name='engineering.mo.service.line'`, `_description='Engineering MO Service Line'`, `_order='id'`, `_rec_name='product_id'` (constitution Principle IV); fields `production_id` (Many2one `mrp.production`, required, ondelete cascade), `boq_line_id` (Many2one `engineering.boq.line`), `product_id`, `product_qty`, `product_uom_id`, `state` (Selection `to_do`,`done`, default `to_do`); add to `models/__init__.py`; add `ir.model.access.csv` row (T015 update)
- [X] T047 [US3] Extend `mrp.production` via `_inherit` in `custom_addons/engineering/models/engineering_mo.py`: add `engineering_service_line_ids` One2many to `engineering.mo.service.line`; add `engineering_project_id` Many2one back-link
- [X] T048 [US3] Implement `engineering.project._generate_mo()` in `custom_addons/engineering/models/engineering_project.py`: (1) create `mrp.bom` (type=`normal`, `product_id=engineering.product_engineering_project.product_variant_id` — R15 shared finished good; if Odoo 18 rejects service-type finished good on `mrp.bom`, add a `consu`-type "Engineering Project (Finished Good)" product to `data/product_data.xml` and use it here) with `mrp.bom.line` entries = BoM materials (product, qty, UoM); (2) create `mrp.production` from that `mrp.bom` via standard `create` + `action_confirm`; (3) for each BoQ service line create `engineering.mo.service.line` on the production; (4) set `project.mrp_production_id`; set `state='manufacturing'`; raise `UserError` if `mrp_production_id` already set; log INFO events
- [X] T049 [US3] Extend `sale.order.action_confirm()` (or Odoo 18's approval hook) in `custom_addons/engineering/models/engineering_quotation.py` to call `engineering_project_id.action_customer_approve()` → sets `state='approved'` then calls `_generate_mo()` (T048). NO runtime dependency guard — FR-016 is enforced at install time via hard `depends` (R11), so `mrp`/`purchase`/`stock` are always present
- [X] T050 [US3] Implement `engineering.project.action_customer_approve()` in `custom_addons/engineering/models/engineering_project.py`: set `state='approved'`; call `_generate_mo()`; log INFO `approved`
- [X] T051 [US3] Implement `engineering.project.action_customer_reject()` and `sale.order.action_reject()` (added) in `custom_addons/engineering/models/engineering_quotation.py` + `engineering_project.py`: reject sets `state='rejected'` (R12 auditable intermediate) and cancels `sale.order`; no MO created; add `engineering.project.action_re_quote()` (from `rejected` only) → `state='draft'` (same revision, re-quote); log INFO `rejected`/`re_quote`
- [X] T052 [US3] Add MO smart-button to `engineering_project_views.xml` (T027) showing `mrp_production_id` count and linking to the MO form; add `Reject` and `Re-quote` buttons (commercial group, visible in `sent`/`rejected` states); verify tests T041–T045 pass

**Checkpoint**: User Stories 1, 2, AND 3 independently functional. Approval → real `mrp.bom`+MO (shared finished good, R15), services as non-stock work lines, RFQs for shortages, rejection → `rejected` state → re-quote.

---

## Phase 6: User Story 4 - Project Module Manages Construction Timeline (Priority: P4)

**Goal**: On approval/MO generation, link a `project.project` to the engineering project and seed one `project.task` per BoQ service line; manage timeline via standard Project UI.

**Independent Test**: After US3 approval, open the engineering project → click Project smart button → a `project.project` opens with one task per BoQ service; add milestones/dependencies and reschedule. (See `quickstart.md` Scenario 4.)

### Tests for User Story 4 (write first, fail before implementation)

- [X] T053 [P] [US4] Add failing test in `custom_addons/engineering/tests/test_project_timeline.py`: `TestProjectTimeline(TransactionCase)` — after approval, `engineering.project.project_id` set; `project.project.engineering_project_id` back-link set; one `project.task` exists per BoQ service line (count == BoQ line count) with matching product/qty; NO tasks seeded from BoM material lines
- [X] T054 [P] [US4] Add failing test in `custom_addons/engineering/tests/test_project_timeline.py` for idempotency: re-calling `_create_or_link_project()` when `project_id` set and tasks already seeded raises `UserError` (no duplicate tasks)
- [X] T055 [P] [US4] Add failing test in `custom_addons/engineering/tests/test_project_timeline.py` for reachability: the engineering project form exposes a smart button to `project_id` (SC-006)

### Implementation for User Story 4

- [X] T056 [US4] Extend `project.project` via `_inherit` in `custom_addons/engineering/models/project_project.py`: add `engineering_project_id` Many2one to `engineering.project`; add to `models/__init__.py`; update `ir.model.access.csv` (T015) for the new field (read/write per groups)
- [X] T057 [US4] Implement `engineering.project._create_or_link_project()` in `custom_addons/engineering/models/engineering_project.py`: if `project_id` set, reuse; else create `project.project` (name=project name, partner=customer, `engineering_project_id`=self); for each BoQ service line create a `project.task` (name=service product display, `planned_qty`/`product_id`=service product, project=linked project); raise `UserError` if `project_id` already set and tasks already seeded; log INFO
- [X] T058 [US4] Wire `_create_or_link_project()` into `action_customer_approve()` (T050) after `_generate_mo()` so approval creates MO AND links project in one action
- [X] T059 [US4] Add Project smart-button to `engineering_project_views.xml` (T027) linking to `project_id`; create inherited `project_project_views.xml` (xpath into `project.project` form) with an Engineering smart-button linking back to `engineering_project_id`; verify tests T053–T055 pass

**Checkpoint**: All user stories (US1–US4) independently functional. Construction timeline linked and seeded from BoQ services.

---

## Phase 7: Revision Flow (Edge case from FR-014 / clarify Q5)

**Note**: This phase is labeled `[REV]` (revision), not `[US5]`. It is derived from FR-014 and the revision edge case, not a primary spec user story (the spec has US1–US4 only). It operates on the send/lock mechanism introduced in US1, so it depends only on US1 and can run in parallel with US2/US3/US4. (analyze F1 fix.)

**Goal**: A commercial user can request a revision of a `sent_to_commercial` scope, creating a new editable draft revision while retaining the previous version for audit (and cancelling the old `sale.order`, R13).

**Independent Test**: From `sent_to_commercial` state, engineering edit blocked; commercial runs Request Revision wizard → new revision created, previous retained + its `sale.order` cancelled, new revision starts `sale_order_id = False`, scope editable again. (See `quickstart.md` Scenario 5.)

### Tests for Revision Flow (write first, fail before implementation)

- [X] T060 [P] [REV] Add failing test in `custom_addons/engineering/tests/test_revision_flow.py`: `TestRevisionFlow(TransactionCase)` — from `sent_to_commercial`, engineering user write on BoM line raises `UserError` (locked, FR-014/SC-007); commercial user runs `action_request_revision()` → `revision_number` increments, previous project revision `is_current_revision=False`, previous revision's `sale.order` is cancelled (R13), new project revision `state='draft'`, `is_current_revision=True`, `sale_order_id=False`, BoM/BoQ editable
- [X] T061 [P] [REV] Add failing test in `custom_addons/engineering/tests/test_revision_flow.py` for access control: only `group_commercial_user` can call `action_request_revision()`; engineering user gets `AccessError`

### Implementation for Revision Flow

- [X] T062 [REV] Implement `engineering.project.action_request_revision()` in `custom_addons/engineering/models/engineering_project.py`: require `state=='sent_to_commercial'` and commercial group; cancel the current revision's `sale.order` (R13, retained for audit); copy current project (and its BoM/BoQ via `copy()`) to a new record with `revision_number+1`, `is_current_revision=True`, `state='draft'`, `sale_order_id=False`; mark current revision `is_current_revision=False`; log INFO `revision requested`
- [X] T063 [REV] Create wizard `engineering.request.revision.wizard` in `custom_addons/engineering/wizard/request_revision.py` (TransientModel) with a `reason` text field and a confirm button calling `project_id.action_request_revision()`; create `custom_addons/engineering/wizard/request_revision_views.xml` form view; add wizard action to the project form visible to commercial group when `state=='sent_to_commercial'`
- [X] T064 [REV] Verify tests T060–T061 pass; verify previous revision retained and readable (audit), its `sale.order` cancelled, new revision gets a fresh quotation on its next send

**Checkpoint**: All stories plus the revision edge case functional. Scope lock + revision (with sale.order cancellation) enforced.

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories.

- [X] T065 [P] Add `_(...)` translation wrappers to ALL user-facing strings in models (UserError messages, field labels via views) — verify no hardcoded English in `UserError` calls
- [X] T066 [P] Replace any `sudo()` usage with explicit group/record-rule enforcement or add an inline justification comment per constitution Principle IV; grep `custom_addons/engineering/models/*.py` for `sudo(`
- [X] T067 [P] Create `custom_addons/engineering/demo/demo.xml` with a sample engineering project, 3 material lines, 2 service lines, and a sent quotation — for demonstration ONLY; confirm no test depends on demo data
- [X] T068 Run full module install + test: `odoo-bin -c <cfg> -d <test_db> -i engineering --test-enable --stop-after-init --log-level=:INFO`; confirm zero WARNING+ log lines during install and all `test_*` cases green
- [X] T069 [P] Code cleanup: remove scaffold `models/models.py` commented sample and any dead imports; ensure `_logger = logging.getLogger(__name__)` defined per file with business-event INFO logs (scope sent, quotation sent, rejected, approved, MO generated, RFQ triggered, revision requested, re_quote)
- [X] T070 [P] Security review: verify `ir.model.access.csv` grants least privilege; verify `engineering.mo.service.line` and the `sale.order`/`mrp.production`/`project.project` extension fields have appropriate access; verify record rules cover draft-only engineering write
- [X] T071 Run quickstart.md validation scenarios 1–7 manually against a fresh test DB; record pass/fail per scenario; fix any regressions
- [X] T072 [P] Bump `custom_addons/engineering/__manifest__.py` `version` to `18.0.1.0.1` if any PATCH fixes are made during polish (constitution Principle V versioning)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup; BLOCKS all user stories.
- **User Stories (Phase 3–6)**: All depend on Foundational completion.
  - US1 (Phase 3): independent — implements the core BoM/BoQ/lock.
  - US2 (Phase 4): depends on US1 (needs a `sent_to_commercial` scope + sale.order creation).
  - US3 (Phase 5): depends on US2 (needs a `sent` quotation); also implements rejection/re-quote.
  - US4 (Phase 6): depends on US3 (needs approval/MO to link project).
  - REV (Phase 7): depends on US1 (needs the send/lock mechanism); can run in parallel with US2/US3/US4 if staffed.
- **Polish (Phase N)**: depends on all desired user stories + revision being complete.

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational. No dependency on other stories. **MVP**.
- **US2 (P2)**: Starts after US1. Integrates with US1 scope but independently testable (mock a sent scope).
- **US3 (P3)**: Starts after US2. Integrates with US1 scope + US2 quotation; independently testable (mock an approved quotation); also delivers rejection/re-quote (R12).
- **US4 (P4)**: Starts after US3. Integrates with US3 MO; independently testable (mock an approved project with MO).
- **REV (revision)**: Starts after US1. Independent of US2–US4 (operates on the send/lock introduced in US1 and the sale.order created in US2's send path — coordinate T062's sale.order cancellation with US2's sale.order creation logic).

### Within Each User Story

- Tests MUST be written and FAIL before implementation (constitution Principle III).
- Models (skeletons in Foundational; full logic in story phase) before services/orchestration.
- Views after models.
- Story complete before moving to next priority.

### Parallel Opportunities

- Setup tasks marked [P] (T002–T006) run in parallel.
- Foundational model skeletons T008–T011 marked [P] run in parallel.
- Foundational tests T012–T014 marked [P] run in parallel.
- Within US2, tests T031–T034 marked [P] run in parallel.
- Within US3, tests T041–T045 marked [P] run in parallel.
- Within US4, tests T053–T055 marked [P] run in parallel.
- Within REV, tests T060–T061 marked [P] run in parallel.
- Polish tasks T065/T066/T067/T069/T070/T072 marked [P] run in parallel.
- REV (Phase 7) can be developed in parallel with US2/US3/US4 by a second developer (operates only on US1's lock mechanism + US2's sale.order creation).

---

## Parallel Example: User Story 3

```bash
# Launch all tests for User Story 3 together:
Task: "Add failing test test_approval_generates_mo.py in tests/test_approval_generates_mo.py" (T041)
Task: "Add failing test for BoQ services as engineering.mo.service.line in tests/test_approval_generates_mo.py" (T042)
Task: "Add failing test test_rfq_on_shortage.py in tests/test_rfq_on_shortage.py" (T043)
Task: "Add failing test idempotency in tests/test_approval_generates_mo.py" (T044)
Task: "Add failing test reject/re-quote in tests/test_reject_requote.py" (T045)

# After tests fail, implement in dependency order:
Task: "Create engineering.mo.service.line model in models/engineering_mo.py" (T046)
Task: "Extend mrp.production with engineering_service_line_ids" (T047)  # depends on T046
Task: "Implement _generate_mo() in models/engineering_project.py" (T048)  # depends on T046, T047
Task: "Extend sale.order.action_confirm() approval hook" (T049)  # depends on T048
Task: "Implement action_customer_approve/reject/re_quote" (T050, T051)  # depends on T048
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories).
3. Complete Phase 3: User Story 1 (BoM + BoQ + lock).
4. **STOP and VALIDATE**: run `quickstart.md` Scenario 1; run
   `tests/test_engineering_bom.py` + `tests/test_engineering_boq.py`.
5. Deploy/demo if ready — the MVP delivers a managed engineering scope
   for a customer order.

### Incremental Delivery

1. Setup + Foundational → Foundation ready.
2. US1 → Test independently → Demo (MVP: engineering scope).
3. US2 → Test independently → Demo (commercial quotation, single summary line, customer-facing final price only).
4. US3 → Test independently → Demo (approval → MO + RFQs; rejection → `rejected` → re-quote).
5. US4 → Test independently → Demo (construction timeline linked).
6. REV → Test independently → Demo (revision flow with audit trail + sale.order cancellation).
7. Polish → full quickstart validation (scenarios 1–7).

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together.
2. Once Foundational is done:
   - Developer A: US1 → US2 → US3 (sequential, dependent chain).
   - Developer B: REV (revision flow — depends only on US1's lock + US2's sale.order).
   - Developer C: US4 (once US3 is far enough to mock an approved project).
3. Stories integrate independently; REV merges after US1/US2; US4 merges after US3.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks.
- [Story] label maps task to specific user story (US1–US4) or REV
  (revision, derived from FR-014) for traceability.
- Each user story is independently completable and testable per the spec.
- Tests MUST fail before implementing (constitution Principle III).
- Foundational skeletons (declarations only, no logic) are created
  before failing tests to allow the module to install and tests to
  import the ORM layer; this does not violate Test-First (skeletons
  contain no testable logic). (analyze D3 fix.)
- Commit after each task or logical group; tests must pass on a fresh
  DB before committing.
- Stop at any checkpoint to validate a story independently.
- Avoid: vague tasks, same-file conflicts, cross-story dependencies
  that break independence.
- The shared `engineering.product_engineering_project` product (R15)
  serves as both the `mrp.bom` finished good and the `sale.order.line`
  summary product (R14). If Odoo 18 rejects a service-type finished good
  on `mrp.bom`, add a `consu`-type variant in `data/product_data.xml`
  (noted in T048).