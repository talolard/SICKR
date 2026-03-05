"""Renderer integration for generating floor-plan images with renovation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

from renovation.elements import create_elements_registry
from renovation.floor_plan import FloorPlan
from renovation.project import Project

from tal_maria_ikea.tools.floor_planner_models import FloorPlanRequest


class FloorPlannerRenderError(RuntimeError):
    """Raised when floor-plan rendering fails."""


@dataclass(frozen=True, slots=True)
class FloorPlanRenderResult:
    """Structured metadata returned after successful rendering."""

    output_png: Path
    plan_name: str
    wall_count: int
    door_count: int
    window_count: int


class _ProjectSettings(TypedDict):
    dpi: int
    pdf_file: str | None
    png_dir: str


class _LayoutSettings(TypedDict):
    bottom_left_corner: tuple[float, float]
    top_right_corner: tuple[float, float]
    scale_numerator: int
    scale_denominator: int
    grid_major_step: float
    grid_minor_step: float


class _ElementConfig(TypedDict, total=False):
    type: str
    anchor_point: tuple[float, float]
    length: float
    thickness: float
    orientation_angle: float
    overall_thickness: float
    single_line_thickness: float
    doorway_width: float
    door_width: float
    to_the_right: bool
    color: str


class _TitleConfig(TypedDict):
    text: str
    font_size: int


class _FloorPlanConfig(TypedDict, total=False):
    title: _TitleConfig
    layout: _LayoutSettings
    inherited_elements: list[str]
    elements: list[_ElementConfig]


class _RenovationSettings(TypedDict):
    project: _ProjectSettings
    default_layout: _LayoutSettings
    reusable_elements: dict[str, list[_ElementConfig]]
    floor_plans: list[_FloorPlanConfig]


class FloorPlannerRenderer:
    """Render typed floor-plan payloads to local PNG artifacts."""

    def render(self, request: FloorPlanRequest, output_dir: Path) -> FloorPlanRenderResult:
        """Render one floor plan and return metadata and output file path."""

        output_dir.mkdir(parents=True, exist_ok=True)
        settings = cast(
            "_RenovationSettings",
            request.to_renovation_settings(str(output_dir)),
        )

        try:
            self._render_from_settings(settings)
        except Exception as exc:  # pragma: no cover - protected by integration tests
            msg = f"Failed to render floor plan '{request.plan_name}'"
            raise FloorPlannerRenderError(msg) from exc

        output_png = _resolve_renderer_output(output_dir, request.plan_name)
        if output_png is None:
            msg = f"Renderer did not produce any PNG output in: {output_dir}"
            raise FloorPlannerRenderError(msg)

        final_png = output_dir / f"{request.output_filename_stem}.png"
        if final_png.exists():
            final_png.unlink()
        output_png.replace(final_png)

        return FloorPlanRenderResult(
            output_png=final_png,
            plan_name=request.plan_name,
            wall_count=len(request.walls),
            door_count=len(request.doors),
            window_count=len(request.windows),
        )

    def _render_from_settings(self, settings: _RenovationSettings) -> None:
        elements_registry = create_elements_registry()
        floor_plans: list[FloorPlan] = []

        default_layout = settings["default_layout"]
        reusable = settings["reusable_elements"]

        for floor_plan_params in settings["floor_plans"]:
            layout_params = floor_plan_params.get("layout") or default_layout
            floor_plan = FloorPlan(**layout_params)

            title_params = floor_plan_params.get("title")
            if title_params is not None:
                floor_plan.add_title(**title_params)

            for set_name in floor_plan_params.get("inherited_elements", []):
                for element_params in reusable.get(set_name, []):
                    element_class = elements_registry[element_params["type"]]
                    kwargs = {k: v for k, v in element_params.items() if k != "type"}
                    floor_plan.add_element(element_class(**kwargs))

            for element_params in floor_plan_params.get("elements", []):
                element_class = elements_registry[element_params["type"]]
                kwargs = {k: v for k, v in element_params.items() if k != "type"}
                floor_plan.add_element(element_class(**kwargs))

            floor_plans.append(floor_plan)

        project_settings = settings["project"]
        project = Project(floor_plans, project_settings["dpi"])
        project.render_to_png(project_settings["png_dir"])


def _resolve_renderer_output(output_dir: Path, plan_name: str) -> Path | None:
    plan_named = output_dir / f"{plan_name}.png"
    if plan_named.exists():
        return plan_named

    png_files = sorted(output_dir.glob("*.png"))
    if not png_files:
        return None
    return png_files[0]
