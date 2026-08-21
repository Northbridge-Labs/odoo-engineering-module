<!--
=== Sync Impact Report ===
Version change: 0.0.0 (uninitialized template) → 1.0.0
- Initial ratification of project constitution.

Modified principles:
- [PRINCIPLE_1_NAME] → I. Single Responsibility per Artifact (SRP)
- [PRINCIPLE_2_NAME] → II. Open/Closed via Odoo Inheritance (OCP)
- [PRINCIPLE_3_NAME] → III. Test-First (NON-NEGOTIABLE)
- [PRINCIPLE_4_NAME] → IV. Odoo Conventions & Security Compliance
- [PRINCIPLE_5_NAME] → V. Simplicity, Observability & Versioning

Added sections:
- "Odoo Module Constraints" (formerly [SECTION_2_NAME])
- "Development Workflow" (formerly [SECTION_3_NAME])
- "Governance"

Removed sections: none.

Templates requiring updates:
- .specify/templates/plan-template.md — ✅ compatible (Constitution Check gate references constitution generically; no edits needed)
- .specify/templates/spec-template.md — ✅ compatible (no constitution-specific placeholders)
- .specify/templates/tasks-template.md — ✅ compatible (phase structure aligns with Test-First principle)
- .specify/templates/checklist-template.md — ✅ compatible
- .specify/templates/commands/* — no commands directory present; N/A

Follow-up TODOs: none. All placeholders resolved.
==========================
-->

# Engineering (Odoo Module) Constitution

## Core Principles

### I. Single Responsibility per Artifact (SRP)

Each Odoo artifact — model, wizard, controller, view XML, report, security
record — MUST own exactly one well-defined responsibility.

- One model per business concept; cross-cutting concerns are delegated,
  not duplicated, across models.
- Business logic lives in model methods (Inheritance/Delegation), not in
  views or controllers. Controllers MUST only marshal HTTP I/O.
- Wizards are single-purpose transactional helpers; reusable workflows
  are promoted to model methods.
- A field, method, or view is changed for one reason only. If a change
  touches multiple responsibilities, split the artifact first.

**Rationale**: Odoo modules rot when models accumulate unrelated logic.
SRP keeps upgrades, migrations, and peer reviews tractable.

### II. Open/Closed via Odoo Inheritance (OCP)

The module MUST be extensible without editing its source. New behavior
is added through Odoo's extension mechanisms, never by forking core
files.

- Prefer `_inherit` (model extension) and `_inherit`/`_delegate`
  (delegation) over copying upstream code.
- Use `Modular`/mixin models (`_name` + `_inherit` equal) to expose
  reusable capabilities other modules can compose.
- Views extend via `<xpath>` in inherited views; never replace a base
  view wholesale unless the base is owned by this module.
- Expose stable extension points: well-named methods, `@api.model`,
  `_inherits`, and hook methods (`_compute_*`, `write`/`create`
  overrides with `super()`). Document them.
- Public model `_name` strings and field names are part of the API:
  renaming or removing them is a MAJOR breaking change.

**Rationale**: Odoo's inheritance is its primary extension vector. Honoring
OCP keeps the module compatible with downstream customizations and
future Odoo upgrades.

### III. Test-First (NON-NEGOTIABLE)

Tests are written, approved, and shown to fail BEFORE implementation.
Red-Green-Refactor is strictly enforced.

- Every model method with non-trivial logic MUST have an Odoo
  `TransactionCase` (or `SavepointCase`) test covering happy path and
  edge cases before the method is implemented.
- Tests live in the module's `tests/` package with `__init__.py`
  importing each `TestX` class; `tests/__init__.py` is required.
- Demo data (`demo/`) MUST NOT be required for tests to pass; tests
  create their own fixtures.
- A feature is "done" only when its tests pass on a fresh database
  with `-i <module> --test-enable --stop-after-init`.
- Regression: any bug fix MUST land with a reproducing test.

**Rationale**: Odoo's ORM/XML/environment coupling makes regressions
expensive. Test-First is the only reliable guardrail.

### IV. Odoo Conventions & Security Compliance

The module MUST follow Odoo's documented conventions and security model
exactly. Deviations require documented justification in the plan.

- `__manifest__.py` keys, naming, `depends`, `data`/`demo` ordering
  follow the official manifest spec; `version` follows `X.Y.Z` Odoo
  convention (e.g. `17.0.1.0.0`).
- Every new model MUST declare `_name`, `_description`, and
  `_order`; `_rec_name` is set or a `_rec_name_search` override
  provides a display name.
- Access rights: every model ships an entry in
  `security/ir.model.access.csv`; record rules and user groups are
  declared in `security/` and loaded via `data`.
- No `sudo()` without an inline comment explaining the reason and
  the security boundary; prefer groups and record rules.
- Translations use `_(...)`; no hardcoded user-facing English strings
  in views that bypass the translation mechanism.
- Views are namespaced, inherit base views rather than overwriting,
  and validate against the active Odoo version's DTD.

**Rationale**: Convention violations block upgrades, break security, and
make the module unreviewable by the Odoo community/maintainers.

### V. Simplicity, Observability & Versioning

Start with the simplest viable implementation; add complexity only when
a measured need justifies it. Make behavior observable; version
deliberately.

- YAGNI: do not pre-build "future" models/fields. A field ships when a
  user story requires it.
- Logging via `_logger = logging.getLogger(__name__)`; structured
  messages at INFO for business events, DEBUG for diagnostics. No
  `print()`.
- `__manifest__.py` module version uses semantic-style bumping:
  MAJOR for breaking ORM/field changes, MINOR for new features, PATCH
  for fixes. New dependencies require a MINOR bump.
- Database migrations use `migrations/` scripts; destructive changes
  are gated by a migration with a documented back-out path.

**Rationale**: Odoo upgrades and long-term maintenance punish
uncontrolled complexity and silent behavior.

## Odoo Module Constraints

- **Language/Runtime**: Python 3 (matching the target Odoo major
  version's supported runtime) + Odoo ORM/XML framework.
- **Module path**: `custom_addons/engineering/` with the canonical Odoo
  layout: `models/`, `views/`, `security/`, `controllers/`, `report/`
  (if needed), `wizard/` (if needed), `demo/`, `tests/`, `data/`,
  `migrations/`, plus top-level `__init__.py` and `__manifest__.py`.
- **Base dependencies**: `['base']` minimum; add `project`,
  `hr`, `account`, etc. only when a user story requires it and the
  dependency is recorded in the plan's Complexity Tracking.
- **Storage**: PostgreSQL via the Odoo ORM. No raw SQL except in
  documented performance-critical paths with a `_auto`-compatible
  rationale.
- **Target platform**: the Odoo major version declared in
  `__manifest__.py` `version`. Cross-version support is out of scope
  unless explicitly added.
- **Security**: principle of least privilege in
  `ir.model.access.csv`; multi-company rules via
  `res.company` record rules when applicable.
- **No external services**: the module is self-contained within Odoo.
  External integrations are separate modules that depend on this one.

## Development Workflow

- **Spec → Plan → Tasks**: every feature follows the Spec-Kit
  workflow: `/speckit.spec` (user stories + requirements), `/speckit.plan`
  (technical context + constitution check), `/speckit.tasks` (phased
  task list), `/speckit.implement`, `/speckit.checklist`.
- **Constitution Check** (plan.md) MUST pass before Phase 0 research
  and is re-checked after Phase 1 design. Violations require a
  Complexity Tracking entry or a constitution amendment.
- **Branch**: one feature branch per spec, named
  `[###]-feature-name` matching the spec folder.
- **Commit cadence**: commit after each task or logical group; tests
  must pass on the fresh-test DB before committing.
- **Code review**: every PR MUST reference the spec and verify (a)
  SRP of changed artifacts, (b) OCP via inheritance not fork, (c) tests
  added/failing-first, (d) security entries present, (e) manifest
  version bumped appropriately.
- **Quality gates**: module installs cleanly with
  `-i engineering --stop-after-init`; all tests green; no Odoo log
  warnings at WARNING+ level during install or test run.

## Governance

This constitution is the single source of truth for the
`engineering` Odoo module. It supersedes ad-hop preferences, prior
scaffolds, and individual conventions.

- **Supremacy**: any conflict between this constitution and another
  practice, this constitution wins. The scaffold shipped in the
  repository's initial `models/models.py` (commented sample) is
  explicitly superseded.
- **Amendment procedure**: amendments require (1) a written proposal,
  (2) impact analysis on existing specs/tasks, (3) a migration plan
  for in-flight work, and (4) an updated version bump. An amendment
  is recorded by rewriting this file and prepending a new Sync Impact
  Report.
- **Versioning policy**: MAJOR for removal/redefinition of a
  principle or governance rule, MINOR for a new principle or
  materially expanded guidance, PATCH for clarifications/typos.
- **Compliance review**: every `/speckit.plan` MUST re-read this
  file and emit a Constitution Check section; every `/speckit.tasks`
  MUST verify task categories align with the principles above.
- **Runtime guidance**: refer to `AGENTS.md` (when present) for
  day-to-day development guidance; this constitution governs
  principles, not tactics.

**Version**: 1.0.0 | **Ratified**: 2026-08-20 | **Last Amended**: 2026-08-20