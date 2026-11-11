# Configuración

Precedencia: **flags de la CLI > variables de entorno > defaults**.

Hay dos flujos con configuración distinta:

- `repo-analyzer analyze` — analiza un repo local (sin red salvo LLM opcional).
- `repo-analyzer scan` — escanea los repos de una cuenta/organización de GitHub.

## Analizador local (`analyze`)

| Flag | Default | Descripción |
|---|---|---|
| `repo_path` | — | Ruta del repositorio |
| `--output-dir` | `./repo_agent_output` | Carpeta de reportes |
| `--no-json` | off | No escribir `repo_diagnostic.json` |
| `--print-report` | off | Imprimir el Markdown en consola |
| `--llm-max-input-tokens` | `24000` | Presupuesto total del contexto |
| `--important-file-budget-ratio` | `0.35` | Fracción para el archivo principal |
| `--secondary-file-budget-ratio` | `0.10` | Fracción por archivo satélite |
| `--max-secondary-files` | `2` | Satélites máximos |
| `--tree-depth` | `3` | Profundidad del árbol |
| `--extra-exclude` | vacío | Patrones extra a excluir |

Enriquecimiento con LLM local (opcional):

| Variable | Default | Descripción |
|---|---|---|
| `REPO_AGENT_LLM_ENDPOINT` | vacío | Endpoint compatible con chat completions |
| `REPO_AGENT_LLM_MODEL` | vacío | Nombre del modelo |
| `REPO_AGENT_LLM_API_KEY` | vacío | API key si el endpoint la exige |

Si el endpoint está vacío, el análisis funciona igual (solo heurísticas).

## Escáner de GitHub (`scan`)

| Variable | Default | Descripción |
|---|---|---|
| `GITHUB_TOKEN` | — | PAT con permiso de lectura |
| `GITHUB_SCAN_MODE` | `authenticated` | `authenticated` o `public` |
| `GITHUB_OWNER` | vacío | Usuario u organización |
| `GITHUB_INCLUDE_ARCHIVED` | `false` | Incluir repos archivados |
| `GITHUB_INCLUDE_FORKS` | `true` | Incluir forks |
| `GITHUB_PER_PAGE` | `100` | Tamaño de página |
| `GITHUB_MAX_REPOS` | `0` | Límite (0 = todos) |
| `GITHUB_API_VERSION` | `2022-11-28` | Cabecera de versión |
| `GITHUB_API_BASE_URL` | `https://api.github.com` | Para GitHub Enterprise |
| `GITHUB_REPO_ALLOWLIST` | vacío | Lista de repos (`:`-separado) |
| `OUTPUT_DIR` | `./outputs` | Carpeta de salida |
| `REPORT_TIMESTAMP_OVERRIDE` | vacío | Fecha fija para pruebas |

### LLM del escáner (opcional)

| Variable | Default | Descripción |
|---|---|---|
| `LLM_ENABLED` | `true` | Activa el resumen por LLM |
| `LLM_BASE_URL` | `http://localhost:8080` | Servidor llama.cpp |
| `LLM_CHAT_PATH` | `/v1/chat/completions` | Ruta de chat |
| `LLM_MODEL` | `qwen2.5-7b-instruct-q4_k_m` | Modelo |
| `LLM_TIMEOUT_SECONDS` | `60` | Timeout |
| `LLM_TEMPERATURE` | `0.1` | Temperatura |
| `LLM_MAX_TOKENS` | `700` | Tokens de salida |

## Ejemplos

### Analizar el repo actual y ver el informe

```bash
repo-analyzer analyze . --output-dir ./reports --print-report
```

### Escanear una organización sin LLM

```env
GITHUB_TOKEN=ghp_...
GITHUB_OWNER=bi0punk
LLM_ENABLED=false
OUTPUT_DIR=./outputs
```

```bash
repo-analyzer scan
```

### GitHub Enterprise

```env
GITHUB_API_BASE_URL=https://github.mi-empresa.com/api/v3
```

### Presupuesto de contexto

```bash
repo-analyzer analyze . \
  --llm-max-input-tokens 32000 \
  --important-file-budget-ratio 0.30 \
  --secondary-file-budget-ratio 0.12 \
  --max-secondary-files 3
```
