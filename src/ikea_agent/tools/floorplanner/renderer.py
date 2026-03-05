"""Renderer integration for generating floor-plan images with renovation."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict, cast

from pydantic import BaseModel
from renovation.elements import create_elements_registry
from renovation.floor_plan import FloorPlan
from renovation.project import Project

from ikea_agent.tools.floorplanner.models import FloorPlanRequest


class FloorPlannerRenderError(RuntimeError):
    """Raised when floor-plan rendering fails."""


class FloorPlanRenderResult(BaseModel):
    """Structured metadata returned after successful rendering."""

    output_png: Path
    wall_count: int
    door_count: int
    window_count: int


class FloorPlanRenderSvgResult(BaseModel):
    """Structured metadata returned after successful SVG rendering."""

    output_svg: Path
    wall_count: int
    door_count: int
    window_count: int


class FloorPlannerRenderer:
    """Render typed floor-plan payloads to local PNG artifacts."""

    def render(self, request: FloorPlanRequest, output_dir: Path) -> FloorPlanRenderResult:
        """Render one floor plan and return metadata and output file path."""

        output_dir.mkdir(parents=True, exist_ok=True)
        settings = cast("_RenovationSettings", request.to_renovation_settings(str(output_dir)))

        try:
            self._render_png_from_settings(settings)
        except Exception as exc:  # pragma: no cover - protected by integration tests
            msg = "Failed to render floor plan"
            raise FloorPlannerRenderError(msg) from exc

        output_png = _resolve_renderer_output(output_dir)
        if output_png is None:
            msg = f"Renderer did not produce any PNG output in: {output_dir}"
            raise FloorPlannerRenderError(msg)

        final_png = output_dir / "floor_plan.png"
        if final_png.exists():
            final_png.unlink()
        output_png.replace(final_png)

        return FloorPlanRenderResult(
            output_png=final_png,
            wall_count=request.count_elements("wall"),
            door_count=request.count_elements("door"),
            window_count=request.count_elements("window"),
        )

    def render_svg(self, request: FloorPlanRequest, output_dir: Path) -> FloorPlanRenderSvgResult:
        """Render one floor plan as SVG and return metadata and output file path."""

        output_dir.mkdir(parents=True, exist_ok=True)
        settings = cast("_RenovationSettings", request.to_renovation_settings(str(output_dir)))

        try:
            self._render_svg_from_settings(settings)
        except Exception as exc:  # pragma: no cover - protected by integration tests
            msg = "Failed to render floor plan"
            raise FloorPlannerRenderError(msg) from exc

        output_svg = _resolve_renderer_output_svg(output_dir)
        if output_svg is None:
            msg = f"Renderer did not produce any SVG output in: {output_dir}"
            raise FloorPlannerRenderError(msg)

        final_svg = output_dir / "floor_plan.svg"
        if final_svg.exists():
            final_svg.unlink()
        output_svg.replace(final_svg)

        return FloorPlanRenderSvgResult(
            output_svg=final_svg,
            wall_count=request.count_elements("wall"),
            door_count=request.count_elements("door"),
            window_count=request.count_elements("window"),
        )

    def _render_png_from_settings(self, settings: _RenovationSettings) -> None:
        floor_plans = _create_floor_plans_from_settings(settings)
        project_settings = settings["project"]
        project = Project(floor_plans, project_settings["dpi"])
        project.render_to_png(project_settings["png_dir"])

    def _render_svg_from_settings(self, settings: _RenovationSettings) -> None:
        floor_plans = _create_floor_plans_from_settings(settings)
        project_settings = settings["project"]
        output_dir = Path(project_settings["png_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, floor_plan in enumerate(floor_plans):
            title = floor_plan.title or f"{i}.svg"
            if not title.endswith("svg"):
                title += ".svg"
            floor_plan.fig.savefig(output_dir / title, format="svg", dpi=project_settings["dpi"])


def _resolve_renderer_output(output_dir: Path) -> Path | None:
    png_files = sorted(output_dir.glob("*.png"))
    if not png_files:
        return None
    return png_files[0]


def _resolve_renderer_output_svg(output_dir: Path) -> Path | None:
    svg_files = sorted(output_dir.glob("*.svg"))
    if not svg_files:
        return None
    return svg_files[0]


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


class _TitleSettings(TypedDict):
    text: str
    font_size: int


class _FloorPlanSettings(TypedDict, total=False):
    title: _TitleSettings
    layout: _LayoutSettings
    inherited_elements: list[str]
    elements: list[dict[str, object]]


class _RenovationSettings(TypedDict):
    project: _ProjectSettings
    default_layout: _LayoutSettings
    reusable_elements: dict[str, list[dict[str, object]]]
    floor_plans: list[_FloorPlanSettings]


def _create_floor_plans_from_settings(settings: _RenovationSettings) -> list[FloorPlan]:
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
                element_type = cast("str", element_params["type"])
                element_class = elements_registry[element_type]
                kwargs = {k: v for k, v in element_params.items() if k != "type"}
                floor_plan.add_element(element_class(**kwargs))

        for element_params in floor_plan_params.get("elements", []):
            element_type = cast("str", element_params["type"])
            element_class = elements_registry[element_type]
            kwargs = {k: v for k, v in element_params.items() if k != "type"}
            floor_plan.add_element(element_class(**kwargs))

        floor_plans.append(floor_plan)

    return floor_plans
