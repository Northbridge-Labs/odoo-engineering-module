# Engineering

Odoo 18 module that manages the engineering-to-quotation-to-manufacturing flow.

[![License: LGPL-3](https://img.shields.io/badge/license-LGPL--3-blue.svg)](LICENSE)

## Features

- Engineering drafts a **Bill of Materials** (material specs) and a **Bill of Quantities** (service scope) for a customer work order.
- Commercial applies a markup and issues a customer-facing **quotation** that exposes only the final project estimate price.
- On customer approval, a **Manufacturing Order** is generated from the approved BoM (BoQ services carried as non-stock work lines) and **Purchase RFQs** are created for stock shortages.
- Revision requests, rejection and re-quote flows.
- Each engineering project is linked to the **Project** module to manage the construction timeline.

## Requirements

- Odoo 18.0
- Odoo apps: `sale`, `stock`, `mrp`, `purchase`, `project` (plus `base`, `product`, `uom`)

## Installation

1. Clone this repository into your Odoo addons path:
   ```bash
   git clone https://github.com/Northbridge-Labs/odoo-engineering-module.git engineering
   ```
   The directory name must match the technical module name used in your instance.
2. Add the parent directory to `addons_path` in `odoo.conf`.
3. Restart Odoo, update the apps list and install **Engineering**.

## Branches and versions

One branch per supported Odoo series, named after the series (OCA convention):

| Branch | Odoo | Module version |
|--------|------|----------------|
| `18.0` | 18.0 | `18.0.x.y.z` |
| `19.0` | 19.0 | `19.0.x.y.z` |

`main` tracks the newest series. The manifest version always starts with the
branch name. Check out the branch that matches your Odoo version.

## Update flow

Development happens on the **oldest supported branch** and is forward-ported
(merged) into the newer ones, so every fix exists in all series:

```
18.0  ──●──●──●──────────●──  (fixes and features land here first)
         \    \          \
19.0  ────●────●──────────●──  (merge 18.0 into 19.0, then adapt for the new API)
```

1. Branch from `18.0`: `git checkout -b fix/short-name 18.0`.
2. Open a pull request against `18.0`, with tests passing.
3. After merge, forward-port: 
   ```bash
   git checkout 19.0
   git merge 18.0        # resolve conflicts, adapt code to Odoo 19 changes
   ```
   Run the tests on 19.0 and push.
4. Changes that only apply to a newer series are committed directly on that branch.
5. Bump the manifest `version` on every release (`<series>.<major>.<minor>.<patch>`)
   and tag it, e.g. `18.0-1.1.0`.
6. Never merge a newer branch into an older one.

## Tests

```bash
odoo-bin -d <test_db> -i engineering --test-enable --stop-after-init
```

## Contributing

Issues and pull requests are welcome. By contributing you agree that your
contribution is licensed under LGPL-3.

## License

[LGPL-3](LICENSE) — Copyright (c) Northbridge Labs.
