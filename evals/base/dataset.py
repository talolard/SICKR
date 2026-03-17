"""Shared dataset/report helpers for direct eval runners."""

from __future__ import annotations

from typing import Any, cast


def assert_report_has_no_failures(report: object) -> None:
    """Raise AssertionError when any case-level assertion in the report failed."""

    report_obj = cast("Any", report)
    failures: list[str] = []
    for case in report_obj.cases:
        case_name = cast("str | None", case.name) or "<unnamed>"
        for label, result in case.assertions.items():
            value = getattr(result, "value", result)
            if value is not False:
                continue
            reason = getattr(result, "reason", None)
            if reason:
                failures.append(f"{case_name}: {label}: {reason}")
            else:
                failures.append(f"{case_name}: {label}")
        failures.extend(
            (f"{case_name}: evaluator failure in {evaluator_failure.evaluator_name}")
            for evaluator_failure in case.evaluator_failures
        )
    if failures:
        raise AssertionError("Eval failures:\n" + "\n".join(failures))
