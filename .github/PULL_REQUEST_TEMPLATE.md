## Qué cambia

## Por qué

## Cómo se probó

- [ ] `ruff check .`
- [ ] `mypy repo_agent src`
- [ ] `vulture repo_agent src/repo_scanner_mvp --min-confidence 70`
- [ ] `pytest -q --cov=repo_agent --cov=repo_scanner_mvp --cov-fail-under=65`

## Checklist

- [ ] Tests nuevos o actualizados
- [ ] Sin tokens ni rutas personales en el diff
- [ ] `action.yml` actualizado si cambian inputs/outputs
