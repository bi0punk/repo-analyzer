# Repo Agent MVP v3

[![CI](https://github.com/bi0punk/repo-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/bi0punk/repo-analyzer/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

MVP funcional para diagnosticar repositorios locales y preparar un paquete de contexto útil para un LLM.

## Tabla de contenidos

- [Qué detecta](#qué-detecta-esta-versión)
- [Stack](#stack)
- [Arquitectura](#arquitectura)
- [Instalación](#instalación)
- [Uso](#uso)
- [Tests](#tests)
- [CI](#ci)
- [LLM opcional](#llm-opcional-por-endpoint-compatible-openai)
- [Limitaciones](#limitaciones-actuales)
- [Escáner de GitHub](#escáner-de-repos-de-github-segunda-herramienta)
- [Licencia](#licencia)

## Stack

- Python 3.12+
- Biblioteca estándar (análisis local sin deps pesadas)
- `requests` + `python-dotenv` (escáner GitHub)
- LLM opcional vía endpoint OpenAI-compatible (llama.cpp)
- Calidad: ruff (lint), pytest

## Arquitectura

```
repo local ──► repo_agent.scanner (files/structure)
                 │
                 ├─► detectors (stack/languages/frameworks)
                 ├─► analyzers (findings: README, tests, CI, secrets, …)
                 ├─► importance (primary + supporting files)
                 ├─► budgeting (token budget)
                 └─► context_builder (bundle para LLM)
                         │
                         ▼
                  reporter (markdown report) ──► optional LLM summary
```

Esta versión añade una mejora clave sobre la v2:

1. selecciona el archivo más importante del proyecto,
2. estima si cabe dentro del presupuesto del modelo,
3. lo incluye completo o lo resume si excede el presupuesto,
4. agrega hasta 2 archivos satélite opcionales,
5. exporta un bundle listo para pegar o enviar a un LLM.

## Qué detecta esta versión

- estructura general del repo
- vista previa del árbol de directorios
- tecnologías y frameworks detectados
- lenguajes principales por extensiones
- tipo de proyecto sugerido
- CI detectado o ausente
- README real vs README generado
- presencia de tests
- presencia de `.gitignore`
- presencia de `.env.example`
- archivos más grandes considerados
- `app.py` sobredimensionado
- rutas centralizadas en un solo archivo
- sospecha simple de secretos hardcodeados
- artefactos comprimidos dentro del repo
- contexto preliminar para LLM
- selección del archivo principal para contexto LLM
- archivos satélite opcionales dentro de presupuesto

## Salidas generadas

- `repo_diagnostic.md`
- `repo_diagnostic.json`
- `llm_project_brief.json`
- `llm_prompt.txt`
- `llm_antecedents.md`
- `llm_context_bundle.json`
- `llm_context_prompt.txt`
- `important_file_summary.md`

## Ejecución

```bash
cd repo-analyzer
python3 analyze_repo.py /ruta/a/tu/repositorio --output-dir ./output --print-report
```

O bien:

```bash
./run_demo.sh /ruta/a/tu/repositorio
```

## Ejemplo con control del presupuesto LLM

```bash
python3 analyze_repo.py ~/Documentos/atacamahub_web \
  --output-dir ./output \
  --print-report \
  --llm-max-input-tokens 24000 \
  --important-file-budget-ratio 0.35 \
  --secondary-file-budget-ratio 0.10 \
  --max-secondary-files 2
```

### Opciones adicionales

```bash
repo-analyze /ruta/al/repo --tree-depth 4 --extra-exclude "legacy,vendor"
repo-analyze /ruta/al/repo --llm-summary        # fuerza resumen LLM
repo-analyze /ruta/al/repo --no-llm-summary     # desactiva resumen LLM
```

- `--tree-depth N` — profundidad máxima del árbol de estructura en el reporte.
- `--extra-exclude a,b` — directorios adicionales a excluir del escaneo (además de los defaults).
- `--llm-summary` / `--no-llm-summary` — forzar o desactivar el resumen LLM (por defecto se genera solo si `REPO_AGENT_LLM_ENDPOINT` y `REPO_AGENT_LLM_MODEL` están definidos).

## Qué hace con el archivo principal

- detecta candidatos como `app.py`, `main.py`, `server.py`, etc.
- prioriza señales de entrypoint, rutas, render de templates o arranque del servidor
- si el archivo cabe, lo mete completo en `llm_context_bundle.json`
- si no cabe, lo resume en forma estructurada

## Cómo usar el contexto con el LLM

Toma `llm_context_prompt.txt` o `llm_context_bundle.json` y úsalo para pedir algo como:

- “redacta un README preliminar”
- “hazme antecedentes del proyecto”
- “resume el stack y la estructura actual”
- “propón quick wins y plan de refactor”
- “explica el archivo principal y sus riesgos”

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Uso

```bash
# Analizar un repo local
./run_demo.sh /ruta/al/repositorio
# o directamente:
python analyze_repo.py /ruta/al/repositorio --print-report

# Escáner de GitHub (requiere .env con GITHUB_TOKEN)
./run_scan.sh scan
```

## Tests

```bash
pytest -q
```

Cobertura (39 tests):

- `tests/test_rules.py` — reglas del escáner GitHub (`src/repo_scanner_mvp/rules.py`).
- `tests/test_repo_scanner.py` — exclusión de ruido, conteos, árbol y archivos grandes.
- `tests/test_repo_importance.py` — scoring y selección de archivo principal/satélite.
- `tests/test_repo_budgeting.py` — presupuesto de tokens.
- `tests/test_repo_context_builder.py` — resumen de archivos y payload del bundle.
- `tests/test_repo_llm_cli.py` — bundle, resumen LLM y flujo CLI.
- `tests/test_repo_fixes.py` — detección unificada de tests, README raíz y entrypoints.

Chequeos estáticos: `ruff check .` y `mypy repo_agent src`.

## CI

GitHub Actions (`.github/workflows/ci.yml`) sobre Python 3.12:

- **lint** — `ruff check .`
- **typecheck** — `mypy repo_agent src`
- **test** — `pytest -q` (31 tests)

## LLM opcional por endpoint compatible OpenAI

Si quieres que el propio MVP consulte un modelo local, por ejemplo `llama.cpp server`, exporta:

```bash
export REPO_AGENT_LLM_ENDPOINT="http://127.0.0.1:8080"
export REPO_AGENT_LLM_MODEL="qwen2.5-7b-instruct"
```

Luego ejecuta el análisis normalmente. Si el endpoint no responde, el diagnóstico base igual se genera.

## Limitaciones actuales

Este MVP todavía no:

- aplica patches automáticamente
- corre `ruff`, `pytest`, `eslint` o `semgrep`
- crea commits o PRs
- hace parsing AST profundo
- entiende reglas de negocio del proyecto

## Camino natural de mejora

### Iteración 4

- ejecutar linters y tests reales si existen
- agregar detección de dependencias y entrypoints por lenguaje
- sumar patch generator para quick wins seguros
- branch temporal y validación antes de patch

## Escáner de repos de GitHub (segunda herramienta)

Este repositorio incluye además `src/repo_scanner_mvp/`, un escáner que recorre
los repos de un owner de GitHub y genera un reporte de estado/riesgo por repo.

```bash
cp .env.example .env   # completa GITHUB_TOKEN y config
./run_scan.sh scan
```

Variables relevantes (ver `.env.example`): `GITHUB_TOKEN`, `GITHUB_OWNER`,
`GITHUB_SCAN_MODE`, `GITHUB_REPO_ALLOWLIST`, `GITHUB_API_VERSION`,
`GITHUB_API_BASE_URL`, así como la config del LLM opcional (`LLM_*`) y
`OUTPUT_DIR`/`REPORT_TIMESTAMP_OVERRIDE`.

## Licencia

MIT — ver [LICENSE](LICENSE).
