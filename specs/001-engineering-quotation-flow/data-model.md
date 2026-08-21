# Data Model: Engineering-to-Quotation-to-Manufacturing Flow

**Feature**: 001-engineering-quotation-flow
**Date**: 2026-08-20
**Odoo version**: 18.0

> Model names follow the `<module>.<model>` Odoo convention. Fields
> use Odoo 18 `fields` types. Relationships use `Many2one` /
> `One2many` / `Many2many`. All new models declare `_name`, `_description`,
> `_order`, and `_rec_name` (or `_rec_name_search`) per constitution
> Principle IV.

## New Models

### `engineering.project`

The top-level engineering work order record. One per customer order.

| Field | Type | Notes |
|-------|------|-------|
| `name` | `Char` | Sequence `eng.project` (e.g. `ENG/2026/0001`). `_rec_name`. |
| `partner_id` | `Many2one('res.partner')` | Customer. Required. |
| `sale_order_id` | `Many2one('sale.order')` | The customer-facing quotation (extended). Set on quotation creation. |
| `project_id` | `Many2one('project.project')` | Linked construction-timeline project. Set on approval/MO generation. |
| `mrp_production_id` | `Many2one('mrp.production')` | The MO generated on approval. |
| `state` | `Selection` | `draft`, `sent_to_commercial`, `approved`, `manufacturing`, `rejected`. Default `draft`. |
| `revision_number` | `Integer` | Starts at 1; increments on commercial "request revision". |
| `is_current_revision` | `Boolean` | True on the active revision; False on retained prior revisions. Default True. |
| `active` | `Boolean` | Archive support. Default True. |
| `company_id` | `Many2one('res.company')` | Multi-company (host rules). Default `company_id` from user. |
| `bom_ids` | `One2many('engineering.bom', 'project_id')` | The BoM(s) for this project. |
| `boq_ids` | `One2many('engineering.boq', 'project_id')` | The BoQ(s) for this project. |

**State transitions** (research R12, supersedes R7):
```text
draft --send_to_commercial--> sent_to_commercial
sent_to_commercial --request_revision--> draft (new revision)
sent_to_commercial --customer_approve--> approved
approved --generate_mo--> manufacturing
sent_to_commercial --customer_reject--> rejected
rejected --re_quote--> draft (same revision)
```

**Methods** (extension points, OCP):
- `action_send_to_commercial()` — validate non-empty scope (FR-013);
  lock scope; set `state = 'sent_to_commercial'`; create the
  `sale.order` (engineering quotation) with one summary
  `sale.order.line` (R14); set `sale_order_id`. If `sale_order_id` is
  already set (e.g. re-quote from `rejected`), reuse and reset to
  draft.
- `action_request_revision()` — commercial only; cancel the current
  revision's `sale.order` (R13, retained for audit); create new
  revision (`revision_number + 1`, previous marked
  `is_current_revision=False`); new revision starts with
  `sale_order_id = False`; set `state = 'draft'`.
- `action_customer_approve()` — set `state = 'approved'`; call
  `_generate_mo()` and `_create_or_link_project()`.
- `action_customer_reject()` — set `state = 'rejected'` (auditable
  intermediate, R12); cancel the `sale.order`; no MO created.
- `action_re_quote()` — from `rejected` only; set `state = 'draft'`
  (same revision, re-quote).
- `_generate_mo()` — orchestrate `mrp.bom` + `mrp.production` creation
  from BoM materials (using the shared finished-good product, R15);
  attach BoQ services as non-stock work lines; trigger procurement
  (RFQs) via standard MRP confirm.
- `_create_or_link_project()` — create/link `project.project`; seed
  tasks from BoQ service lines.
- `_check_scope_editable()` — raise `UserError` if state ≠ `draft`
  (used in BoM/BoQ line create/write/unlink).

### `engineering.bom`

The engineering Bill of Materials (material specifications) for a
project. One current BoM per project per revision.

| Field | Type | Notes |
|-------|------|-------|
| `name` | `Char` | Defaults to project name + `/BOM`. `_rec_name`. |
| `project_id` | `Many2one('engineering.project')` | Required, ondelete cascade. |
| `line_ids` | `One2many('engineering.bom.line', 'bom_id')` | Material lines. |
| `total_standard_cost` | `Float` (compute) | Σ line standard cost. |
| `company_id` | `Many2one('res.company')` (related) | From project. |
| `state` | `Selection` (related) | From project (for view read-only rules). |

**Methods**:
- `_check_editable()` — delegate to `project_id._check_scope_editable()`.
- `create/write/unlink` overrides — call `_check_editable()`.

### `engineering.bom.line`

A single material line on a BoM.

| Field | Type | Notes |
|-------|------|-------|
| `bom_id` | `Many2one('engineering.bom')` | Required, ondelete cascade. |
| `product_id` | `Many2one('product.product')` | Required; material/stockable/consumable product. |
| `product_qty` | `Float` | Required, > 0. |
| `product_uom_id` | `Many2one('uom.uom')` | Required; default from product. |
| `standard_cost` | `Float` (compute) | `product_id.standard_price` at line time. |
| `line_cost` | `Float` (compute) | `product_qty * standard_cost`. |

**Constraints**: `product_qty > 0`; `product_id` must not be a service
product (rejected with `UserError` — services belong on the BoQ).

### `engineering.boq`

The engineering Bill of Quantities (service scope) for a project.
One current BoQ per project per revision.

| Field | Type | Notes |
|-------|------|-------|
| `name` | `Char` | Defaults to project name + `/BOQ`. `_rec_name`. |
| `project_id` | `Many2one('engineering.project')` | Required, ondelete cascade. |
| `line_ids` | `One2many('engineering.boq.line', 'boq_id')` | Service lines. |
| `total_standard_cost` | `Float` (compute) | Σ line standard cost. |
| `company_id` | `Many2one('res.company')` (related) | From project. |
| `state` | `Selection` (related) | From project. |

**Methods**: same lock pattern as `engineering.bom`.

### `engineering.boq.line`

A single service line on a BoQ.

| Field | Type | Notes |
|-------|------|-------|
| `boq_id` | `Many2one('engineering.boq')` | Required, ondelete cascade. |
| `product_id` | `Many2one('product.product')` | Required; service-type product. |
| `product_qty` | `Float` | Required, > 0. |
| `product_uom_id` | `Many2one('uom.uom')` | Required; default from product. |
| `standard_cost` | `Float` (compute) | `product_id.standard_price`. |
| `line_cost` | `Float` (compute) | `product_qty * standard_cost`. |

**Constraints**: `product_qty > 0`; `product_id` must be a service
product (rejected with `UserError` — materials belong on the BoM).

### `engineering.quotation` (extends `sale.order`)

The customer-facing quotation. Implemented by `_inherit = 'sale.order'`
adding engineering-specific fields and behavior. The `sale.order`
itself remains the customer-facing document; the custom report shows
only the final price.

| Field (added) | Type | Notes |
|----------------|------|-------|
| `engineering_project_id` | `Many2one('engineering.project')` | Back-link to the engineering scope. |
| `internal_cost` | `Float` (compute) | `bom.total_standard_cost + boq.total_standard_cost`. Stored for reporting. |
| `markup_percent` | `Float` | Commercial-entered percentage. Default 0.0. |
| `final_estimate_price` | `Float` (compute) | `internal_cost * (1 + markup_percent/100)`. |

**Methods** (added on `sale.order`):
- `_compute_internal_cost()` — sum linked BoM + BoQ standard costs;
  raise warning if any line product has `standard_price = 0` (FR-015).
- `_compute_final_estimate_price()` — apply markup formula (FR-006).
- `action_send_quotation()` — super to use `sale`'s send; ensure
  customer-facing report renders only `final_estimate_price`.
- `action_approve()` — override/extend to call
  `engineering_project_id.action_customer_approve()`. No runtime
  dependency guard (FR-016 is install-time hard `depends`, R11).
- `action_reject()` — call `engineering_project_id.action_customer_reject()`
  (enters `rejected` state, R12); cancel the `sale.order`.

**`sale.order.line` content (R14)**: The engineering quotation carries
exactly ONE summary `sale.order.line`:
- `product_id` = the shared "Engineering Project" product
  (`data/product_data.xml`, R15).
- `product_uom_qty` = 1.
- `price_unit` = `final_estimate_price` (kept in sync on markup/cost
  change).
- No per-product BoM/BoQ detail is ever written to `sale.order.line`.

**Customer-facing report**: A custom QWeb report
(`report/quotation_report.xml`) renders only the project name,
customer, and `final_estimate_price`. It MUST NOT iterate
`order_line` product details (SC-003). Structural non-exposure (one
summary line only, R14) plus template non-rendering together enforce
SC-003.

### `engineering.mo.service.line` (extends `mrp.production`)

Non-stock work-line list for BoQ services attached to the MO.

| Field (added on `mrp.production`) | Type | Notes |
|-----------------------------------|------|-------|
| `engineering_service_line_ids` | `One2many('engineering.mo.service.line', 'production_id')` | BoQ services carried onto the MO. |

### `engineering.mo.service.line`

| Field | Type | Notes |
|-------|------|-------|
| `production_id` | `Many2one('mrp.production')` | Required, ondelete cascade. |
| `boq_line_id` | `Many2one('engineering.boq.line')` | Source service line (audit). |
| `product_id` | `Many2one('product.product')` | The service product. |
| `product_qty` | `Float` | Quantity to perform. |
| `product_uom_id` | `Many2one('uom.uom')` | UoM. |
| `state` | `Selection` | `to_do`, `done`. Default `to_do`. |

`_name = 'engineering.mo.service.line'`, `_description = 'Engineering MO Service Line'`,
`_order = 'id'`, `_rec_name = 'product_id'` (constitution Principle IV).

**Rationale**: Services are work to be performed, not stockable
components. They are tracked here as a separate work-line list on the
MO (FR-011), not as `mrp.bom.line` components.

### `project.project` extension

| Field (added) | Type | Notes |
|----------------|------|-------|
| `engineering_project_id` | `Many2one('engineering.project')` | Back-link. |

On MO generation, `_create_or_link_project()` creates a
`project.project` and seeds one `project.task` per BoQ service line
(product = service product, planned qty = service qty, name = service
product name + project name).

## Extended/Used Existing Models (read-only use)

- `product.product` / `product.template` — `standard_price` is the
  internal cost source (Q2). Material products vs service products are
  distinguished by the product's `type` (`consu`/`product` vs
  `service`).
- `uom.uom` — units of measure for all BoM/BoQ lines.
- `mrp.bom` / `mrp.bom.line` — generated on approval to drive the MO;
  components = BoM materials only.
- `purchase.order` — RFQs created by standard procurement on MO
  confirm; the module does NOT create `purchase.order` records directly
  (R6).
- `res.partner` — customer.
- `res.company` — multi-company passthrough.

## Validation Rules (from requirements)

- FR-013: `engineering.project.action_send_to_commercial()` raises
  `UserError` if both `bom_ids.line_ids` and `boq_ids.line_ids` are
  empty.
- FR-014: BoM/BoQ line `create/write/unlink` call
  `_check_scope_editable()`; raise `UserError` if project state ≠
  `draft`.
- FR-015: `_compute_internal_cost()` raises a `UserError` / validation
  warning listing products with `standard_price = 0`; does not
  silently total zero-cost lines.
- BoM line product type MUST be non-service; BoQ line product type MUST
  be service (enforced in line `create/write`).
- `product_qty > 0` on all lines.
- `markup_percent >= 0` (negative markup not allowed in v1).

## State Machine (consolidated)

See `engineering.project` state transitions above (R12). Quotation
(`sale.order`) states follow standard `sale` (`draft` → `sent` →
`sale`), with the engineering approval handler invoked on `sale`
confirmation; rejection enters `rejected` (R12) before `re_quote`
returns to `draft`.

## Module Data Records

### Shared "Engineering Project" product (`data/product_data.xml`, R15)

A single shared `product.product` / `product.template` created once at
module install and reused across all features:

- `name` = `Engineering Project`
- `type` = `service` (usable as the summary `sale.order.line` product,
  R14; non-stockable, so it does not interfere with MRP stock).
- For the MRP `mrp.bom` finished good: MRP allows a service-type
  finished good on a `mrp.bom` whose components are stockable; the MO
  produced quantity is informational. Verify during US3 implementation
  that Odoo 18 accepts a service-type finished good; if not, create a
  separate `consu`-type "Engineering Project (Finished Good)" product
  in the same data file.
- `standard_price` = 0 (the engineering quotation price is set on the
  `sale.order.line.price_unit`, not derived from this product's cost).
- `list_price` = 0 (placeholder; actual price comes from
  `final_estimate_price`).
- Lookup via `xml_id` `engineering.product_engineering_project` so
  code references it deterministically without hardcoding IDs.