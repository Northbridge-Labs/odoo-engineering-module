# Feature Specification: Engineering-to-Quotation-to-Manufacturing Flow

**Feature Branch**: `001-engineering-quotation-flow`

**Created**: 2026-08-20

**Status**: Draft

**Input**: User description: "engineering-module - Odoo module to manage engineering projects implementation. The process consists in receive the order from the customer, so they create the list of the necessary material and services for the ordered work. So, this list is sent to commercial department, to make a price quotation for the items on that list. To customer, just final project estimate price matters, material and services list is irrelevant. When the customer approves the quotation, it generates a manufacturing order on MRP module. That MO consumes the materials and triggers Purchase RFQs if needed. Link Project module to manage construction timeline. Engineering team will manage draft bill of materials and bill of quantities. Services should be included in BoM. Commercial team can apply a markup percentage to the quotation final value"

## Clarifications

### Session 2026-08-20

- Q: How should the Bill of Materials (materials) and Bill of Quantities (services) be structured? → A: Two linked lists on the project — a materials BoM (material specifications) and a separate services BoQ (scope with measure units) — both feeding the quotation and Manufacturing Order.
- Q: What cost should be used as the "internal cost" for materials and services in the quotation? → A: Standard Cost of each product (company-managed, stable baseline).
- Q: Is the markup a single percentage on the combined total, or separate per list/line? → A: One single markup percentage applied to the combined BoM + BoQ internal cost.
- Q: How does the engineering scope feed the MRP Manufacturing Order? → A: The engineering BoM/BoQ are a staging scope; on approval the module generates/links a real mrp.bom for materials and carries BoQ services as non-stock MO work lines.
- Q: How is the engineering scope protected from edits after it is sent to commercial? → A: Lock the scope on send; commercial "request revision" unlocks a new draft revision tied to the same project (original kept for audit).
- Q: How is FR-016 (missing-dependency message) enforced — install-time vs runtime? → A: Odoo hard `depends` in the manifest is the clear-message mechanism (install-time blocking); no runtime guard needed.
- Q: Is `rejected` a real state or just a return-to-draft on rejection? → A: Explicit `rejected` state as an intermediate before returning to `draft` (`sent_to_commercial → rejected → draft`), so rejection is a queryable auditable event.
- Q: What happens to the old revision's sale.order when a revision is requested? → A: The old revision's sale.order is cancelled (retained for audit); the new revision starts with sale_order_id = False and gets a fresh quotation on its next action_send_to_commercial().
- Q: What goes on the sale.order.line of the engineering quotation? → A: One summary line: a dedicated "Engineering Project" service product with product_uom_qty = 1 and price_unit = final_estimate_price. No per-product BoM/BoQ detail on sale.order.line.
- Q: What finished-good product does the generated mrp.bom reference? → A: One shared generic "Engineering Project" product, created once as module data (data/product_data.xml) and reused by every generated mrp.bom. Per-project identity lives on engineering.project, not on the MRP product.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Engineering Drafts Bill of Materials & Bill of Quantities (Priority: P1)

An engineering team member receives a customer work order and registers
the technical scope of the ordered engineering project. They create a
draft Bill of Materials (BoM) listing every material item needed and a
draft Bill of Quantities (BoQ) listing every service needed for the
work. The BoM and the BoQ are two distinct but linked lists on the
engineering project: the BoM holds material specifications (product,
quantity, UoM), and the BoQ holds the service scope (service product,
quantity, UoM). Both lists together form the engineering scope that is
sent to the commercial department. The engineering team can revise these
drafts at any time before the scope is sent to the commercial
department.

**Why this priority**: Without a structured materials + services list
there is nothing to quote, manufacture, or schedule. This is the
backbone of the entire engineering-to-delivery flow and the smallest
viable slice that delivers value (a managed engineering scope for an
order).

**Independent Test**: An engineering user can create a project scope,
add material lines to the BoM and service lines to the BoQ, edit
quantities on either list, and persist the drafts — all without
involving the commercial, MRP, or Project modules. The value delivered
is a saved, reviewable engineering scope (BoM + BoQ) tied to a customer
order.

**Acceptance Scenarios**:

1. **Given** a new engineering project linked to a customer order,
   **When** the engineering user adds a material line with product,
   quantity, and unit, **Then** the line is saved on the draft BoM and
   is visible in the project's materials list.
2. **Given** an existing draft project, **When** the engineering user
   adds a service line (labor/service product, quantity, unit) to the
   BoQ, **Then** the service line is saved on the BoQ and is
   distinguishable as a service scope entry, separate from the BoM.
3. **Given** a draft BoM and BoQ, **When** the engineering user edits a
   quantity on either list, **Then** the change is persisted and the
   drafts remain editable until the scope is explicitly sent to the
   commercial department.
4. **Given** a draft BoM and BoQ, **When** the engineering user
   attempts to send the scope to the commercial department with both
   lists empty, **Then** the action is rejected with a clear message
   that at least one line (material or service) is required.

---

### User Story 2 - Commercial Builds Customer-Facing Price Quotation (Priority: P2)

A commercial department user receives the engineering scope (BoM +
BoQ) and builds a price quotation for the customer. Internally the
quotation is backed by the full materials + services scope (so the
commercial team can verify cost across both lists), but the document
the customer sees shows only the final project estimate price — the
line-level breakdown is irrelevant to the customer. The commercial team
can apply a markup percentage to the computed internal cost; the final
quotation value reflects that markup. The quotation can be sent to the
customer for approval.

**Why this priority**: Converts engineering effort into a sellable
offer. It is the first slice that involves money and customer
interaction, but it depends on US1 (a BoM/BoQ scope must exist first),
so it sits at P2.

**Independent Test**: Given an engineering scope (BoM + BoQ) already
exists and is "sent to commercial", a commercial user can open it,
compute an internal cost from both lists, apply a markup, generate a
customer-facing quotation showing only the final price, and send it —
without triggering any manufacturing or project timeline work.

**Acceptance Scenarios**:

1. **Given** an engineering list that has been sent to the commercial
   department, **When** the commercial user opens it, **Then** they see
   the full materials + services breakdown with their costs, for
   internal use only.
2. **Given** the internal cost has been computed, **When** the
   commercial user enters a markup percentage, **Then** the final
   project estimate price is recalculated as internal cost × (1 +
   markup) and is shown as the customer-facing price.
3. **Given** a finalized quotation, **When** the commercial user
   generates the customer-facing quotation document, **Then** the
   document displays only the final project estimate price and does
   not expose the material/service line breakdown.
4. **Given** a customer-facing quotation, **When** the commercial user
   sends it to the customer, **Then** its status advances to "sent"
   and it becomes eligible for customer approval.

---

### User Story 3 - Customer Approval Generates Manufacturing Order (Priority: P3)

When the customer approves the quotation, the system automatically
generates a Manufacturing Order (MO) in the MRP module from the
approved engineering scope (BoM materials + BoQ services). The
engineering BoM and BoQ are a staging scope: on approval, the module
generates (or links) a real `mrp.bom` that holds the BoM materials as
its components, and creates the MO from that BoM. The BoQ services are
carried onto the MO as non-stock work lines (tracked separately from
material components), not as `mrp.bom` components. The MO consumes the
required materials and, where stock is insufficient, triggers Purchase
Requests for Quotation (RFQs) for the missing quantities. The approved
quotation's status advances to "approved/manufacturing".

**Why this priority**: Bridges commerce to production. It depends on
both a finalized quotation (US2) and an MRP integration, so it is P3.
Delivering it unlocks the operational manufacturing value of the
module.

**Independent Test**: Given an approved quotation, the system creates
exactly one MO from a generated/linked `mrp.bom` whose components match
the approved BoM material lines, carries the BoQ service lines as
non-stock work lines on the MO, reduces stock accordingly, and creates
RFQs only for the shortage quantities — all without any further user
action and without the Project timeline feature.

**Acceptance Scenarios**:

1. **Given** a quotation in "sent" status, **When** the customer
   approves it (recorded by commercial/engineering), **Then** the
   quotation status becomes "approved", a real `mrp.bom` is generated
   or linked from the approved BoM materials, and a Manufacturing Order
   is automatically created from that BoM with BoQ services attached as
   non-stock work lines.
2. **Given** an approved quotation and sufficient stock for all
   materials, **When** the MO is generated, **Then** the MO consumes
   the required material quantities and no Purchase RFQs are created.
3. **Given** an approved quotation and insufficient stock for one or
   more materials, **When** the MO is generated, **Then** a Purchase
   RFQ is created for each shortage material for the exact shortage
   quantity.
4. **Given** an approved quotation whose BoQ includes service lines,
   **When** the MO is generated, **Then** the services are carried
   onto the MO as non-stock work lines (not as `mrp.bom` components and
   not as stockable material consumption) so they can be tracked as
   work to be performed.

---

### User Story 4 - Project Module Manages Construction Timeline (Priority: P4)

Each engineering project is linked to the Project module so the
engineering/operations team can manage the construction timeline: tasks,
milestones, dates, and dependencies derived from the approved scope.
The project timeline is accessible from the engineering project record
and reflects the approved BoM/BoQ scope as actionable work items.

**Why this priority**: Adds schedule management on top of the
manufacturing flow. It depends on an approved quotation (US3) and
integrates the Project module, so it is the least critical MVP slice
and is delivered last.

**Independent Test**: Given an approved quotation and the resulting MO,
a project manager can open the linked project, view/create timeline
tasks tied to the engineering scope, and see milestone dates — without
re-running the quotation or manufacturing flows.

**Acceptance Scenarios**:

1. **Given** an approved quotation, **When** the manufacturing order is
   generated, **Then** a Project (or project task list) is created or
   linked and is reachable from the engineering project record.
2. **Given** the linked project, **When** the project manager adds
   tasks and milestones with start/end dates, **Then** the construction
   timeline is persisted and visible from both the project and the
   engineering project record.
3. **Given** a project timeline with dependent tasks, **When** a
   milestone date is moved, **Then** dependent tasks' scheduled dates
   are recomputed according to the project's dependency rules.

---

### Edge Cases

- What happens when the engineering scope is sent to commercial but
  the engineering team later edits the BoM or BoQ? (The scope is locked
  on send; only a commercial "request revision" action unlocks a new
  draft revision tied to the same project, with the original retained
  for audit.)
- What happens when a material on the BoM has no standard cost defined
  when the commercial team computes the internal cost? (A clear warning
  must be raised; the internal cost cannot be silently zero.)
- What happens when a service on the BoQ has no defined cost? (Same
  warning behavior as materials; missing service costs cannot be
  silently zero.)
- What happens when the customer requests changes after the quotation
  is sent but before approval? (A revised quotation cycle must be
  supported without losing the original BoM/BoQ scope.)
- What happens when a service line on the BoQ is a deliverable that
  itself consumes materials? (Services are tracked on the MO as
  non-stock components; nested material consumption for services is
  out of scope unless explicitly modeled.)
- What happens when the customer rejects the quotation? (The project
  enters an explicit `rejected` state for audit, then returns to
  `draft` for re-quotation on the same revision; no MO is created.)
- What happens when MRP/Purchase are not installed? (The module declares
  hard `depends` in its manifest; Odoo blocks install/uninstall with a
  clear message, so the unsupported configuration cannot exist.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow an engineering user to create an
  engineering project linked to a customer order.
- **FR-002**: The system MUST allow the engineering user to maintain a
  draft Bill of Materials (BoM) listing material products with quantity
  and unit of measure per project.
- **FR-003**: The system MUST allow the engineering user to maintain a
  draft Bill of Quantities (BoQ) listing service products with quantity
  and unit of measure per project. The BoQ is a separate list from the
  BoM, linked to the same engineering project, and represents the
  service scope.
- **FR-004**: The system MUST allow the engineering user to send the
  completed engineering scope (BoM + BoQ) to the commercial department,
  transitioning both lists out of the editable draft state.
- **FR-005**: The commercial department MUST be able to view the full
  BoM and BoQ with internal costs for pricing purposes.
- **FR-006**: The commercial department MUST be able to apply a markup
  percentage; the final project estimate price MUST equal the total
  internal cost (BoM + BoQ) multiplied by (1 + markup).
- **FR-007**: The system MUST produce a customer-facing quotation that
  shows only the final project estimate price and MUST NOT expose the
  BoM or BoQ line breakdown to the customer. The engineering quotation
  (`sale.order`) MUST carry exactly one summary `sale.order.line` for a
  dedicated "Engineering Project" service product with
  `product_uom_qty = 1` and `price_unit = final_estimate_price`; no
  per-product BoM or BoQ detail MUST appear on `sale.order.line`.
- **FR-008**: The system MUST allow the commercial department to send
  the quotation to the customer and record customer approval or
  rejection. On rejection, the engineering project MUST enter an
  explicit `rejected` state (auditable) before returning to `draft`
  for re-quotation on the same revision; no MO is created.
- **FR-009**: Upon customer approval, the system MUST automatically
  generate or link a real `mrp.bom` from the approved BoM materials and
  create a Manufacturing Order from it, with the BoQ services attached
  to the MO as non-stock work lines. The generated `mrp.bom` MUST
  reference a single shared generic "Engineering Project" finished-good
  product (created once as module data) reused across all projects;
  per-project identity is carried on `engineering.project`, not on the
  MRP product.
- **FR-010**: The generated Manufacturing Order MUST consume the
  required material quantities (from the BoM, via the `mrp.bom`) from
  stock and MUST trigger a Purchase RFQ for each material whose
  available stock is insufficient, sized to the exact shortage
  quantity.
- **FR-011**: BoQ service components MUST be attached to the
  Manufacturing Order as non-stock work lines (not as `mrp.bom`
  components and not as stockable material consumption) so they can be
  tracked as work to be performed.
- **FR-012**: The engineering project MUST be linked to the Project
  module so a construction timeline (tasks, milestones, dates,
  dependencies) can be managed from the project record.
- **FR-013**: The system MUST enforce that the engineering scope cannot
  be sent to commercial with both BoM and BoQ empty (at least one line
  across either list is required).
- **FR-014**: The system MUST lock the engineering scope (BoM and BoQ)
  when it is sent to the commercial department, preventing silent
  editing. The commercial department MAY issue a "request revision"
  action, which unlocks a new draft revision of the scope tied to the
  same engineering project (the previously sent version is retained
  for audit). Only this revision action MAY modify the scope after
  sending. On revision, the previous revision's `sale.order`
  (quotation) MUST be cancelled (retained for audit), and the new
  revision MUST start with `sale_order_id = False`, receiving a fresh
  quotation on its next `action_send_to_commercial()`.
- **FR-015**: The system MUST raise a clear warning if any BoM material
  or BoQ service product lacks a defined cost when the internal cost is
  computed, and MUST NOT silently treat missing costs as zero.
- **FR-016**: The module MUST declare hard dependencies (`depends` in
  `__manifest__.py`) on MRP, Purchase, and Project. Odoo enforces these
  at install time, producing a clear message and blocking any
  unsupported configuration (e.g. disabling a required addon) before it
  can exist. No runtime guard is required.

### Key Entities *(include if feature involves data)*

- **Engineering Project**: The top-level record representing a customer
  engineering work order; links to the customer order, the BoM, the
  BoQ, the quotation, the generated Manufacturing Order, and the linked
  Project-module project.
- **Engineering BoM (Draft)**: The engineering-maintained Bill of
  Materials for the project, holding material lines (product, quantity,
  UoM). It represents the material specifications of the work.
- **Engineering BoQ (Draft)**: The engineering-maintained Bill of
  Quantities for the project, a separate list from the BoM but linked
  to the same engineering project. It holds service lines (service
  product, quantity, UoM) and represents the service scope of the work.
- **Engineering Quotation**: The commercial document derived from the
  engineering scope (BoM + BoQ); carries the internal cost (sum of BoM
  and BoQ costs), the markup percentage, the final project estimate
  price, the customer-facing view, and the approval state. Implemented
  as an extended `sale.order` with exactly one summary
  `sale.order.line` ("Engineering Project" service product, qty=1,
  `price_unit = final_estimate_price`).
- **Customer-facing Quotation View**: The customer-visible
  representation of the quotation exposing only the final project
  estimate price.
- **Manufacturing Order (integration)**: The MRP MO generated on
  approval. The module generates/links a real `mrp.bom` from the
  approved BoM materials to drive the MO; the `mrp.bom` references a
  single shared generic "Engineering Project" finished-good product
  (module data), reused across all projects. BoQ services are attached
  to the MO as non-stock work lines. The MO consumes materials from
  stock and triggers Purchase RFQs for shortages.
- **Construction Project (integration)**: The Project-module project
  linked to the engineering project for timeline management (tasks,
  milestones, dependencies).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An engineering user can create a project's full materials
  + services draft list in under 5 minutes for a 20-line scope.
- **SC-002**: A commercial user can compute the internal cost, apply a
  markup, and produce a customer-facing quotation in under 2 minutes
  from a received engineering list.
- **SC-003**: 100% of customer-facing quotations generated expose only
  the final project estimate price with zero material/service line
  leakage.
- **SC-004**: Customer approval produces the corresponding Manufacturing
  Order in a single user action with no manual re-entry of BoM lines.
- **SC-005**: Purchase RFQs are created automatically for exactly the
  shortage quantities with no over- or under-ordering versus the
  computed shortfall.
- **SC-006**: 100% of approved engineering projects have a reachable,
  editable construction timeline in the Project module within one
  navigation step from the engineering project record.
- **SC-007**: Engineering list edits after commercial pricing begins are
  blocked 100% of the time without an explicit revision action.
- **SC-008**: Missing-cost products on the engineering list are flagged
  for 100% of lines where cost is undefined before the internal cost is
  finalized.

## Assumptions

- The target Odoo instance has the MRP, Purchase, and Project modules
  available; the engineering module declares them as dependencies for
  the manufacturing/timeline flows and degrades gracefully with a clear
  message if any are disabled.
- Materials and services are modeled using Odoo product variants:
  stockable/consumable products for materials and service products for
  services, so costs and procurement behavior come from the standard
  product master.
- The "internal cost" used by the commercial team is the Standard Cost
  of each product (material or service) on the line — the company-
  managed, stable cost baseline. If a product has no standard cost set,
  the system warns rather than silently using zero. Standard Cost is
  used for both BoM materials and BoQ services so the internal cost
  baseline is consistent with MRP consumption valuation.
- The customer-facing quotation is a single consolidated price; the
  customer does not require a per-line breakdown, and the module does
  not need to support optional per-line disclosure in v1.
- The markup is a single percentage applied to the total internal cost
  (BoM + BoQ) of the engineering scope; tiered or per-line markup is
  out of scope for v1.
- One approved quotation generates one Manufacturing Order; multi-MO
  splitting by workshop or phase is out of scope for v1.
- The construction timeline uses the standard Project module's tasks,
  milestones, and dependencies; no custom scheduling engine is built in
  v1.
- Multi-company behavior follows the existing `res.company` rules of the
  host Odoo instance; no custom multi-company logic is added unless a
  user story requires it.
- Revision of an approved/sent quotation is supported via a commercial
  "request revision" action, which unlocks a new draft revision of the
  engineering scope (BoM + BoQ) tied to the same engineering project;
  the previously sent version is retained for audit. Full quotation
  versioning history UI is out of scope for v1 beyond this revise
  action.