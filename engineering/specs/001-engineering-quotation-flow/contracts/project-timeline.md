# Contract: Project-Module Timeline Link

**User Story**: US4 — Project Module Manages Construction Timeline
**Owning models**: `project.project` (extended),
`project.task` (used), `engineering.project`.
**Security**: `engineering.group_engineering_user` and
`engineering.group_commercial_user` (read project link);
`project.group_project_user` (edit tasks/milestones — standard Project
group).

## Behavior Contract

### `engineering.project._create_or_link_project()`

- **Preconditions**: `state == 'approved'` (called from
  `_generate_mo`); `project` module installed (manifest `depends`).
- **Behavior**:
  1. If `project_id` is set, reuse it; otherwise create a
     `project.project` with name = engineering project name, partner =
     customer.
  2. Set `engineering_project_id` back-link on the `project.project`.
  3. For each `engineering.boq.line` on the current BoQ revision,
     create a `project.task` (name = service product display name,
     planned qty = service qty, project = the linked project) —
     material (BoM) lines do NOT seed tasks (they are procurement-
     tracked via MRP/stock).
- **Postconditions**: `project_id` set on `engineering.project`;
  `engineering_project_id` set on `project.project`; one
  `project.task` per BoQ service line exists (SC-006).
- **Idempotency**: raises `UserError` if `project_id` already set and
  tasks already seeded (no duplicate tasks).

### Navigation Contract

- The `engineering.project` form MUST show a smart button / stat
  button linking to `project_id` reachable in one click (SC-006).
- The `project.project` form MUST show a smart button back to
  `engineering_project_id`.
- Tasks and milestones are managed via the standard Project module UI
  (no custom scheduling engine in v1).

## Out of Scope (v1)

- Custom Gantt/dependency scheduling engine (uses standard Project
  module dependency rules).
- Seeding tasks from BoM materials (materials are procurement-tracked).
- Multi-project program rollups.