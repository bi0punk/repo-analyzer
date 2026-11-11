"""Valida el contrato de la GitHub Action y el flujo CLI de punta a punta."""

from pathlib import Path

import yaml

from repo_agent.cli import main

ROOT = Path(__file__).resolve().parent.parent


def test_action_tiene_contrato_composite():
    action = yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))
    assert action["runs"]["using"] == "composite"
    assert action["outputs"]["report"]["value"]
    assert {"path", "output-dir", "llm-max-input-tokens"} <= set(action["inputs"])
    pasos = action["runs"]["steps"]
    assert any("repo-analyzer analyze" in str(paso.get("run", "")) for paso in pasos)


def test_analyze_genera_solo_markdown_si_no_json(tmp_path):
    out = tmp_path / "out"
    code = main(["analyze", str(ROOT), "--output-dir", str(out), "--no-json"])

    assert code == 0
    assert (out / "repo_diagnostic.md").is_file()
    assert not (out / "repo_diagnostic.json").exists()
