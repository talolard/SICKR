from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _script_path() -> Path:
    return _repo_root() / "scripts" / "ci_coverage_report.py"


def _run_script(arguments: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run the coverage report script with deterministic local arguments."""

    return subprocess.run(  # noqa: S603
        [sys.executable, str(_script_path()), *arguments],
        check=check,
        cwd=_repo_root(),
        text=True,
        capture_output=True,
    )


def _write_backend_fixture(
    repo_root: Path,
    path: Path,
    *,
    include_orphan_helper: bool = False,
) -> None:
    (repo_root / "tests").mkdir(parents=True, exist_ok=True)
    (repo_root / "tests/test_example.py").write_text(
        "def test_example() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    if include_orphan_helper:
        (repo_root / "tests/helpers.py").write_text(
            "def helper() -> bool:\n    return True\n",
            encoding="utf-8",
        )

    path.write_text(
        json.dumps(
            {
                "files": {
                    "src/ikea_agent/example.py": {
                        "summary": {
                            "covered_lines": 2,
                            "num_statements": 3,
                            "percent_covered": 66.6666666667,
                        },
                        "executed_lines": [10, 11],
                        "missing_lines": [12],
                    },
                    "tests/test_example.py": {
                        "summary": {
                            "covered_lines": 2,
                            "num_statements": 2,
                            "percent_covered": 100.0,
                        },
                        "executed_lines": [1, 2],
                        "missing_lines": [],
                    },
                }
            }
        ),
        encoding="utf-8",
    )


def _write_frontend_fixture(
    repo_root: Path,
    summary_path: Path,
    lcov_path: Path,
    *,
    include_orphan_helper: bool = False,
) -> None:
    (repo_root / "ui/src/components").mkdir(parents=True, exist_ok=True)
    (repo_root / "ui/src/test/msw").mkdir(parents=True, exist_ok=True)
    (repo_root / "ui/src/components/Demo.test.tsx").write_text(
        'import { server } from "../test/msw/server";\n'
        "describe('demo', () => {\n"
        "  it('uses the server', () => {\n"
        "    expect(server).toBeDefined();\n"
        "  });\n"
        "});\n",
        encoding="utf-8",
    )
    (repo_root / "ui/src/test/setup.ts").write_text(
        'import { server } from "./msw/server";\nbeforeAll(() => server.listen());\n',
        encoding="utf-8",
    )
    (repo_root / "ui/src/test/msw/server.ts").write_text(
        'import { handlers } from "./handlers";\n'
        "export const server = { listen: () => handlers.length };\n",
        encoding="utf-8",
    )
    (repo_root / "ui/src/test/msw/handlers.ts").write_text(
        "export const handlers = ['demo'];\n",
        encoding="utf-8",
    )
    if include_orphan_helper:
        (repo_root / "ui/src/test/orphan.ts").write_text(
            "export const orphanHelper = true;\n",
            encoding="utf-8",
        )

    summary_path.write_text(
        json.dumps(
            {
                "src/components/Demo.tsx": {
                    "lines": {"total": 3, "covered": 2, "pct": 66.6666666667},
                },
                "total": {
                    "lines": {"total": 3, "covered": 2, "pct": 66.6666666667},
                },
            }
        ),
        encoding="utf-8",
    )

    lcov_path.write_text(
        """TN:
SF:src/components/Demo.tsx
DA:4,1
DA:5,0
DA:6,1
end_of_record
""",
        encoding="utf-8",
    )


def test_ci_coverage_report_builds_four_surfaces_and_patch_coverage(tmp_path: Path) -> None:
    backend_json = tmp_path / "backend.json"
    _write_backend_fixture(tmp_path, backend_json)

    frontend_summary = tmp_path / "coverage-summary.json"
    frontend_lcov = tmp_path / "lcov.info"
    _write_frontend_fixture(tmp_path, frontend_summary, frontend_lcov)

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
""",
        encoding="utf-8",
    )

    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "backend_source": {"percent": 70.0},
                "backend_tests": {"percent": 100.0},
                "frontend_source": {"percent": 60.0},
                "frontend_tests": {"percent": 100.0},
            }
        ),
        encoding="utf-8",
    )

    summary_path = tmp_path / "summary.md"
    report_path = tmp_path / "report.json"

    result = _run_script(
        [
            "--backend-json",
            str(backend_json),
            "--frontend-summary",
            str(frontend_summary),
            "--frontend-lcov",
            str(frontend_lcov),
            "--repo-root",
            str(tmp_path),
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

    assert result.returncode == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["backend_source"]["percent"] == pytest.approx(66.6666666667)
    assert report["schema_version"] == 2
    assert report["baseline_comparable"] is True
    assert report["backend_source"]["regressed"] is True
    assert report["backend_source"]["delta_points"] == pytest.approx(-3.3333333333)
    assert report["backend_tests"]["percent"] == 100.0
    assert report["frontend_source"]["percent"] == pytest.approx(66.6666666667)
    assert report["frontend_source"]["regressed"] is False
    assert report["frontend_tests"]["percent"] == 100.0
    assert report["patch"]["applicable"] is True
    assert report["patch"]["covered_lines"] == 4
    assert report["patch"]["total_lines"] == 6
    assert report["total_regressed"] is True
    assert "`src/ikea_agent/example.py:12`" in summary_path.read_text(encoding="utf-8")
    assert "`ui/src/components/Demo.tsx:5`" in summary_path.read_text(encoding="utf-8")


def test_ci_coverage_report_handles_missing_baseline_and_non_code_diff(tmp_path: Path) -> None:
    backend_json = tmp_path / "backend.json"
    _write_backend_fixture(tmp_path, backend_json)

    frontend_summary = tmp_path / "coverage-summary.json"
    frontend_lcov = tmp_path / "lcov.info"
    _write_frontend_fixture(tmp_path, frontend_summary, frontend_lcov)

    diff_path = tmp_path / "changed.diff"
    diff_path.write_text(
        """diff --git a/docs/ci.md b/docs/ci.md
--- a/docs/ci.md
+++ b/docs/ci.md
@@ -1,0 +1,2 @@
""",
        encoding="utf-8",
    )

    summary_path = tmp_path / "summary.md"
    report_path = tmp_path / "report.json"

    result = _run_script(
        [
            "--backend-json",
            str(backend_json),
            "--frontend-summary",
            str(frontend_summary),
            "--frontend-lcov",
            str(frontend_lcov),
            "--repo-root",
            str(tmp_path),
            "--diff",
            str(diff_path),
            "--summary-md",
            str(summary_path),
            "--report-json",
            str(report_path),
        ]
    )

    assert result.returncode == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["baseline_available"] is False
    assert report["baseline_comparable"] is False
    assert report["total_regressed"] is False
    assert report["patch"]["applicable"] is False
    assert "Default-branch baseline unavailable" in summary_path.read_text(encoding="utf-8")


def test_ci_coverage_report_can_fail_on_thresholds_and_regressions(tmp_path: Path) -> None:
    backend_json = tmp_path / "backend.json"
    _write_backend_fixture(tmp_path, backend_json, include_orphan_helper=True)

    frontend_summary = tmp_path / "coverage-summary.json"
    frontend_lcov = tmp_path / "lcov.info"
    _write_frontend_fixture(tmp_path, frontend_summary, frontend_lcov, include_orphan_helper=True)

    summary_path = tmp_path / "summary.md"
    report_path = tmp_path / "report.json"
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "backend_source": {"percent": 80.0},
                "backend_tests": {"percent": 100.0},
                "frontend_source": {"percent": 80.0},
                "frontend_tests": {"percent": 100.0},
            }
        ),
        encoding="utf-8",
    )

    threshold_result = _run_script(
        [
            "--backend-json",
            str(backend_json),
            "--frontend-summary",
            str(frontend_summary),
            "--frontend-lcov",
            str(frontend_lcov),
            "--repo-root",
            str(tmp_path),
            "--summary-md",
            str(summary_path),
            "--report-json",
            str(report_path),
            "--fail-on-thresholds",
        ],
        check=False,
    )
    assert threshold_result.returncode == 2

    regression_result = _run_script(
        [
            "--backend-json",
            str(backend_json),
            "--frontend-summary",
            str(frontend_summary),
            "--frontend-lcov",
            str(frontend_lcov),
            "--repo-root",
            str(tmp_path),
            "--baseline",
            str(baseline_path),
            "--summary-md",
            str(summary_path),
            "--report-json",
            str(report_path),
            "--fail-on-regression",
        ],
        check=False,
    )
    assert regression_result.returncode == 3


def test_ci_coverage_report_skips_regression_for_incompatible_baseline(
    tmp_path: Path,
) -> None:
    backend_json = tmp_path / "backend.json"
    _write_backend_fixture(tmp_path, backend_json)

    frontend_summary = tmp_path / "coverage-summary.json"
    frontend_lcov = tmp_path / "lcov.info"
    _write_frontend_fixture(tmp_path, frontend_summary, frontend_lcov)

    summary_path = tmp_path / "summary.md"
    report_path = tmp_path / "report.json"
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "frontend_source": {"percent": 99.0},
                "backend_source": {"percent": 99.0},
            }
        ),
        encoding="utf-8",
    )

    result = _run_script(
        [
            "--backend-json",
            str(backend_json),
            "--frontend-summary",
            str(frontend_summary),
            "--frontend-lcov",
            str(frontend_lcov),
            "--repo-root",
            str(tmp_path),
            "--baseline",
            str(baseline_path),
            "--summary-md",
            str(summary_path),
            "--report-json",
            str(report_path),
            "--fail-on-regression",
        ],
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["baseline_available"] is True
    assert report["baseline_comparable"] is False
    assert report["total_regressed"] is False
    assert "older coverage schema" in summary_path.read_text(encoding="utf-8")
