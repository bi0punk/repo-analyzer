# Changelog

Formato [Keep a Changelog](https://keepachangelog.com/es/1.1.0/) y
[SemVer](https://semver.org/lang/es/).

## [1.0.0] - 2026-11-11

Primera versión pensada para usarse desde CI y como Action.

### Añadido

- GitHub Action composite (`action.yml`): instala desde el repositorio, analiza,
  publica el informe como artefacto y expone el output `report`.
- Workflow de dogfooding `self-analysis.yml` que ejecuta la Action sobre el
  propio repo y publica el resumen.
- Imagen Docker CLI (`ghcr.io/bi0punk/repo-analyzer`) sin root.
- CI completo: calidad (ruff, mypy, vulture, bandit), tests 3.12/3.13 con
  cobertura, `pip-audit` y publicación en GHCR.
- `--version` con metadatos del paquete.
- Documentación: Action, configuración, troubleshooting y arquitectura.
- Dependabot, plantillas de issue/PR, seguridad y contribución.

### Cambiado

- El extra `dev` incluye vulture, bandit y pytest-cov para que local y CI
  ejecuten exactamente los mismos chequeos.
- Cobertura 68 % con gate del 65 %.

### Corregido

- El CI instalaba contra el Python del runner (PEP 668) y el job de tests no
  instalaba el paquete: fallaba antes de ejecutar pytest. Ahora usa venv y
  `-e ".[dev]"`.

### Seguridad

- `pip-audit` limpio en CI.
- Imagen y ejecución sin privilegios.
- Guía de scope mínimo del `GITHUB_TOKEN` en `SECURITY.md`.

## [0.1.0] - 2026-10-12

- Diagnóstico local con selección de archivo principal y satélites bajo
  presupuesto de tokens.
- Bundle de contexto y brief para LLM.
- Escáner de repos de GitHub con reporte de estado/riesgo (JSON/CSV/MD).
