# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python scaffold for an academic reliable P2P messaging simulator. The current entry point is `main.py`, and requirements are documented in `HARNESS.md`.

As implementation grows, keep backend code in a Python package such as `backend/`, with separate modules for API routes, UDP routers, graph/Dijkstra logic, RDT protocols, configuration loading, and logging. Place React/Vite code in `frontend/`. Keep simulation files at the root or in `config/`, especially `roteador.config` and `enlaces.config`.

Recommended future layout:

```text
backend/
frontend/
tests/
config/
main.py
HARNESS.md
```

## Build, Test, and Development Commands

Create and activate a virtual environment before installing dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
```

Run the current scaffold:

```bash
python main.py
```

When FastAPI is introduced, prefer a command such as:

```bash
uvicorn backend.app:app --reload
```

When React/Vite is introduced under `frontend/`, use `npm install` once and `npm run dev` locally.

## Coding Style & Naming Conventions

Use Python 3 with 4-space indentation and descriptive snake_case names for functions, modules, and variables. Use PascalCase for classes such as router, packet, or protocol abstractions. Keep responsibilities separated: HTTP/WebSocket API code should not replace UDP communication between routers.

For frontend code, use PascalCase component names and separate route, state, and visualization logic when practical.

Follow the project design system documented in `DESIGN.md` for UI layout, colors, typography, spacing, and component behavior.

## Testing Guidelines

Add tests under `tests/` using `pytest` for Python code. Name test files `test_*.py` and test functions `test_*`. Prioritize unit tests for Dijkstra routing, packet serialization, RDT ACK/timeout/retransmission behavior, message length validation, and configuration parsing.

Run tests with:

```bash
pytest
```

For frontend work, add component or interaction tests only after the UI exists.

## Commit & Pull Request Guidelines

No Git history is available in this checkout, so use concise imperative commit messages such as `Add Dijkstra routing module` or `Validate message length`. Keep commits focused on one logical change.

Pull requests should include a short description, tests run, linked issue or assignment requirement when applicable, and screenshots for UI changes. Call out any changes to required UDP, RDT, topology, or configuration behavior.

## Agent-Specific Instructions

Follow the constraints in `HARNESS.md`. Do not replace router-to-router UDP with HTTP, bypass hop-by-hop routing, remove `roteador.config` or `enlaces.config`, or drop ACK, timeout, retransmission, stop-and-wait, local logs, or the 100-character message limit.
