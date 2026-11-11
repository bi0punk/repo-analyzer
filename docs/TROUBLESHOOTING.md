# Troubleshooting

## 1. `repo-analyzer: command not found`

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

En la Action, el paquete se instala desde `github.action_path`; si falla, revisa
que el repositorio tenga `pyproject.toml` y `repo_agent/`.

## 2. `analyze` no termina o tarda demasiado

- Excluye vendors y artefactos:

```bash
repo-analyzer analyze . --extra-exclude node_modules --extra-exclude .venv
```

- Baja `--tree-depth` a 2.
- El análisis no descarga nada; si tarda, es por cantidad de archivos.

## 3. El bundle de contexto viene vacío o incompleto

| Causa | Solución |
|---|---|
| Presupuesto muy bajo | Sube `--llm-max-input-tokens` |
| Archivo principal no detectado | Revisa `repo_diagnostic.md` → sección de prioridad |
| Repo con solo binarios | Normal: no hay texto que incluir |
| Exclusión demasiado agresiva | Revisa `--extra-exclude` y `.gitignore` |

## 4. El resumen LLM no aparece

- Define `REPO_AGENT_LLM_ENDPOINT` y `REPO_AGENT_LLM_MODEL`.
- Comprueba el endpoint:

```bash
curl -s "$REPO_AGENT_LLM_ENDPOINT/models"
```

- Sin endpoint, el reporte heurístico sigue generándose (es lo esperado).

## 5. `scan` devuelve 401/403

```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user
```

- Token caducado o sin scope `repo`/`public_repo`.
- Límite de la API: usa `GITHUB_SCAN_MODE=public` o espera al reset.
- GitHub Enterprise: define `GITHUB_API_BASE_URL` con `/api/v3`.

## 6. La Action falla al subir el artefacto

- El input `output-dir` debe existir tras el análisis; si usas una ruta fuera
  del workspace, `upload-artifact` no la encuentra.
- Desactiva la subida con `upload-artifact: "false"` para depurar.

## 7. CI en rojo

```bash
uv venv .venv --python 3.12
uv pip install -e ".[dev]"
.venv/bin/ruff check .
.venv/bin/mypy repo_agent src
.venv/bin/vulture repo_agent src/repo_scanner_mvp --min-confidence 70
.venv/bin/bandit -q -r repo_agent src/repo_scanner_mvp
.venv/bin/pytest -q --cov=repo_agent --cov=repo_scanner_mvp --cov-fail-under=65
```

Errores típicos:

- **vulture**: un símbolo usado solo por `argparse`/entrypoints puede requerir
  ajustar la confianza o añadirlo a un whitelist.
- **mypy**: el proyecto usa `ignore_missing_imports`; tipa las funciones nuevas.
- **pytest**: `tests/conftest.py` añade `src/` al path; si mueves paquetes,
  actualiza ese archivo.

## 8. Recolectar diagnóstico

```bash
repo-analyzer analyze . --output-dir /tmp/diag --print-report > /tmp/diag.txt
python -m pip show repo-scanner-mvp >> /tmp/diag.txt
git rev-parse --short HEAD >> /tmp/diag.txt
```

Adjunta el informe y la versión al abrir un issue.
