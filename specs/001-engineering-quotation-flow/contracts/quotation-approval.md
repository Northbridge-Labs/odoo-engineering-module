# Contract: Quotation → MO Orchestration

**User Stories**: US2 (quotation), US3 (approval → MO + RFQ)
**Owning models**: `sale.order` (extended → engineering quotation),
`engineering.project`, `mrp.bom`, `mrp.production`,
`engineering.mo.service.line`, `purchase.order` (via procurement).
**Security**: `engineering.group_commercial_user` (markup, send,
approve, reject); `engineering.group_engineering_user` (read quotation).

## Behavior Contract

### `sale.order._compute_internal_cost()` (added)

- **Preconditions**: `engineering_project_id` set.
- **Returns**: `Float` = `engineering.bom.total_standard_cost` +
  `engineering.boq.total_standard_cost`.
- **Errors**: raises a validation error listing any line product with
  `standard_price == 0` (FR-015); does NOT silently treat missing
  costs as zero.

### `sale.order._compute_final_estimate_price()` (added)

- **Returns**: `Float` = `internal_cost * (1 + markup_percent / 100)`.
- **Pure compute**; recomputed on `internal_cost` or `markup_percent`
  change (FR-006).
- The single summary `sale.order.line.price_unit` is kept in sync with
  this value (R14) so the `sale.order` total equals
  `final_estimate_price`.

### `sale.order.line` content (R14)

- Exactly ONE summary line per engineering quotation:
  - `product_id` = `engineering.product_engineering_project` (shared
    data product, R15).
  - `product_uom_qty` = 1.
  - `price_unit` = `final_estimate_price`.
- No per-product BoM/BoQ detail is ever written to `sale.order.line`.
- Structural non-exposure (one summary line) + template non-rendering
  together enforce SC-003 (zero line leakage).

### `sale.order.action_send_quotation()` (extended)

- **Behavior**: delegates to `sale`'s standard send; the customer
  report template (`report/quotation_report.xml`) renders only the
  project name, customer, and `final_estimate_price` (SC-003). No
  `order_line` product details exposed.
- **Postconditions**: `sale.order` state `draft` → `sent`;
  `engineering.project.state` remains `sent_to_commercial`.
- **Quotation creation**: the `sale.order` and its single summary
  `sale.order.line` are created by
  `engineering.project.action_send_to_commercial()` (see
  `engineering-scope.md`), not by this method.

### `sale.order.action_approve()` (extended/override hook)

- **Preconditions**: `state == 'sent'`; caller in
  `engineering.group_commercial_user`.
- **Postconditions**: `sale.order` state `sent` → `sale`;
  `engineering.project.state` → `approved`; then `approved` →
  `manufacturing` via `_generate_mo()`; `project.project` created/
  linked via `_create_or_link_project()`.
- **Errors**: None at runtime — FR-016 is enforced at install time
  via hard `depends` (R11); the module cannot be installed without
  `mrp`/`purchase`/`stock`/`project`, so the approval path is always
  reachable. No runtime guard.

### `sale.order.action_reject()` (added)

- **Preconditions**: `state == 'sent'`; caller in
  `engineering.group_commercial_user`.
- **Postconditions**: `engineering.project.state` → `rejected`
  (auditable intermediate, R12); `sale.order` cancelled; no MO created.
  A subsequent `action_re_quote()` on the project returns
  `state = 'draft'` (same revision) for re-quotation.

### `engineering.project._generate_mo()`

- **Behavior**:
  1. Create a real `mrp.bom` (type `normal`, product = the shared
     `engineering.product_engineering_project` finished good, R15)
     with `mrp.bom.line` entries = BoM materials (product, qty, UoM).
  2. Create a `mrp.production` from that `mrp.bom`.
  3. For each BoQ service line, create an
     `engineering.mo.service.line` attached to the production (non-
     stock work line, FR-011).
  4. Call `mrp.production.action_confirm()` → standard MRP/stock
     procurement triggers RFQs for shortage quantities (R6, FR-010).
- **Postconditions**: `mrp_production_id` set on `engineering.project`;
  `state == 'manufacturing'`; one MO created (FR-009); RFQs
  (`purchase.order` in draft) exist for each shortage material at the
  exact shortage quantity (FR-010); BoQ services attached as
  `engineering.mo.service.line` with `state = 'to_do'`.
- **Idempotency**: raises `UserError` if `mrp_production_id` already
  set (no duplicate MO).
- **Shared product note**: the same `engineering.product_engineering_project`
  product serves as (a) the `mrp.bom` finished good and (b) the
  `sale.order.line` summary product (R14/R15). If Odoo 18 rejects a
  service-type finished good on `mrp.bom`, fall back to a separate
  `consu`-type "Engineering Project (Finished Good)" product declared
  in the same `data/product_data.xml`.

## Customer-Facing Report Contract

- **Template**: `report/quotation_report.xml` (QWeb).
- **Renders**: project name, customer (`partner_id`), and
  `final_estimate_price` ONLY.
- **MUST NOT render**: any `order_line`, BoM, or BoQ line detail, no
  per-product prices, no markup breakdown.
- **Acceptance**: SC-003 — 100% of generated customer-facing
  quotations expose zero line-level leakage.