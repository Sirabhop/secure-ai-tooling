# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

CoSAI Risk Map — a Python/Streamlit web application for AI security risk assessment. Single service (no monorepo). See `README.md` and `APP_README.md` for details.

### Running the app

```bash
streamlit run streamlit_app.py --server.headless true
```

App serves on port 8501. PostgreSQL is optional; without it data stays in Streamlit session state.

### Lint

- **Python**: `ruff check .` (config in `pyproject.toml` is minimal; ruff defaults apply)
- **YAML**: `npx prettier --check "risk-map/**/*.yaml"` (config in `.prettierrc.yml`)

Note: the repo currently has pre-existing lint violations in both ruff and prettier; these are not regressions.

### Tests

```bash
pytest --timeout=60
```

All tests are under `scripts/hooks/tests/` and `scripts/hooks/issue_template_generator/tests/`. 885 tests as of this writing.

### Key caveats

- `pip install` places binaries in `~/.local/bin`; ensure it is on `PATH` (`export PATH="$HOME/.local/bin:$PATH"`).
- Node.js is only needed for `prettier` (YAML formatting). `npm ci` installs it from `package-lock.json`.
- The pre-commit hook installer (`scripts/install-precommit-hook.sh`) is interactive and should not be run by cloud agents.
