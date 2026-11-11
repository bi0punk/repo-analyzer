# GitHub Action

La acción es **composite**: instala el paquete desde `github.action_path`, corre
el análisis y sube el resultado como artefacto. No requiere publicar en PyPI.

## Uso mínimo

```yaml
name: Analizar repositorio
on: [push]

permissions:
  contents: read

jobs:
  analyzer:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: bi0punk/repo-analyzer@v1
```

Genera `repo-analyzer-output/` con `repo_diagnostic.md` y lo sube como artefacto
`repo-analyzer-report`.

## Inputs

| Input | Default | Descripción |
|---|---|---|
| `path` | `.` | Ruta del repositorio a analizar |
| `output-dir` | `repo-analyzer-output` | Carpeta de reportes |
| `llm-max-input-tokens` | `24000` | Presupuesto de tokens del bundle |
| `upload-artifact` | `true` | Subir el resultado como artefacto |

## Outputs

| Output | Descripción |
|---|---|
| `report` | Ruta al `repo_diagnostic.md` generado |

## Ejemplo con hallazgos en el summary

```yaml
- uses: bi0punk/repo-analyzer@v1
  id: analyzer
  with:
    path: .
    output-dir: reports
    llm-max-input-tokens: "32000"

- name: Resumen
  run: |
    echo "### Repo Analyzer" >> "$GITHUB_STEP_SUMMARY"
    head -n 30 "${{ steps.analyzer.outputs.report }}" >> "$GITHUB_STEP_SUMMARY"
```

## Qué genera

| Archivo | Contenido |
|---|---|
| `repo_diagnostic.md` | Informe legible: stack, estructura, riesgos, recomendaciones |
| `repo_diagnostic.json` | Mismo informe estructurado |
| `llm_project_brief.json` / `llm_prompt.txt` | Brief para un LLM |
| `llm_context_bundle.json` / `llm_context_prompt.txt` | Contexto con archivos priorizados |
| `important_file_summary.md` | Resumen de los archivos seleccionados |

## Coste y límites

- No descarga modelos ni llama a un LLM: solo prepara el contexto.
- El presupuesto de tokens controla cuántos archivos se incluyen.
- Con repos grandes, usa `--extra-exclude` (CLI) para omitir vendors.

## Versionado

- `@v1` apunta a la última 1.x (se mueve con cada release menor/patch).
- Para fijar, usa el tag exacto (`@v1.0.0`) o el SHA del commit.
