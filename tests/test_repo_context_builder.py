from repo_agent.context_builder import (
    build_file_payload,
    build_prompt_from_bundle,
    summarize_python_file,
)


def test_summarize_python_file_detects_structures():
    text = (
        "import os\n"
        "from flask import Flask\n\n"
        "class Servicio:\n"
        "    pass\n\n"
        "@app.route('/')\n"
        "def home():\n"
        "    return 'x'\n"
    )
    summary = summarize_python_file(text)
    assert any(i["code"].startswith("import os") for i in summary["imports"])
    assert any(c["signature"].startswith("class Servicio") for c in summary["classes"])
    assert any(f["signature"].startswith("def home") for f in summary["functions"])
    assert any(r["code"].startswith("@app.route") for r in summary["routes"])
    assert summary["key_snippets"]


def test_build_file_payload_full_when_fits():
    payload = build_file_payload("app.py", "x = 1\n", budget_tokens=1000)
    assert payload["included_mode"] == "full"
    assert payload["content"] == "x = 1\n"


def test_build_file_payload_summary_when_exceeds():
    content = "import os\n" + "print('line')\n" * 2000
    payload = build_file_payload("app.py", content, budget_tokens=200)
    assert payload["included_mode"] == "summary"
    assert "summary" in payload
    assert "content" not in payload


def test_build_file_payload_summary_for_unknown_suffix():
    content = "\n".join(f"line {i}" for i in range(2000))
    payload = build_file_payload("config.txt", content, budget_tokens=200)
    assert payload["included_mode"] == "summary"
    assert "preview" in payload["summary"]


def test_build_prompt_from_bundle():
    bundle = {
        "primary_file": {"path": "app.py", "included_mode": "full"},
        "secondary_files": [],
        "budget": {"max_input_tokens": 1000},
    }
    project_brief = {"repo": {"root_path": "/tmp/x"}}
    prompt = build_prompt_from_bundle(project_brief, bundle)
    assert "app.py" in prompt
    assert "quick wins" in prompt