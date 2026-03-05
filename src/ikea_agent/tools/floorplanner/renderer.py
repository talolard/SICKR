"""Renderer integration for generating floor-plan images with renovation."""

from __future__ import annotations

from pathlib import Path

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


class FloorPlannerRenderer:
    """Render typed floor-plan payloads to local PNG artifacts."""

    def render(self, request: FloorPlanRequest, output_dir: Path) -> FloorPlanRenderResult:
        """Render one floor plan and return metadata and output file path."""

        output_dir.mkdir(parents=True, exist_ok=True)
        settings = request.to_renovation_settings(str(output_dir))

        try:
            self._render_from_settings(settings)
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

    def _render_from_settings(self, settings: dict[str, object]) -> None:
        elements_registry = create_elements_registry()
        floor_plans: list[FloorPlan] = []

        default_layout = settings["default_layout"]  # type: ignore[index]
        reusable = settings["reusable_elements"]  # type: ignore[index]

        for floor_plan_params in settings["floor_plans"]:  # type: ignore[index]
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

        project_settings = settings["project"]  # type: ignore[index]
        project = Project(floor_plans, project_settings["dpi"])
        project.render_to_png(project_settings["png_dir"])


def _resolve_renderer_output(output_dir: Path) -> Path | None:
    png_files = sorted(output_dir.glob("*.png"))
    if not png_files:
        return None
    return png_files[0]
