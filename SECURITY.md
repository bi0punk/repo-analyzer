# Política de seguridad

## Cómo reportar

Usa **GitHub Security Advisories** o un issue privado. Incluye versión/commit,
pasos de reproducción e impacto. No adjuntes tokens.

Respuesta objetivo: acuse en 72 h y parche/mitigación en 14 días.

## Alcance

- exposición de `GITHUB_TOKEN`, `REPO_AGENT_LLM_API_KEY` o `.env`;
- lectura de archivos fuera del repositorio analizado (path traversal);
- ejecución de comandos a partir de rutas del repo;
- SSRF vía endpoints de LLM o de la API de GitHub configurables;
- dependencias con CVE.

Fuera de alcance: contenido del repositorio analizado y seguridad de GitHub o
del servidor LLM upstream.

## Recomendaciones

- Usa un PAT de solo lectura y ámbito mínimo.
- No ejecutes el analizador como root sobre repositorios no confiables.
- En la Action, fija la versión (`@v1.0.0`) si necesitas reproducibilidad.
- Mantén dependencias al día: Dependabot + `pip-audit` en CI.
