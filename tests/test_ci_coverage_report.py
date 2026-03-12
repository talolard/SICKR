from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script_path() -> Path:
    return _repo_root() / "scripts" / "ci_coverage_report.py"


def _run_script(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """Run the coverage report script with deterministic local arguments."""

    return subprocess.run(  # noqa: S603
        [sys.executable, str(_script_path()), *arguments],
        check=True,
        cwd=_repo_root(),
        text=True,
        capture_output=True,
    )


def test_ci_coverage_report_builds_totals_and_patch_coverage(tmp_path: Path) -> None:
    backend_json = tmp_path / "backend.json"
    backend_json.write_text(
        json.dumps(
            {
                "totals": {
                    "covered_lines": 8,
                    "num_statements": 10,
                    "percent_covered": 80.0,
                },
                "files": {
                    "src/ikea_agent/example.py": {
                        "executed_lines": [10, 11],
                        "missing_lines": [12],
                    }
                },
            }
        )
    )

    frontend_summary = tmp_path / "coverage-summary.json"
    frontend_summary.write_text(
        json.dumps(
            {
                "total": {
                    "lines": {
                        "total": 4,
                        "covered": 3,
                        "pct": 75.0,
                    }
                }
            }
        )
    )

    frontend_lcov = tmp_path / "lcov.info"
    frontend_lcov.write_text(
        """TN:
SF:src/components/Demo.tsx
DA:4,1
DA:5,0
DA:6,1
end_of_record
"""
    )

    diff_path = tmp_path / "changed.diff"
    diff_path.write_text(
        """diff --git a/src/ikea_agent/example.py b/src/ikea_agent/example.py
--- a/src/ikea_agent/example.py
+++ b/src/ikea_agent/example.py
@@ -10,0 +10,3 @@
diff --git a/ui/src/components/Demo.tsx b/ui/src/components/Demo.tsx
--- a/ui/src/components/Demo.tsx
+++ b/ui/src/components/Demo.tsx
@@ -4,0 +4,3 @@
"""
    )

    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "backend": {"percent": 82.0},
                "frontend": {"percent": 74.0},
            }
        )
    )

    summary_path = tmp_path / "summary.md"
    report_path = tmp_path / "report.json"

    _run_script(
        [
            "--backend-json",
            str(backend_json),
            "--frontend-summary",
            str(frontend_summary),
            "--frontend-lcov",
            str(frontend_lcov),
            "--repo-root",
            str(_repo_root()),
            "--diff",
            str(diff_path),
            "--baseline",
            str(baseline_path),
            "--summary-md",
            str(summary_path),
            "--report-json",
            str(report_path),
        ]
    )

    report = json.loads(report_path.read_text())

    assert report["backend"]["percent"] == 80.0
    assert report["backend"]["regressed"] is True
    assert report["backend"]["delta_points"] == -2.0
    assert report["frontend"]["percent"] == 75.0
    assert report["frontend"]["regressed"] is False
    assert report["patch"]["applicable"] is True
    assert report["patch"]["covered_lines"] == 4
    assert report["patch"]["total_lines"] == 6
    assert report["total_regressed"] is True
    assert "`src/ikea_agent/example.py:12`" in summary_path.read_text()
    assert "`ui/src/components/Demo.tsx:5`" in summary_path.read_text()


def test_ci_coverage_report_handles_missing_baseline_and_non_code_diff(tmp_path: Path) -> None:
    backend_json = tmp_path / "backend.json"
    backend_json.write_text(
        json.dumps(
            {
                "totals": {
                    "covered_lines": 5,
                    "num_statements": 5,
                    "percent_covered": 100.0,
                },
                "files": {},
            }
        )
    )

    frontend_summary = tmp_path / "coverage-summary.json"
    frontend_summary.write_text(
        json.dumps(
            {
                "total": {
                    "lines": {
                        "total": 2,
                        "covered": 2,
                        "pct": 100.0,
                    }
                }
            }
        )
    )

    frontend_lcov = tmp_path / "lcov.info"
    frontend_lcov.write_text("")

    diff_path = tmp_path / "changed.diff"
    diff_path.write_text(
        """diff --git a/docs/ci.md b/docs/ci.md
--- a/docs/ci.md
+++ b/docs/ci.md
@@ -1,0 +1,2 @@
"""
    )

    summary_path = tmp_path / "summary.md"
    report_path = tmp_path / "report.json"

    _run_script(
        [
            "--backend-json",
            str(backend_json),
            "--frontend-summary",
            str(frontend_summary),
            "--frontend-lcov",
            str(frontend_lcov),
            "--repo-root",
            str(_repo_root()),
            "--diff",
            str(diff_path),
            "--summary-md",
            str(summary_path),
            "--report-json",
            str(report_path),
        ]
    )

    report = json.loads(report_path.read_text())

    assert report["baseline_available"] is False
    assert report["total_regressed"] is False
    assert report["patch"]["applicable"] is False
    assert "Default-branch baseline unavailable" in summary_path.read_text()
