# GitHub Repo Scanner MVP

MVP de la etapa 1 de escaneo para gobierno de repositorios.

Este proyecto **no modifica nada en GitHub**. Solo inspecciona repositorios, ramas, rama por defecto y el estado de protección de ramas relevantes. Además, puede enriquecer cada repositorio con una clasificación breve usando un servidor local de `llama.cpp` expuesto con API compatible OpenAI.

## Objetivo del MVP

Levantar una línea base antes de automatizar normalización de ramas.

Salida esperada por repositorio:

- ramas detectadas
- rama por defecto
- si existe `main`
- si existe `master`
- si existe `dev`
- si existe `develop`
- si `main` está protegida
- rama candidata para consolidación
- estado sugerido del repo
- acciones recomendadas para una siguiente etapa
- resumen opcional generado por LLM local

## Alcance de esta versión

Incluye:

1. Escaneo de repos del usuario autenticado, una organización o un usuario.
2. Lectura de ramas por repo.
3. Lectura de protección de rama cuando GitHub la expone para esa rama.
4. Clasificación determinística inicial.
5. Enriquecimiento opcional vía `llama.cpp` local.
6. Reportes en JSON, CSV y Markdown.

No incluye aún:

1. creación de ramas
2. merges
3. PR automáticos
4. protección automática de ramas
5. cambios sobre rama por defecto

## Arquitectura

```text
.env
  |
  v
CLI (main.py)
  |
  v
RepoScanner
  |-- GitHubClient ------> GitHub REST API
  |-- Rules Engine ------> estado / riesgo / acciones
  |-- LLMClient ---------> llama.cpp local (opcional)
  |
  v
ReportWriter
  |-- scan_results.json
  |-- scan_results.csv
  \-- scan_report.md
```

## Estructura del proyecto

```text
github_repo_scanner_mvp/
├── .env.example
├── main.py
├── pyproject.toml
├── README.md
├── requirements.txt
├── run_scan.sh
├── src/
│   └── repo_scanner_mvp/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── github_client.py
│       ├── llm_client.py
│       ├── models.py
│       ├── report_writer.py
│       ├── rules.py
│       ├── scanner.py
│       └── utils.py
└── tests/
    └── test_rules.py
```

## Requisitos

- Linux
- Python 3.10+
- token de GitHub con permisos suficientes de lectura
- servidor local `llama.cpp` ya levantado si quieres enriquecimiento LLM

## Permisos recomendados del token

Para este MVP de solo lectura, lo normal es usar un fine-grained PAT con permisos mínimos para:

- listar repositorios
- listar ramas
- leer protección de ramas cuando sea accesible

Si el token no tiene permisos suficientes para leer cierta protección, el escaneo **no se cae**: deja el error reflejado en el reporte.

## Configuración

### 1) Crear entorno

```bash
cd github_repo_scanner_mvp
cp .env.example .env
```

### 2) Editar `.env`

Ejemplo mínimo:

```env
GITHUB_TOKEN=ghp_replace_me
GITHUB_SCAN_MODE=authenticated
GITHUB_OWNER=
GITHUB_INCLUDE_ARCHIVED=false
GITHUB_INCLUDE_FORKS=true

LLM_ENABLED=true
LLM_BASE_URL=http://127.0.0.1:8080
LLM_CHAT_PATH=/v1/chat/completions
LLM_MODEL=qwen2.5-7b-instruct-q4_k_m

OUTPUT_DIR=./outputs
```

## Modos de escaneo

### A. Repos accesibles al usuario autenticado

```env
GITHUB_SCAN_MODE=authenticated
```

### B. Repos de una organización

```env
GITHUB_SCAN_MODE=org
GITHUB_OWNER=mi-organizacion
```

### C. Repos de un usuario

```env
GITHUB_SCAN_MODE=user
GITHUB_OWNER=mi-usuario
```

## Ejecución rápida

```bash
./run_scan.sh
```

## Ejecución manual

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=./src
python main.py scan
```

Con override de salida:

```bash
python main.py scan --output-dir ./salidas
```

Con otro archivo de entorno:

```bash
python main.py scan --env-file .env.prod
```

## Integración con llama.cpp local

Este proyecto espera un servidor local accesible por HTTP.

Ejemplo de uso típico de tu lado:

```bash
/path/a/llama-server \
  --model /ruta/modelo.gguf \
  --host 127.0.0.1 \
  --port 8080
```

Luego el escáner llamará a:

```text
http://127.0.0.1:8080/v1/chat/completions
```

Si el LLM falla, el escaneo continúa y registra el error por repositorio.

## Lógica de clasificación actual

La clasificación determinística es intencionalmente simple para el MVP.

Casos principales:

- `archived`: repo archivado, no se propone tocar
- `main_only`: existe `main`, pero no `dev`
- `legacy_master_layout`: existe `master`, pero no `main`
- `dev_without_main`: existe `dev`, pero no `main`
- `nearly_ready`: existe `dev` y `main`, y `main` está protegida
- `needs_normalization`: caso mixto o ambiguo

Acciones sugeridas posibles:

- `create_dev_from_primary_candidate`
- `plan_main_creation_or_master_migration`
- `create_main_after_dev_validation`
- `protect_main_branch`
- `review_default_branch_alignment`
- `validate_dev_then_pr_to_main`
- `manual_review`

## Salidas

Cada ejecución crea una carpeta con timestamp, por ejemplo:

```text
outputs/
└── 20260330T150000Z/
    ├── scan_report.md
    ├── scan_results.csv
    └── scan_results.json
```

### `scan_results.json`

Contiene:

- resumen global
- detalle completo por repo
- ramas y protecciones detectadas
- clasificación LLM si aplica

### `scan_results.csv`

Pensado para filtrar rápido en Excel, LibreOffice o pandas.

### `scan_report.md`

Resumen legible para revisión humana.

## Siguiente etapa prevista

Esta base queda lista para crecer a una etapa 2 con acciones controladas:

1. crear `dev` cuando falte
2. definir rama candidata de consolidación
3. abrir PR `dev -> main`
4. proteger `main`
5. registrar cambios y evidencias

## Hardening recomendado para la siguiente iteración

1. caché local de respuestas GitHub
2. rate-limit awareness más explícito
3. soporte GitHub App además de PAT
4. lectura de GitHub Actions y environments
5. detector de repos experimentales vs productivos
6. estrategia de aprobación humana antes de ejecutar cambios
7. pruebas unitarias y de integración más amplias

## Notas operativas

- El proyecto está hecho para Linux.
- No hace clones de repositorios en esta etapa.
- No altera ramas ni crea PR.
- Si un endpoint devuelve 403 o 404, eso queda documentado y el proceso sigue.

## Comando recomendado para partir

```bash
cp .env.example .env
nano .env
./run_scan.sh
```
