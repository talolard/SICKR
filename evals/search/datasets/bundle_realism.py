"""Thread-derived bundle realism evals for the search agent."""

from __future__ import annotations

from pydantic_evals import Case

from evals.search.datasets.common import build_case
from evals.search.types import SearchEvalInput

_STEUERBERATER_PROMPT = (
    "My friend Anna is a bad ass former consultant who drinks the bloog of her enemies "
    "as a protien shake. She is brcoming a german Steuerberater with Hans and Klaus and "
    "wants to decorate to capture all that paperwork, her personality and the germanness "
    "of hans and klaus the Steuerberater. Budget of 15000 euros for a single 8 by 6 meter room"
)
_STEUERBERATER_CONTEXT = (
    "Continuation context from thread agent_search-fe0d9f2d: the assistant had already "
    "pitched a high-contrast executive-office direction for Anna, Hans, and Klaus, with "
    "a command center, an archive wall, and a consultation zone. The user replied 'Yes' "
    "to formalize that direction. The fixture already includes the re-grounded search "
    "return for the chosen MITTZON desk, ALEFJÄLL office chair, BROR shelving unit with "
    "cabinets and drawers, MITTZON conference table, TOSSBERG / LÅNGFJÄLL conference "
    "chair, IDÅSEN cabinet, and HEKTAR floor lamp. This eval judges only the bundle-stage "
    "decision from that point, without rerunning search."
)
_STEUERBERATER_FIXTURE = "steuerberater_bundle_continuation"
_STEUERBERATER_THREAD_ID = "agent_search-fe0d9f2d"


def build_bundle_realism_cases() -> list[Case[SearchEvalInput, str, None]]:
    """Return thread-derived continuation cases that judge subtle bundle realism."""

    shared_kwargs = {
        "fixture_name": _STEUERBERATER_FIXTURE,
        "source_thread_id": _STEUERBERATER_THREAD_ID,
        "scenario_context": _STEUERBERATER_CONTEXT,
        "continue_from_history": True,
        "forbid_search_call": True,
        "require_bundle_call": True,
    }
    return [
        build_case(
            "steuerberater_workstation_coverage",
            _STEUERBERATER_PROMPT,
            bundle_attrs=[
                (
                    "The bundle treats Anna, Hans, and Klaus as three people using the "
                    "office rather than one executive plus occasional meeting guests."
                ),
                (
                    "The bundle provides three dedicated primary workstations, which "
                    "normally means three desks and three task chairs unless an explicit "
                    "alternative is justified."
                ),
            ],
            forbidden_bundle_attrs=[
                (
                    "Only one dedicated desk and one dedicated office chair for the whole "
                    "three-person office without explicit justification."
                ),
            ],
            **shared_kwargs,
        ),
        build_case(
            "steuerberater_large_storage_quantity_sanity",
            _STEUERBERATER_PROMPT,
            bundle_attrs=[
                (
                    "Large composite storage pieces have physically plausible quantities "
                    "for one 8m by 6m office."
                ),
                (
                    "The bundle does not multiply the BROR shelving unit with cabinets and "
                    "drawers into an implausible count without a spatial rationale."
                ),
            ],
            forbidden_bundle_attrs=[
                (
                    "Six copies of the BROR shelving unit with cabinets and drawers, or a "
                    "similarly implausible multiplication of a large composite storage unit "
                    "without explanation."
                ),
            ],
            **shared_kwargs,
        ),
        build_case(
            "steuerberater_storage_role_differentiation",
            _STEUERBERATER_PROMPT,
            bundle_attrs=[
                (
                    "If both BROR archival storage and IDÅSEN lockable cabinets are "
                    "included, the bundle clearly differentiates their roles and avoids "
                    "unnecessary redundancy."
                ),
            ],
            forbidden_bundle_attrs=[
                (
                    "Open shelving and lockable cabinet storage that feel duplicative "
                    "rather than intentionally divided into separate roles."
                ),
            ],
            **shared_kwargs,
        ),
        build_case(
            "steuerberater_budget_utilization",
            _STEUERBERATER_PROMPT,
            bundle_attrs=[
                (
                    "For a premium 48 square meter executive office with a €15,000 budget, "
                    "the bundle uses a material portion of the budget or explicitly explains "
                    "why a much lower spend is preferable."
                ),
            ],
            forbidden_bundle_attrs=[
                "A dramatically under-budget bundle with no rationale for the underspend.",
            ],
            **shared_kwargs,
        ),
    ]


__all__ = ["build_bundle_realism_cases"]
