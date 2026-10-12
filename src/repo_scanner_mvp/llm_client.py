from __future__ import annotations

from textwrap import dedent

from repo_agent.llm import chat_completion
from repo_scanner_mvp.config import LLMConfig
from repo_scanner_mvp.models import RepoScanResult


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def enrich_repo(self, repo: RepoScanResult) -> tuple[str | None, str | None]:
        if not self.config.enabled:
            return (None, None)

        prompt = dedent(
            f"""
            Eres un analista técnico de gobierno de repositorios.
            Resume este repositorio y clasifícalo brevemente para una futura normalización de ramas.

            Repo: {repo.full_name}
            Descripción: {repo.description or "sin descripción"}
            Lenguaje principal: {repo.language or "desconocido"}
            Rama por defecto: {repo.default_branch or "desconocida"}
            Ramas: {", ".join(branch.name for branch in repo.branches) or "sin ramas"}
            Tiene main: {repo.has_main}
            Tiene master: {repo.has_master}
            Tiene dev: {repo.has_dev}
            Tiene develop: {repo.has_develop}
            main protegida: {repo.protected_main}
            Estado determinístico actual: {repo.repo_status}
            Riesgo: {repo.risk_level}
            Acciones sugeridas: {", ".join(repo.recommended_actions) or "ninguna"}

            Devuelve exactamente este formato:
            CLASSIFICATION: <una etiqueta corta>
            SUMMARY: <máximo 90 palabras>
            """
        ).strip()

        messages = [
            {"role": "system", "content": "Responde en español, conciso y técnico."},
            {"role": "user", "content": prompt},
        ]

        try:
            content = chat_completion(
                url=f"{self.config.base_url}{self.config.chat_path}",
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            return (None, f"llm_error: {exc}")

        classification = None
        summary = None
        for line in content.splitlines():
            if line.startswith("CLASSIFICATION:"):
                classification = line.split(":", 1)[1].strip()
            elif line.startswith("SUMMARY:"):
                summary = line.split(":", 1)[1].strip()

        return (summary, classification or "unspecified")
