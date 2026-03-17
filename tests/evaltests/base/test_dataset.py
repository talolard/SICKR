from __future__ import annotations

from dataclasses import dataclass

import pytest
from evals.base.dataset import assert_report_has_no_failures


@dataclass(frozen=True, slots=True)
class _FakeAssertionResult:
    value: bool
    reason: str | None


@dataclass(frozen=True, slots=True)
class _FakeCase:
    name: str
    assertions: dict[str, _FakeAssertionResult]
    evaluator_failures: list[object]


@dataclass(frozen=True, slots=True)
class _FakeReport:
    cases: list[_FakeCase]


def test_assert_report_has_no_failures_raises_for_failed_assertions() -> None:
    report = _FakeReport(
        cases=[
            _FakeCase(
                name="case-a",
                assertions={
                    "tool_call_quality": _FakeAssertionResult(
                        value=False,
                        reason="missing width filter",
                    )
                },
                evaluator_failures=[],
            )
        ]
    )

    with pytest.raises(AssertionError, match="missing width filter"):
        assert_report_has_no_failures(report)


def test_assert_report_has_no_failures_allows_clean_reports() -> None:
    report = _FakeReport(
        cases=[
            _FakeCase(
                name="case-a",
                assertions={"tool_call_quality": _FakeAssertionResult(value=True, reason=None)},
                evaluator_failures=[],
            )
        ]
    )

    assert_report_has_no_failures(report)
