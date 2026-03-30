from __future__ import annotations

import argparse
import sys
from pathlib import Path

from repo_scanner_mvp.config import load_config, validate_config
from repo_scanner_mvp.report_writer import ReportWriter
from repo_scanner_mvp.scanner import RepoScanner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-scanner-mvp",
        description="Scan GitHub repositories and generate baseline governance reports.",
    )
    parser.add_argument("command", choices=["scan"], help="Command to execute")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory. If omitted, OUTPUT_DIR from .env is used.",
    )
    return parser


def run_scan(env_file: str, output_dir: str | None) -> int:
    config = load_config(env_file=env_file)
    if output_dir:
        config.output_dir = output_dir
    validate_config(config)

    scanner = RepoScanner(config)
    summary, results = scanner.scan()

    writer = ReportWriter(Path(config.output_dir))
    paths = writer.write_all(summary, results)

    print(f"[OK] Repositories scanned: {summary.total_repos}")
    print(f"[OK] Output JSON: {paths['json']}")
    print(f"[OK] Output CSV: {paths['csv']}")
    print(f"[OK] Output Markdown: {paths['markdown']}")
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "scan":
            raise SystemExit(run_scan(env_file=args.env_file, output_dir=args.output_dir))
        raise SystemExit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
