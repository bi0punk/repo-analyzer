from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RepoFacts:
    root_path: str
    total_files: int = 0
    total_dirs: int = 0
    root_files_count: int = 0
    technologies: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    ci_systems: list[str] = field(default_factory=list)
    project_type: str = "unknown"
    project_summary: str = ""
    has_readme: bool = False
    readme_status: str = "missing"
    readme_path: str | None = None
    has_tests: bool = False
    has_gitignore: bool = False
    has_docker: bool = False
    has_env_example: bool = False
    has_templates_dir: bool = False
    has_static_dir: bool = False
    route_count: int = 0
    main_languages: list[str] = field(default_factory=list)
    file_extension_counts: dict[str, int] = field(default_factory=dict)
    largest_files: list[dict[str, object]] = field(default_factory=list)
    directory_tree_preview: str = ""
    notable_entrypoints: list[str] = field(default_factory=list)
    noise_files_excluded: int = 0
    scan_notes: list[str] = field(default_factory=list)


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    summary: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass
class Finding:
    id: str
    title: str
    category: str
    description: str
    evidence: list[str] = field(default_factory=list)
    affected_files: list[str] = field(default_factory=list)
    urgency: int = 3
    impact: int = 3
    ease: int = 3
    risk: int = 2
    confidence: int = 4
    estimated_hours: float = 1.0
    patchable: bool = False
    suggested_action: str = ""
    validation_steps: list[str] = field(default_factory=list)
    priority_score: float = 0.0

    def compute_score(self) -> float:
        score = (
            0.30 * self.urgency +
            0.25 * self.impact +
            0.20 * self.ease +
            0.15 * self.confidence -
            0.10 * self.risk
        )
        self.priority_score = round(score, 3)
        return self.priority_score

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class AgentState:
    repo_facts: RepoFacts | None = None
    tool_results: list[ToolResult] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    llm_summary: str | None = None
    llm_project_brief: dict[str, Any] | None = None
    llm_context_bundle: dict[str, Any] | None = None
    final_report_markdown: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "repo_facts": asdict(self.repo_facts) if self.repo_facts else None,
            "tool_results": [asdict(t) for t in self.tool_results],
            "findings": [f.to_dict() for f in self.findings],
            "llm_summary": self.llm_summary,
            "llm_project_brief": self.llm_project_brief,
            "llm_context_bundle": self.llm_context_bundle,
            "final_report_markdown": self.final_report_markdown,
        }
