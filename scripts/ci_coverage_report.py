"""Summarize CI coverage artifacts and compare them to a default-branch baseline.

This script keeps the GitHub Actions workflow declarative by moving coverage
parsing, patch-line matching, and baseline comparison into a typed Python
utility. It consumes the backend/frontend artifacts produced in CI and emits a
Markdown summary plus a machine-readable JSON report.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_HUNK_PATTERN = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_FRONTEND_SUFFIXES = (".js", ".jsx", ".ts", ".tsx")
_REGRESSION_EPSILON = 0.0001
_UNCOVERED_LINE_PREVIEW_LIMIT = 20


@dataclass(frozen=True)
class CoverageSurface:
    """Total line coverage for one measured surface."""

    covered_lines: int
    total_lines: int
    percent: float
    baseline_percent: float | None
    delta_points: float | None
    regressed: bool


@dataclass(frozen=True)
class UncoveredLine:
    """One changed executable line that was not covered in the current run."""

    path: str
    line: int


@dataclass(frozen=True)
class PatchCoverage:
    """Coverage over changed executable lines in backend/frontend code."""

    applicable: bool
    covered_lines: int
    total_lines: int
    percent: float | None
    uncovered_lines: tuple[UncoveredLine, ...]


@dataclass(frozen=True)
class CoverageReport:
    """Full CI coverage report, including baseline deltas and patch coverage."""

    backend: CoverageSurface
    frontend: CoverageSurface
    patch: PatchCoverage
    baseline_available: bool
    total_regressed: bool


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for report generation."""

    parser = argparse.ArgumentParser(
        description=(
            "Build a GitHub-native CI coverage report from backend/frontend coverage "
            "artifacts, an optional default-branch baseline, and an optional git diff."
        )
    )
    parser.add_argument("--backend-json", type=Path, required=True)
    parser.add_argument("--frontend-summary", type=Path, required=True)
    parser.add_argument("--frontend-lcov", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--summary-md", type=Path, required=True)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--diff", type=Path)
    parser.add_argument("--baseline", type=Path)
    return parser.parse_args()


def _normalize_path(path_text: str, repo_root: Path) -> str:
    """Normalize a coverage or diff path into a repo-relative POSIX path."""

    candidate = Path(path_text)
    if candidate.is_absolute():
        resolved_root = repo_root.resolve()
        resolved_candidate = candidate.resolve()
        try:
            candidate = resolved_candidate.relative_to(resolved_root)
        except ValueError:
            candidate = resolved_candidate
    return candidate.as_posix().lstrip("./")


def _normalize_frontend_path(path_text: str, repo_root: Path) -> str:
    """Normalize frontend coverage paths so they match repo-root diff paths."""

    normalized = _normalize_path(path_text, repo_root)
    return normalized if normalized.startswith("ui/") else f"ui/{normalized}"


def _surface_from_backend(
    backend_json_path: Path, repo_root: Path
) -> tuple[CoverageSurface, dict[str, dict[int, bool]]]:
    """Load backend totals plus per-line execution status from coverage JSON."""

    payload = json.loads(backend_json_path.read_text())
    totals = payload["totals"]
    surface = CoverageSurface(
        covered_lines=int(totals["covered_lines"]),
        total_lines=int(totals["num_statements"]),
        percent=float(totals["percent_covered"]),
        baseline_percent=None,
        delta_points=None,
        regressed=False,
    )
    line_coverage: dict[str, dict[int, bool]] = {}
    for raw_path, file_payload in payload["files"].items():
        normalized_path = _normalize_path(raw_path, repo_root)
        covered_lines = {int(line) for line in file_payload.get("executed_lines", [])}
        missing_lines = {int(line) for line in file_payload.get("missing_lines", [])}
        line_coverage[normalized_path] = {
            **dict.fromkeys(covered_lines, True),
            **dict.fromkeys(missing_lines, False),
        }
    return surface, line_coverage


def _surface_from_frontend(
    frontend_summary_path: Path, frontend_lcov_path: Path, repo_root: Path
) -> tuple[CoverageSurface, dict[str, dict[int, bool]]]:
    """Load frontend totals plus per-line execution status from Vitest outputs."""

    summary_payload = json.loads(frontend_summary_path.read_text())
    totals = summary_payload["total"]["lines"]
    surface = CoverageSurface(
        covered_lines=int(totals["covered"]),
        total_lines=int(totals["total"]),
        percent=float(totals["pct"]),
        baseline_percent=None,
        delta_points=None,
        regressed=False,
    )

    line_coverage: dict[str, dict[int, bool]] = {}
    current_file: str | None = None
    current_lines: dict[int, bool] = {}
    for raw_line in frontend_lcov_path.read_text().splitlines():
        if raw_line.startswith("SF:"):
            if current_file is not None:
                line_coverage[current_file] = current_lines
            current_file = _normalize_frontend_path(raw_line.removeprefix("SF:"), repo_root)
            current_lines = {}
            continue
        if raw_line == "end_of_record":
            if current_file is not None:
                line_coverage[current_file] = current_lines
            current_file = None
            current_lines = {}
            continue
        if current_file is None or not raw_line.startswith("DA:"):
            continue
        line_number_text, hit_count_text = raw_line.removeprefix("DA:").split(",", maxsplit=1)
        current_lines[int(line_number_text)] = int(hit_count_text) > 0
    if current_file is not None:
        line_coverage[current_file] = current_lines

    return surface, line_coverage


def _load_changed_lines(diff_path: Path, repo_root: Path) -> dict[str, set[int]]:
    """Collect changed line numbers from a unified diff with zero context."""

    changed_lines: dict[str, set[int]] = {}
    current_file: str | None = None

    for raw_line in diff_path.read_text().splitlines():
        if raw_line.startswith("+++ "):
            if raw_line == "+++ /dev/null":
                current_file = None
                continue
            current_file = _normalize_path(raw_line.removeprefix("+++ b/"), repo_root)
            continue

        if current_file is None:
            continue

        match = _HUNK_PATTERN.match(raw_line)
        if match is None:
            continue

        start = int(match.group(1))
        count = int(match.group(2) or "1")
        if count <= 0:
            continue
        changed_lines.setdefault(current_file, set()).update(range(start, start + count))

    return changed_lines


def _apply_baseline(current: CoverageSurface, baseline_percent: float | None) -> CoverageSurface:
    """Attach default-branch comparison metadata to a measured surface."""

    if baseline_percent is None:
        return current
    delta_points = current.percent - baseline_percent
    regressed = delta_points < -_REGRESSION_EPSILON
    return CoverageSurface(
        covered_lines=current.covered_lines,
        total_lines=current.total_lines,
        percent=current.percent,
        baseline_percent=baseline_percent,
        delta_points=delta_points,
        regressed=regressed,
    )


def _build_patch_coverage(
    changed_lines: dict[str, set[int]],
    backend_lines: dict[str, dict[int, bool]],
    frontend_lines: dict[str, dict[int, bool]],
) -> PatchCoverage:
    """Compute coverage for changed executable lines in measured files."""

    covered_lines = 0
    total_lines = 0
    uncovered_lines: list[UncoveredLine] = []

    for path, line_numbers in sorted(changed_lines.items()):
        if path.endswith(".py"):
            line_map = backend_lines.get(path, {})
        elif path.startswith("ui/") and path.endswith(_FRONTEND_SUFFIXES):
            line_map = frontend_lines.get(path, {})
        else:
            continue

        for line_number in sorted(line_numbers):
            covered = line_map.get(line_number)
            if covered is None:
                continue
            total_lines += 1
            if covered:
                covered_lines += 1
                continue
            uncovered_lines.append(UncoveredLine(path=path, line=line_number))

    if total_lines == 0:
        return PatchCoverage(
            applicable=False,
            covered_lines=0,
            total_lines=0,
            percent=None,
            uncovered_lines=(),
        )

    return PatchCoverage(
        applicable=True,
        covered_lines=covered_lines,
        total_lines=total_lines,
        percent=(covered_lines / total_lines) * 100.0,
        uncovered_lines=tuple(uncovered_lines),
    )


def _read_baseline_percent(baseline_payload: dict[str, Any] | None, key: str) -> float | None:
    """Read a stored baseline percentage for one coverage surface."""

    if baseline_payload is None:
        return None
    section = baseline_payload.get(key)
    if not isinstance(section, dict):
        return None
    percent = section.get("percent")
    return float(percent) if percent is not None else None


def generate_report(
    *,
    backend_json_path: Path,
    frontend_summary_path: Path,
    frontend_lcov_path: Path,
    repo_root: Path,
    diff_path: Path | None,
    baseline_path: Path | None,
) -> CoverageReport:
    """Generate the combined coverage report from current artifacts and baseline."""

    backend, backend_lines = _surface_from_backend(backend_json_path, repo_root)
    frontend, frontend_lines = _surface_from_frontend(
        frontend_summary_path, frontend_lcov_path, repo_root
    )

    baseline_payload: dict[str, Any] | None = None
    if baseline_path is not None and baseline_path.exists():
        baseline_payload = json.loads(baseline_path.read_text())

    backend = _apply_baseline(backend, _read_baseline_percent(baseline_payload, "backend"))
    frontend = _apply_baseline(frontend, _read_baseline_percent(baseline_payload, "frontend"))

    patch = PatchCoverage(
        applicable=False,
        covered_lines=0,
        total_lines=0,
        percent=None,
        uncovered_lines=(),
    )
    if diff_path is not None and diff_path.exists():
        patch = _build_patch_coverage(
            _load_changed_lines(diff_path, repo_root),
            backend_lines,
            frontend_lines,
        )

    return CoverageReport(
        backend=backend,
        frontend=frontend,
        patch=patch,
        baseline_available=baseline_payload is not None,
        total_regressed=backend.regressed or frontend.regressed,
    )


def render_markdown(report: CoverageReport) -> str:
    """Render the GitHub summary Markdown for the computed coverage report."""

    lines = [
        "## Coverage Summary",
        "",
        "| Surface | Current | Baseline | Delta | Status |",
        "| --- | --- | --- | --- | --- |",
        _surface_row("Backend", report.backend),
        _surface_row("Frontend", report.frontend),
        "",
    ]

    if report.patch.applicable:
        patch_percent = f"{report.patch.percent:.2f}%"
        lines.append(
            "Patch coverage (changed executable lines): "
            f"{patch_percent} ({report.patch.covered_lines}/{report.patch.total_lines})"
        )
        if report.patch.uncovered_lines:
            lines.append("")
            lines.append("Uncovered changed lines:")
            lines.extend(
                f"- `{uncovered.path}:{uncovered.line}`"
                for uncovered in report.patch.uncovered_lines[:_UNCOVERED_LINE_PREVIEW_LIMIT]
            )
            if len(report.patch.uncovered_lines) > _UNCOVERED_LINE_PREVIEW_LIMIT:
                remaining = len(report.patch.uncovered_lines) - _UNCOVERED_LINE_PREVIEW_LIMIT
                lines.append(f"- `{remaining}` more uncovered changed lines omitted")
    else:
        lines.append("Patch coverage: n/a (no changed executable lines found in measured files)")

    if not report.baseline_available:
        lines.extend(
            [
                "",
                "Default-branch baseline unavailable. Totals were measured, but regression "
                "comparison was skipped for this run.",
            ]
        )

    return "\n".join(lines) + "\n"


def _surface_row(name: str, surface: CoverageSurface) -> str:
    """Render one Markdown table row for a single coverage surface."""

    baseline = f"{surface.baseline_percent:.2f}%" if surface.baseline_percent is not None else "n/a"
    delta = f"{surface.delta_points:+.2f} pts" if surface.delta_points is not None else "n/a"
    status = "regressed" if surface.regressed else "ok"
    current = f"{surface.percent:.2f}% ({surface.covered_lines}/{surface.total_lines})"
    return f"| {name} | {current} | {baseline} | {delta} | {status} |"


def main() -> int:
    """Generate report files from CLI arguments."""

    args = _parse_args()
    report = generate_report(
        backend_json_path=args.backend_json,
        frontend_summary_path=args.frontend_summary,
        frontend_lcov_path=args.frontend_lcov,
        repo_root=args.repo_root,
        diff_path=args.diff,
        baseline_path=args.baseline,
    )

    args.summary_md.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_md.write_text(render_markdown(report))
    args.report_json.write_text(json.dumps(asdict(report), indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
