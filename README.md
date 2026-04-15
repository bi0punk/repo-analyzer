# Repo Agent MVP v3

MVP funcional para diagnosticar repositorios locales y preparar un paquete de contexto útil para un LLM.

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
cd repo_agent_mvp_v3
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
