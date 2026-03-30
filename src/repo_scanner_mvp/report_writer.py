from __future__ import annotations

import csv
import json
from pathlib import Path

from repo_scanner_mvp.models import RepoScanResult, ScanSummary
from repo_scanner_mvp.utils import csv_safe_join, ensure_directory


class ReportWriter:
    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = ensure_directory(output_dir)

    def write_all(self, summary: ScanSummary, results: list[RepoScanResult]) -> dict[str, Path]:
        timestamp_dir = ensure_directory(self.output_dir / summary.timestamp)
        json_path = timestamp_dir / "scan_results.json"
        csv_path = timestamp_dir / "scan_results.csv"
        md_path = timestamp_dir / "scan_report.md"

        self._write_json(json_path, summary, results)
        self._write_csv(csv_path, results)
        self._write_markdown(md_path, summary, results)

        return {
            "json": json_path,
            "csv": csv_path,
            "markdown": md_path,
        }

    def _write_json(self, path: Path, summary: ScanSummary, results: list[RepoScanResult]) -> None:
        payload = {
            "summary": summary.to_dict(),
            "repositories": [result.to_dict() for result in results],
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _write_csv(self, path: Path, results: list[RepoScanResult]) -> None:
        fieldnames = [
            "full_name",
            "private",
            "archived",
            "fork",
            "language",
            "default_branch",
            "branches",
            "has_main",
            "has_master",
            "has_dev",
            "has_develop",
            "protected_main",
            "protected_default_branch",
            "primary_candidate_branch",
            "repo_status",
            "risk_level",
            "recommended_actions",
            "updated_at",
            "pushed_at",
            "llm_policy_classification",
            "llm_summary",
            "scan_errors",
            "html_url",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow(
                    {
                        "full_name": result.full_name,
                        "private": result.private,
                        "archived": result.archived,
                        "fork": result.fork,
                        "language": result.language or "",
                        "default_branch": result.default_branch or "",
                        "branches": csv_safe_join([branch.name for branch in result.branches]),
                        "has_main": result.has_main,
                        "has_master": result.has_master,
                        "has_dev": result.has_dev,
                        "has_develop": result.has_develop,
                        "protected_main": result.protected_main,
                        "protected_default_branch": result.protected_default_branch,
                        "primary_candidate_branch": result.primary_candidate_branch or "",
                        "repo_status": result.repo_status,
                        "risk_level": result.risk_level,
                        "recommended_actions": csv_safe_join(result.recommended_actions),
                        "updated_at": result.updated_at or "",
                        "pushed_at": result.pushed_at or "",
                        "llm_policy_classification": result.llm_policy_classification or "",
                        "llm_summary": result.llm_summary or "",
                        "scan_errors": csv_safe_join(result.scan_errors),
                        "html_url": result.html_url,
                    }
                )

    def _write_markdown(self, path: Path, summary: ScanSummary, results: list[RepoScanResult]) -> None:
        lines: list[str] = []
        lines.append(f"# GitHub Repository Scan Report - {summary.timestamp}")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Scan mode: `{summary.scan_mode}`")
        lines.append(f"- Owner: `{summary.owner or 'authenticated user scope'}`")
        lines.append(f"- Total repositories scanned: **{summary.total_repos}**")
        lines.append(f"- With `dev`: **{summary.total_with_dev}**")
        lines.append(f"- With `main`: **{summary.total_with_main}**")
        lines.append(f"- With protected `main`: **{summary.total_with_protected_main}**")
        lines.append("")
        lines.append("## Repo status counts")
        lines.append("")
        for key, value in summary.repo_status_counts.items():
            lines.append(f"- `{key}`: {value}")
        lines.append("")
        lines.append("## Risk counts")
        lines.append("")
        for key, value in summary.risk_counts.items():
            lines.append(f"- `{key}`: {value}")
        lines.append("")
        lines.append("## Repositories")
        lines.append("")

        for result in results:
            lines.append(f"### {result.full_name}")
            lines.append("")
            lines.append(f"- URL: {result.html_url}")
            lines.append(f"- Default branch: `{result.default_branch or 'unknown'}`")
            lines.append(f"- Branches: `{', '.join(branch.name for branch in result.branches) or 'none'}`")
            lines.append(f"- Candidate consolidation branch: `{result.primary_candidate_branch or 'unknown'}`")
            lines.append(f"- Status: `{result.repo_status}`")
            lines.append(f"- Risk: `{result.risk_level}`")
            lines.append(f"- Actions: `{', '.join(result.recommended_actions) or 'none'}`")
            if result.llm_policy_classification:
                lines.append(f"- LLM classification: `{result.llm_policy_classification}`")
            if result.llm_summary:
                lines.append(f"- LLM summary: {result.llm_summary}")
            if result.scan_errors:
                lines.append(f"- Scan errors: `{'; '.join(result.scan_errors)}`")
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")
