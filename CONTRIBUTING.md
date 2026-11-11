# Contribuir

Rama de trabajo: `dev`; `main` recibe merges `--no-ff` con CI verde.

## Entorno

```bash
uv venv .venv --python 3.12
uv pip install -e ".[dev]"
```

## Flujo

1. Rama desde `dev` (`feat/*`, `fix/*`, `docs/*`).
2. Commits atómicos en imperativo.
3. PR contra `dev` con CI verde.

## Calidad

```bash
ruff check .
mypy repo_agent src
vulture repo_agent src/repo_scanner_mvp --min-confidence 70
bandit -q -r repo_agent src/repo_scanner_mvp
pytest -q --cov=repo_agent --cov=repo_scanner_mvp --cov-fail-under=65
pip-audit
```

## Tests

- `tests/test_*.py` cubren reglas, priorización, presupuesto, bundle y CLI.
- `tests/test_action_metadata.py` valida `action.yml` y un análisis real.
- `tests/conftest.py` añade `src/` al path; los paquetes viven en `repo_agent/`
  y `src/repo_scanner_mvp/`.

## Documentación

`docs/ACTION.md`, `docs/CONFIGURATION.md`, `docs/TROUBLESHOOTING.md` y
`docs/ARCHITECTURE.md`.
