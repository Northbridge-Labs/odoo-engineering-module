# Contract: Engineering Scope (BoM + BoQ)

**User Story**: US1 — Engineering Drafts BoM & BoQ
**Owning models**: `engineering.project`, `engineering.bom`,
`engineering.bom.line`, `engineering.boq`, `engineering.boq.line`
**Security**: `engineering.group_engineering_user` (create/edit in
`draft`); `engineering.group_commercial_user` (read; trigger revision).

## Behavior Contract

### `engineering.project.action_send_to_commercial()`

- **Preconditions**: `state == 'draft'`; at least one line across
  `bom_ids.line_ids` or `boq_ids.line_ids` (FR-013).
- **Postconditions**: `state == 'sent_to_commercial'`; BoM and BoQ
  become read-only (`_check_scope_editable()` enforces); a `sale.order`
  (engineering quotation) is created with exactly one summary
  `sale.order.line` (`engineering.product_engineering_project`,
  qty=1, `price_unit = final_estimate_price`, R14); `sale_order_id`
  is set. If re-quoting from `rejected` with `sale_order_id` already
  set, reuse and reset the `sale.order` to draft.
- **Errors**: `UserError` if scope empty; `AccessError` if caller is
  not in `engineering.group_engineering_user`.

### `engineering.project.action_request_revision()`

- **Preconditions**: `state == 'sent_to_commercial'`; caller in
  `engineering.group_commercial_user`.
- **Postconditions**: the current revision's `sale.order` is cancelled
  (retained for audit, R13); a new revision of the project scope is
  created (`revision_number` increments; previous revision's
  `is_current_revision` set to False); the new revision starts with
  `sale_order_id = False` (gets a fresh quotation on its next
  `action_send_to_commercial()`); `state == 'draft'`; previous
  revision retained for audit.
- **Errors**: `AccessError` if not commercial; `UserError` if not in
  `sent_to_commercial` state.

### `engineering.bom.line` / `engineering.boq.line` create/write/unlink

- **Preconditions**: parent project `state == 'draft'`.
- **Postconditions**: line persisted/edited/deleted.
- **Errors**: `UserError` if project state ≠ `draft` (FR-014);
  `UserError` if BoM line product type is service or BoQ line product
  type is non-service; `ValidationError` if `product_qty <= 0`.

### `engineering.bom._compute_total_standard_cost()` / `engineering.boq._compute_total_standard_cost()`

- **Returns**: `Float` = Σ `line.line_cost`.
- **Pure compute**: no side effects.

## Visibility Contract (who sees what)

- **Engineering user**: full BoM + BoQ detail, both lists.
- **Commercial user**: full BoM + BoQ detail with internal costs.
- **Customer (report)**: NEITHER list — only the final estimate price
  on the quotation report (see `quotation-approval.md`).