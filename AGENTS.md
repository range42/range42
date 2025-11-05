# Repository Guidelines

## Project Structure & Module Organization
- `pub/` holds active code; `priv/` mirrors operations assets and stays read-only unless coordinated with range ops.
- `pub/range42-backend-api` contains the FastAPI + Ansible orchestrator (`app/` for Python, `inventory/` and `playbooks/` for automation glue).
- `pub/range42-deployer-ui` stores the Vue 3 designer: shared widgets in `src/components/`, Pinia stores in `src/stores/`, Playwright specs in `e2e/`.
- Catalog bundles live in `pub/range42-catalog`, `pub/range42-playbooks`, and the Ansible role repos; reuse them instead of copying tasks into the API.

## Build, Test, and Development Commands
- Backend API: `cd pub/range42-backend-api && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`; run `./start.sh` for uvicorn and collection installs. Validate catalog hooks with `ansible-playbook -i inventory/sample generic.yml --check`.
- Deployer UI: `cd pub/range42-deployer-ui && npm ci`, use `npm run dev` for Vite hot reload, `npm run build` for the production bundle under `dist/`.
- Automation helpers: run `npx playwright install` before end-to-end tests and `ansible-galaxy install -r requirements.yml` when catalog roles change.

## Coding Style & Naming Conventions
- Python follows PEP 8 with four-space indentation and type-hinted public functions; keep routers in `app/routers/` and name modules after the catalog bundle they trigger.
- Vue components use `<script setup>`, PascalCase filenames such as `NodePalette.vue`, and colocated `*.spec.ts` tests; Pinia stores stay in `src/stores/` with camelCase keys.
- YAML playbooks prefer two-space indentation and uppercase task labels that mirror their Ansible role (`RUN ACTION - range42-ansible_roles-proxmox_controller`).
- Run `npm run lint` for UI changes, `ansible-lint playbooks/*.yml` for automation, and format Python with `python -m black` (or `ruff format` if installed).

## Testing Guidelines
- UI unit tests rely on Vitest; place new cases under `src/**/__tests__` and run `npm run test:unit` before requesting review.
- UI end-to-end paths live in `e2e/`; execute `npm run test:e2e` locally and include Playwright traces for regressions.
- Backend updates need reproducible steps: record `curl_utils/` scripts or HTTPX sessions plus `ansible-playbook ... --check` output against `inventory/px-testing`.

## Commit & Pull Request Guidelines
- Use imperative, component-prefixed subjects (e.g., `ui: add bundle selector`, `api: harden inventory loader`) and mention affected playbooks or bundles in the body.
- Pull requests should link the driving issue, list manual verification commands, and attach UI screenshots or terminal output; document rollback steps for deployment scripts.
- Request review from the relevant module owner (`@deployer-ui`, `@backend-api`, `@catalog`) and wait for one approval plus passing CI before merging.
