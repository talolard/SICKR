"""Summarize coverage artifacts, enforce staged thresholds, and compare baselines."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from coverage_thresholds import (
    SURFACE_BY_KEY,
    classify_backend_path,
    classify_frontend_path,
)

_HUNK_PATTERN = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_FRONTEND_SUFFIXES = (".js", ".jsx", ".ts", ".tsx")
_FULL_COVERAGE_PERCENT = 100.0
_REGRESSION_EPSILON = 0.0001
_UNCOVERED_LINE_PREVIEW_LIMIT = 20
_FILE_PREVIEW_LIMIT = 10
_FRONTEND_TEST_IMPORT_PATTERN = re.compile(
    r"""(?x)
    ^\s*
    (?:
        import\s+(?:[^"'()]*?\s+from\s+)?["'](?P<static>[^"']+)["']
        |
        export\s+(?:[^"'()]*?\s+from\s+)?["'](?P<reexport>[^"']+)["']
        |
        import\(\s*["'](?P<dynamic>[^"']+)["']\s*\)
    )
    """
)
_FRONTEND_TEST_FILE_PATTERNS = ("ui/src/**/*.test.ts", "ui/src/**/*.test.tsx")
_FRONTEND_TEST_HELPER_PATTERNS = ("ui/src/test/**/*.ts", "ui/src/test/**/*.tsx")
_FRONTEND_TEST_SETUP_NAMES = {"setup.ts", "setup.tsx"}
_REPORT_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class FileCoverage:
    """Coverage summary for one file in one surface."""

    path: str
    covered_lines: int
    total_lines: int
    percent: float


@dataclass(frozen=True)
class CoverageSurface:
    """Line coverage for one named source or test surface."""

    covered_lines: int
    total_lines: int
    percent: float
    threshold_percent: float
    threshold_failed: bool
    baseline_percent: float | None
    delta_points: float | None
    regressed: bool
    file_preview: tuple[FileCoverage, ...]


@dataclass(frozen=True)
class UncoveredLine:
    """One changed executable source line that was not covered in the current run."""

    path: str
    line: int


@dataclass(frozen=True)
class PatchCoverage:
    """Coverage over changed executable lines in measured source files."""

    applicable: bool
    covered_lines: int
    total_lines: int
    percent: float | None
    uncovered_lines: tuple[UncoveredLine, ...]


@dataclass(frozen=True)
class CoverageReport:
    """Full coverage report, including thresholds and baseline deltas."""

    schema_version: int
    backend_source: CoverageSurface
    backend_tests: CoverageSurface
    frontend_source: CoverageSurface
    frontend_tests: CoverageSurface
    patch: PatchCoverage
    baseline_available: bool
    baseline_comparable: bool
    total_regressed: bool
    threshold_failed: bool


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a coverage report from backend/frontend artifacts, optional baseline "
            "data, and an optional git diff. Can also fail the process when thresholds "
            "or baseline regressions are violated."
        )
    )
    parser.add_argument("--backend-json", type=Path)
    parser.add_argument("--frontend-summary", type=Path)
    parser.add_argument("--frontend-lcov", type=Path)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--summary-md", type=Path, required=True)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--diff", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--fail-on-thresholds", action="store_true")
    parser.add_argument("--fail-on-regression", action="store_true")
    return parser.parse_args()


def _normalize_path(path_text: str, repo_root: Path) -> str:
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
    normalized = _normalize_path(path_text, repo_root)
    return normalized if normalized.startswith("ui/") else f"ui/{normalized}"


def _empty_surface(surface_key: str) -> CoverageSurface:
    config = SURFACE_BY_KEY[surface_key]
    return CoverageSurface(
        covered_lines=0,
        total_lines=0,
        percent=_FULL_COVERAGE_PERCENT,
        threshold_percent=config.threshold_percent,
        threshold_failed=False,
        baseline_percent=None,
        delta_points=None,
        regressed=False,
        file_preview=(),
    )


def _surface_from_files(
    surface_key: str,
    files: list[FileCoverage],
) -> CoverageSurface:
    config = SURFACE_BY_KEY[surface_key]
    if not files:
        return _empty_surface(surface_key)

    covered_lines = sum(file.covered_lines for file in files)
    total_lines = sum(file.total_lines for file in files)
    percent = (
        _FULL_COVERAGE_PERCENT
        if total_lines == 0
        else (covered_lines / total_lines) * _FULL_COVERAGE_PERCENT
    )
    preview = tuple(
        sorted(
            (file for file in files if file.percent < _FULL_COVERAGE_PERCENT),
            key=lambda item: (item.percent, -item.total_lines, item.path),
        )[:_FILE_PREVIEW_LIMIT]
    )
    return CoverageSurface(
        covered_lines=covered_lines,
        total_lines=total_lines,
        percent=percent,
        threshold_percent=config.threshold_percent,
        threshold_failed=percent + _REGRESSION_EPSILON < config.threshold_percent,
        baseline_percent=None,
        delta_points=None,
        regressed=False,
        file_preview=preview,
    )


def _load_backend(
    backend_json_path: Path, repo_root: Path
) -> tuple[dict[str, CoverageSurface], dict[str, dict[int, bool]]]:
    payload = json.loads(backend_json_path.read_text())
    files_by_surface: dict[str, list[FileCoverage]] = {"backend_source": []}
    backend_test_payloads: dict[str, dict[str, Any]] = {}
    source_line_coverage: dict[str, dict[int, bool]] = {}

    for raw_path, file_payload in payload["files"].items():
        normalized_path = _normalize_path(raw_path, repo_root)
        surface_key = classify_backend_path(normalized_path)
        if surface_key is None:
            continue

        summary = file_payload["summary"]
        file_coverage = FileCoverage(
            path=normalized_path,
            covered_lines=int(summary["covered_lines"]),
            total_lines=int(summary["num_statements"]),
            percent=float(summary["percent_covered"]),
        )
        if surface_key == "backend_source":
            files_by_surface["backend_source"].append(file_coverage)
        else:
            backend_test_payloads[normalized_path] = file_payload

        if surface_key == "backend_source":
            covered_lines = {int(line) for line in file_payload.get("executed_lines", [])}
            missing_lines = {int(line) for line in file_payload.get("missing_lines", [])}
            source_line_coverage[normalized_path] = {
                **dict.fromkeys(covered_lines, True),
                **dict.fromkeys(missing_lines, False),
            }

    return (
        {
            "backend_source": _surface_from_files(
                "backend_source", files_by_surface["backend_source"]
            ),
            "backend_tests": _build_backend_test_surface(repo_root, backend_test_payloads),
        },
        source_line_coverage,
    )


def _build_backend_test_surface(
    repo_root: Path,
    backend_test_payloads: dict[str, dict[str, Any]],
) -> CoverageSurface:
    """Build backend test execution coverage from discovered pytest files."""

    files: list[FileCoverage] = []
    for path in sorted(repo_root.glob("tests/**/*.py")):
        if not path.is_file():
            continue
        normalized_path = path.resolve().relative_to(repo_root.resolve()).as_posix()
        payload = backend_test_payloads.get(normalized_path)
        if payload is None:
            covered = False
        else:
            summary = payload["summary"]
            covered = (
                int(summary["num_statements"]) == 0
                or int(summary["covered_lines"]) > 0
                or bool(payload.get("executed_lines"))
            )
        files.append(
            FileCoverage(
                path=normalized_path,
                covered_lines=1 if covered else 0,
                total_lines=1,
                percent=_FULL_COVERAGE_PERCENT if covered else 0.0,
            )
        )
    return _surface_from_files("backend_tests", files)


def _load_frontend_summary_files(
    summary_payload: dict[str, Any],
    repo_root: Path,
) -> list[FileCoverage]:
    """Collect frontend source file summaries from Vitest coverage output."""

    files: list[FileCoverage] = []
    for raw_path, file_payload in summary_payload.items():
        if raw_path == "total":
            continue
        normalized_path = _normalize_frontend_path(raw_path, repo_root)
        if classify_frontend_path(normalized_path) != "frontend_source":
            continue
        lines = file_payload["lines"]
        files.append(
            FileCoverage(
                path=normalized_path,
                covered_lines=int(lines["covered"]),
                total_lines=int(lines["total"]),
                percent=float(lines["pct"]),
            )
        )
    return files


def _load_frontend_source_lines(
    frontend_lcov_path: Path,
    repo_root: Path,
) -> dict[str, dict[int, bool]]:
    """Collect executable frontend source line coverage from LCOV data."""

    source_line_coverage: dict[str, dict[int, bool]] = {}
    current_file: str | None = None
    current_lines: dict[int, bool] = {}

    for raw_line in frontend_lcov_path.read_text().splitlines():
        if raw_line.startswith("SF:"):
            _commit_frontend_source_lines(source_line_coverage, current_file, current_lines)
            current_file = _normalize_frontend_path(raw_line.removeprefix("SF:"), repo_root)
            current_lines = {}
            continue
        if raw_line == "end_of_record":
            _commit_frontend_source_lines(source_line_coverage, current_file, current_lines)
            current_file = None
            current_lines = {}
            continue
        if current_file is None or not raw_line.startswith("DA:"):
            continue
        line_number_text, hit_count_text = raw_line.removeprefix("DA:").split(",", maxsplit=1)
        if classify_frontend_path(current_file) != "frontend_source":
            continue
        current_lines[int(line_number_text)] = int(hit_count_text) > 0

    _commit_frontend_source_lines(source_line_coverage, current_file, current_lines)
    return source_line_coverage


def _commit_frontend_source_lines(
    source_line_coverage: dict[str, dict[int, bool]],
    current_file: str | None,
    current_lines: dict[int, bool],
) -> None:
    """Store one frontend source line-coverage record if it is in the measured surface."""

    if current_file is None or classify_frontend_path(current_file) != "frontend_source":
        return
    source_line_coverage[current_file] = current_lines


def _load_frontend(
    frontend_summary_path: Path,
    frontend_lcov_path: Path,
    repo_root: Path,
) -> tuple[dict[str, CoverageSurface], dict[str, dict[int, bool]]]:
    """Load frontend source coverage data from Vitest summary and LCOV outputs."""

    summary_payload = json.loads(frontend_summary_path.read_text())
    source_files = _load_frontend_summary_files(summary_payload, repo_root)
    source_line_coverage = _load_frontend_source_lines(frontend_lcov_path, repo_root)
    return (
        {"frontend_source": _surface_from_files("frontend_source", source_files)},
        source_line_coverage,
    )


def _iter_frontend_test_files(repo_root: Path, patterns: tuple[str, ...]) -> set[str]:
    """Discover frontend unit-test or helper files under the configured repo root."""

    files: set[str] = set()
    resolved_root = repo_root.resolve()
    for pattern in patterns:
        files.update(
            path.resolve().relative_to(resolved_root).as_posix()
            for path in repo_root.glob(pattern)
            if path.is_file()
        )
    return files


def _resolve_frontend_test_import(repo_root: Path, from_path: str, specifier: str) -> str | None:
    """Resolve one relative frontend test/helper import back to a tracked file."""

    if not specifier.startswith("."):
        return None

    origin = repo_root / from_path
    base = (origin.parent / specifier).resolve()
    candidates = [base]
    if base.suffix == "":
        candidates.extend(base.with_suffix(suffix) for suffix in _FRONTEND_SUFFIXES)
        candidates.extend(base / f"index{suffix}" for suffix in _FRONTEND_SUFFIXES)

    resolved_root = repo_root.resolve()
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            relative = candidate.relative_to(resolved_root).as_posix()
        except ValueError:
            continue
        if classify_frontend_path(relative) == "frontend_tests":
            return relative
    return None


def _parse_frontend_test_imports(repo_root: Path, path: str) -> set[str]:
    """Parse relative imports between frontend test files and helpers."""

    imports: set[str] = set()
    for line in (repo_root / path).read_text(encoding="utf-8").splitlines():
        match = _FRONTEND_TEST_IMPORT_PATTERN.match(line)
        if match is None:
            continue
        specifier = next(value for value in match.groupdict().values() if value is not None)
        resolved = _resolve_frontend_test_import(repo_root, path, specifier)
        if resolved is not None:
            imports.add(resolved)
    return imports


def _build_frontend_test_surface(repo_root: Path) -> CoverageSurface:
    """Build frontend test execution coverage from unit-test files and helpers."""

    test_files = _iter_frontend_test_files(repo_root, _FRONTEND_TEST_FILE_PATTERNS)
    helper_files = _iter_frontend_test_files(repo_root, _FRONTEND_TEST_HELPER_PATTERNS)
    roots = set(test_files)
    roots.update(path for path in helper_files if Path(path).name in _FRONTEND_TEST_SETUP_NAMES)

    adjacency = {
        path: _parse_frontend_test_imports(repo_root, path)
        for path in sorted(test_files | helper_files)
    }
    reachable = set(roots)
    stack = list(roots)
    while stack:
        current = stack.pop()
        for target in adjacency.get(current, set()):
            if target in reachable:
                continue
            reachable.add(target)
            stack.append(target)

    files: list[FileCoverage] = [
        FileCoverage(
            path=path,
            covered_lines=1,
            total_lines=1,
            percent=_FULL_COVERAGE_PERCENT,
        )
        for path in sorted(test_files)
    ]
    for path in sorted(helper_files):
        covered = path in reachable
        files.append(
            FileCoverage(
                path=path,
                covered_lines=1 if covered else 0,
                total_lines=1,
                percent=_FULL_COVERAGE_PERCENT if covered else 0.0,
            )
        )
    return _surface_from_files("frontend_tests", files)


def _load_changed_lines(diff_path: Path, repo_root: Path) -> dict[str, set[int]]:
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


def _read_baseline_percent(baseline_payload: dict[str, Any] | None, key: str) -> float | None:
    if baseline_payload is None:
        return None
    section = baseline_payload.get(key)
    if not isinstance(section, dict):
        fallback_key = {
            "backend_source": "backend",
            "frontend_source": "frontend",
        }.get(key)
        if fallback_key is None:
            return None
        section = baseline_payload.get(fallback_key)
        if not isinstance(section, dict):
            return None
    percent = section.get("percent")
    return float(percent) if percent is not None else None


def _baseline_is_comparable(baseline_payload: dict[str, Any] | None) -> bool:
    """Return whether a saved baseline was produced by the same measurement schema."""

    if baseline_payload is None:
        return False
    return baseline_payload.get("schema_version") == _REPORT_SCHEMA_VERSION


def _apply_baseline(
    surface_key: str, current: CoverageSurface, baseline_percent: float | None
) -> CoverageSurface:
    if baseline_percent is None:
        return current
    delta_points = current.percent - baseline_percent
    regressed = delta_points < -_REGRESSION_EPSILON
    return CoverageSurface(
        covered_lines=current.covered_lines,
        total_lines=current.total_lines,
        percent=current.percent,
        threshold_percent=current.threshold_percent,
        threshold_failed=current.threshold_failed,
        baseline_percent=baseline_percent,
        delta_points=delta_points,
        regressed=regressed if SURFACE_BY_KEY[surface_key].compare_to_baseline else False,
        file_preview=current.file_preview,
    )


def _build_patch_coverage(
    changed_lines: dict[str, set[int]],
    backend_source_lines: dict[str, dict[int, bool]],
    frontend_source_lines: dict[str, dict[int, bool]],
) -> PatchCoverage:
    covered_lines = 0
    total_lines = 0
    uncovered_lines: list[UncoveredLine] = []

    for path, line_numbers in sorted(changed_lines.items()):
        if path.endswith(".py"):
            line_map = backend_source_lines.get(path, {})
        elif path.startswith("ui/") and path.endswith(_FRONTEND_SUFFIXES):
            line_map = frontend_source_lines.get(path, {})
        else:
            continue

        for line_number in sorted(line_numbers):
            covered = line_map.get(line_number)
            if covered is None:
                continue
            total_lines += 1
            if covered:
                covered_lines += 1
            else:
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


def generate_report(
    *,
    repo_root: Path,
    backend_json_path: Path | None,
    frontend_summary_path: Path | None,
    frontend_lcov_path: Path | None,
    diff_path: Path | None,
    baseline_path: Path | None,
) -> CoverageReport:
    """Build the combined coverage report consumed by CI and local `make coverage`."""

    backend_surfaces: dict[str, CoverageSurface] = {
        "backend_source": _empty_surface("backend_source"),
        "backend_tests": _empty_surface("backend_tests"),
    }
    frontend_surfaces: dict[str, CoverageSurface] = {
        "frontend_source": _empty_surface("frontend_source"),
        "frontend_tests": _empty_surface("frontend_tests"),
    }
    backend_source_lines: dict[str, dict[int, bool]] = {}
    frontend_source_lines: dict[str, dict[int, bool]] = {}

    if backend_json_path is not None:
        backend_surfaces, backend_source_lines = _load_backend(backend_json_path, repo_root)
    if frontend_summary_path is not None and frontend_lcov_path is not None:
        frontend_surfaces, frontend_source_lines = _load_frontend(
            frontend_summary_path,
            frontend_lcov_path,
            repo_root,
        )
        frontend_surfaces["frontend_tests"] = _build_frontend_test_surface(repo_root)

    baseline_payload: dict[str, Any] | None = None
    if baseline_path is not None and baseline_path.exists():
        baseline_payload = json.loads(baseline_path.read_text())

    baseline_comparable = _baseline_is_comparable(baseline_payload)
    comparable_baseline = baseline_payload if baseline_comparable else None

    backend_source = _apply_baseline(
        "backend_source",
        backend_surfaces["backend_source"],
        _read_baseline_percent(comparable_baseline, "backend_source"),
    )
    backend_tests = _apply_baseline(
        "backend_tests",
        backend_surfaces["backend_tests"],
        _read_baseline_percent(comparable_baseline, "backend_tests"),
    )
    frontend_source = _apply_baseline(
        "frontend_source",
        frontend_surfaces["frontend_source"],
        _read_baseline_percent(comparable_baseline, "frontend_source"),
    )
    frontend_tests = _apply_baseline(
        "frontend_tests",
        frontend_surfaces["frontend_tests"],
        _read_baseline_percent(comparable_baseline, "frontend_tests"),
    )

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
            backend_source_lines,
            frontend_source_lines,
        )

    surfaces = (backend_source, backend_tests, frontend_source, frontend_tests)
    return CoverageReport(
        schema_version=_REPORT_SCHEMA_VERSION,
        backend_source=backend_source,
        backend_tests=backend_tests,
        frontend_source=frontend_source,
        frontend_tests=frontend_tests,
        patch=patch,
        baseline_available=baseline_payload is not None,
        baseline_comparable=baseline_comparable,
        total_regressed=baseline_comparable and any(surface.regressed for surface in surfaces),
        threshold_failed=any(surface.threshold_failed for surface in surfaces),
    )


def _surface_row(label: str, surface: CoverageSurface) -> str:
    baseline = f"{surface.baseline_percent:.2f}%" if surface.baseline_percent is not None else "n/a"
    delta = f"{surface.delta_points:+.2f} pts" if surface.delta_points is not None else "n/a"
    status_parts = []
    if surface.threshold_failed:
        status_parts.append("below-threshold")
    if surface.regressed:
        status_parts.append("regressed")
    if not status_parts:
        status_parts.append("ok")
    current = f"{surface.percent:.2f}% ({surface.covered_lines}/{surface.total_lines})"
    threshold = f"{surface.threshold_percent:.2f}%"
    return (
        f"| {label} | {current} | {threshold} | {baseline} | {delta} | {', '.join(status_parts)} |"
    )


def _append_surface_preview(lines: list[str], title: str, surface: CoverageSurface) -> None:
    if not surface.file_preview:
        return
    lines.extend(["", f"### {title}", ""])
    lines.extend(
        f"- `{file.path}`: {file.percent:.2f}% ({file.covered_lines}/{file.total_lines})"
        for file in surface.file_preview
    )


def render_markdown(report: CoverageReport) -> str:
    """Render one Markdown summary for GitHub step output and local feedback."""

    lines = [
        "## Coverage Summary",
        "",
        "| Surface | Current | Threshold | Baseline | Delta | Status |",
        "| --- | --- | --- | --- | --- | --- |",
        _surface_row("Backend source", report.backend_source),
        _surface_row("Backend tests", report.backend_tests),
        _surface_row("Frontend source", report.frontend_source),
        _surface_row("Frontend tests", report.frontend_tests),
        "",
    ]

    if report.patch.applicable:
        patch_percent = f"{report.patch.percent:.2f}%"
        lines.append(
            "Patch coverage (changed executable source lines): "
            f"{patch_percent} ({report.patch.covered_lines}/{report.patch.total_lines})"
        )
        if report.patch.uncovered_lines:
            lines.extend(["", "Uncovered changed source lines:"])
            lines.extend(
                f"- `{item.path}:{item.line}`"
                for item in report.patch.uncovered_lines[:_UNCOVERED_LINE_PREVIEW_LIMIT]
            )
            if len(report.patch.uncovered_lines) > _UNCOVERED_LINE_PREVIEW_LIMIT:
                remaining = len(report.patch.uncovered_lines) - _UNCOVERED_LINE_PREVIEW_LIMIT
                lines.append(f"- `{remaining}` more uncovered changed lines omitted")
    else:
        lines.append("Patch coverage: n/a (no changed executable source lines found)")

    _append_surface_preview(lines, "Backend source gaps", report.backend_source)
    _append_surface_preview(lines, "Backend test files below 100%", report.backend_tests)
    _append_surface_preview(lines, "Frontend source gaps", report.frontend_source)
    _append_surface_preview(lines, "Frontend test files below 100%", report.frontend_tests)

    if not report.baseline_available:
        lines.extend(
            [
                "",
                "Default-branch baseline unavailable. Thresholds were checked, but "
                "regression comparison was skipped for this run.",
            ]
        )
    elif not report.baseline_comparable:
        lines.extend(
            [
                "",
                "Default-branch baseline used an older coverage schema. Thresholds were "
                "checked, but regression comparison was skipped for this run.",
            ]
        )

    return "\n".join(lines) + "\n"


def _validate_inputs(args: argparse.Namespace) -> None:
    if args.backend_json is None and args.frontend_summary is None:
        msg = "Provide at least one coverage input surface."
        raise SystemExit(msg)
    if args.frontend_summary is not None and args.frontend_lcov is None:
        msg = "--frontend-lcov is required when --frontend-summary is provided."
        raise SystemExit(msg)
    if args.frontend_lcov is not None and args.frontend_summary is None:
        msg = "--frontend-summary is required when --frontend-lcov is provided."
        raise SystemExit(msg)


def main() -> int:
    """Parse CLI inputs, build the report, write artifacts, and enforce gates."""

    args = _parse_args()
    _validate_inputs(args)
    report = generate_report(
        repo_root=args.repo_root,
        backend_json_path=args.backend_json,
        frontend_summary_path=args.frontend_summary,
        frontend_lcov_path=args.frontend_lcov,
        diff_path=args.diff,
        baseline_path=args.baseline,
    )

    args.summary_md.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    markdown = render_markdown(report)
    args.summary_md.write_text(markdown)
    args.report_json.write_text(json.dumps(asdict(report), indent=2, sort_keys=True) + "\n")
    print(markdown, end="")

    if args.fail_on_thresholds and report.threshold_failed:
        return 2
    if args.fail_on_regression and report.total_regressed:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
