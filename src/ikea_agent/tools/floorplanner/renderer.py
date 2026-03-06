"""In-repo floor-plan renderer that emits deterministic SVG and PNG artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from ikea_agent.tools.floorplanner.models import (
    DetailedFloorPlanScene,
    FloorPlanScene,
    FurniturePlacementCm,
    Point2DCm,
    RenderWarning,
    infer_outline_from_dimensions,
)


class FloorPlannerRenderError(RuntimeError):
    """Raised when scene rendering fails."""


@dataclass(frozen=True, slots=True)
class FloorPlannerRenderArtifacts:
    """Disk artifacts and lightweight metadata emitted by one render pass."""

    output_svg: Path
    output_png: Path
    warnings: list[RenderWarning]
    legend_items: list[str]
    scale_major_step_cm: int


@dataclass(frozen=True, slots=True)
class _Transform:
    scale: float
    plan_origin_x: float
    plan_origin_y: float
    plan_height_px: float

    def to_px(self, point: Point2DCm) -> tuple[float, float]:
        x = self.plan_origin_x + point.x_cm * self.scale
        y = self.plan_origin_y + self.plan_height_px - point.y_cm * self.scale
        return (x, y)


class FloorPlannerRenderer:
    """Render top-down + elevation visuals for typed floor-plan scenes."""

    _canvas_width_px = 1800
    _canvas_height_px = 1040
    _left_margin_px = 70
    _top_margin_px = 70
    _plan_width_px = 1180
    _plan_height_px = 900
    _elevation_x_px = 1300
    _elevation_width_px = 420
    _elevation_floor_y_px = 900
    _major_grid_step_cm = 50

    def render(self, scene: FloorPlanScene, output_dir: Path) -> FloorPlannerRenderArtifacts:
        """Render one scene to SVG and PNG files under output directory."""

        output_dir.mkdir(parents=True, exist_ok=True)
        svg_path = output_dir / "floor_plan.svg"
        png_path = output_dir / "floor_plan.png"

        warnings = self._collect_warnings(scene)
        legend_items = self._legend_items(scene)

        transform = self._compute_transform(scene)
        svg_text = self._render_svg(scene, transform, warnings, legend_items)
        svg_path.write_text(svg_text, encoding="utf-8")

        image = self._render_png(scene, transform, warnings, legend_items)
        image.save(png_path)

        return FloorPlannerRenderArtifacts(
            output_svg=svg_path,
            output_png=png_path,
            warnings=warnings,
            legend_items=legend_items,
            scale_major_step_cm=self._major_grid_step_cm,
        )

    def _compute_transform(self, scene: FloorPlanScene) -> _Transform:
        dimensions = scene.architecture.dimensions_cm
        scale_x = (self._plan_width_px - 2 * self._left_margin_px) / max(
            dimensions.length_x_cm, 1.0
        )
        scale_y = (self._plan_height_px - 2 * self._top_margin_px) / max(dimensions.depth_y_cm, 1.0)
        scale = min(scale_x, scale_y)
        return _Transform(
            scale=scale,
            plan_origin_x=self._left_margin_px,
            plan_origin_y=self._top_margin_px,
            plan_height_px=self._plan_height_px - 2 * self._top_margin_px,
        )

    def _render_svg(  # noqa: C901
        self,
        scene: FloorPlanScene,
        transform: _Transform,
        warnings: list[RenderWarning],
        legend_items: list[str],
    ) -> str:
        outline = scene.architecture.outline_cm or infer_outline_from_dimensions(
            scene.architecture.dimensions_cm
        )

        parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self._canvas_width_px}" '
            f'height="{self._canvas_height_px}" '
            f'viewBox="0 0 {self._canvas_width_px} {self._canvas_height_px}">',
            '<rect x="0" y="0" width="100%" height="100%" fill="#fcfcfb"/>',
            '<g id="grid">',
        ]

        dimensions = scene.architecture.dimensions_cm
        for x_cm in range(0, int(dimensions.length_x_cm) + 1, self._major_grid_step_cm):
            x_px, _ = transform.to_px(Point2DCm(x_cm=float(x_cm), y_cm=0.0))
            parts.append(
                f'<line x1="{x_px:.1f}" y1="{self._top_margin_px}" x2="{x_px:.1f}" '
                f'y2="{self._plan_height_px - self._top_margin_px}" '
                'stroke="#ece8e1" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{x_px:.1f}" y="{self._plan_height_px - self._top_margin_px + 20}" '
                'font-size="12" text-anchor="middle" fill="#6b7280">'
                f"{x_cm}</text>"
            )

        for y_cm in range(0, int(dimensions.depth_y_cm) + 1, self._major_grid_step_cm):
            _, y_px = transform.to_px(Point2DCm(x_cm=0.0, y_cm=float(y_cm)))
            parts.append(
                f'<line x1="{self._left_margin_px}" y1="{y_px:.1f}" '
                f'x2="{self._plan_width_px - self._left_margin_px}" y2="{y_px:.1f}" '
                'stroke="#ece8e1" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{self._left_margin_px - 14}" y="{y_px + 4:.1f}" '
                'font-size="12" text-anchor="end" fill="#6b7280">'
                f"{y_cm}</text>"
            )

        parts.append("</g>")

        parts.append('<g id="architecture">')
        outline_points = " ".join(
            f"{transform.to_px(point)[0]:.1f},{transform.to_px(point)[1]:.1f}" for point in outline
        )
        parts.append(
            f'<polygon points="{outline_points}" fill="#ffffff" stroke="#2d2b29" '
            'stroke-width="3" stroke-opacity="0.75"/>'
        )

        for wall in scene.architecture.walls:
            x1, y1 = transform.to_px(wall.start_cm)
            x2, y2 = transform.to_px(wall.end_cm)
            color = wall.color or "#1f2937"
            width = max(2.0, wall.thickness_cm * transform.scale * 0.05)
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{color}" stroke-width="{width:.1f}" stroke-linecap="round"/>'
            )

        for door in scene.architecture.doors:
            x1, y1 = transform.to_px(door.start_cm)
            x2, y2 = transform.to_px(door.end_cm)
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                'stroke="#b91c1c" stroke-width="4"/>'
            )
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2
            parts.append(
                f'<text x="{mx:.1f}" y="{my - 8:.1f}" font-size="11" '
                'text-anchor="middle" fill="#b91c1c">door</text>'
            )

        for window in scene.architecture.windows:
            x1, y1 = transform.to_px(window.start_cm)
            x2, y2 = transform.to_px(window.end_cm)
            parts.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                'stroke="#0369a1" stroke-width="5" stroke-linecap="round"/>'
            )

        parts.append("</g>")

        parts.append('<g id="placements">')
        for placement in scene.placements:
            parts.extend(self._placement_svg(placement, transform))
        parts.append("</g>")

        if isinstance(scene, DetailedFloorPlanScene):
            parts.append('<g id="fixtures">')
            for fixture in scene.fixtures:
                x_px, y_px = transform.to_px(Point2DCm(x_cm=fixture.x_cm, y_cm=fixture.y_cm))
                color = "#7c3aed" if fixture.fixture_kind == "light" else "#0f766e"
                parts.append(
                    f'<circle cx="{x_px:.1f}" cy="{y_px:.1f}" r="8" fill="{color}" '
                    'fill-opacity="0.7"/>'
                )
                parts.append(
                    f'<text x="{x_px + 12:.1f}" y="{y_px + 4:.1f}" font-size="11" fill="{color}">'
                    f"{fixture.fixture_kind}</text>"
                )
            parts.append("</g>")

        parts.extend(self._elevation_svg(scene))
        parts.extend(self._legend_svg(legend_items, warnings))

        parts.append(
            f'<text x="{self._left_margin_px}" y="35" font-size="22" fill="#111827" '
            'font-weight="600">Floor Plan (Top + Elevation)</text>'
        )
        parts.append("</svg>")
        return "\n".join(parts)

    def _placement_svg(self, placement: FurniturePlacementCm, transform: _Transform) -> list[str]:
        x1, y1 = transform.to_px(placement.position_cm)
        x2, y2 = transform.to_px(
            Point2DCm(
                x_cm=placement.position_cm.x_cm + placement.size_cm.x_cm,
                y_cm=placement.position_cm.y_cm + placement.size_cm.y_cm,
            )
        )
        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        color = placement.color or "#64748b"
        stroke_dash = (
            ' stroke-dasharray="7 4"' if placement.wall_mounted or placement.z_cm > 0 else ""
        )
        label = placement.label or placement.name

        lines = [
            f'<rect x="{left:.1f}" y="{top:.1f}" width="{width:.1f}" height="{height:.1f}" '
            f'fill="{color}" fill-opacity="0.35" stroke="#1f2937" '
            f'stroke-width="1.5"{stroke_dash}/>',
            f'<text x="{left + width / 2:.1f}" y="{top + height / 2:.1f}" '
            'font-size="12" text-anchor="middle" dominant-baseline="middle" fill="#0f172a">'
            f"{label}</text>",
        ]

        if placement.z_cm > 0 or placement.wall_mounted:
            lines.append(
                f'<text x="{left + width / 2:.1f}" y="{top + height + 14:.1f}" '
                'font-size="11" text-anchor="middle" fill="#334155">'
                f"z={placement.z_cm:.0f} cm</text>"
            )

        return lines

    def _elevation_svg(self, scene: FloorPlanScene) -> list[str]:
        parts = [
            '<g id="elevation">',
            f'<rect x="{self._elevation_x_px}" y="{self._top_margin_px}" '
            f'width="{self._elevation_width_px}" '
            f'height="{self._plan_height_px - 2 * self._top_margin_px}" '
            'fill="#ffffff" stroke="#d6d3d1" stroke-width="1.5"/>',
            f'<line x1="{self._elevation_x_px}" y1="{self._elevation_floor_y_px}" '
            f'x2="{self._elevation_x_px + self._elevation_width_px}" '
            f'y2="{self._elevation_floor_y_px}" '
            'stroke="#1f2937" stroke-width="2"/>',
            f'<text x="{self._elevation_x_px + self._elevation_width_px / 2:.1f}" '
            f'y="{self._top_margin_px - 14:.1f}" font-size="14" '
            'text-anchor="middle" fill="#111827">'
            "Elevation (X/Z)</text>",
        ]

        room_w = max(scene.architecture.dimensions_cm.length_x_cm, 1.0)
        room_h = max(scene.architecture.dimensions_cm.height_z_cm, 1.0)
        x_scale = (self._elevation_width_px - 40) / room_w
        z_scale = (self._plan_height_px - 2 * self._top_margin_px - 40) / room_h

        for idx, placement in enumerate(scene.placements):
            x_px = self._elevation_x_px + 20 + placement.position_cm.x_cm * x_scale
            w_px = max(4.0, placement.size_cm.x_cm * x_scale)
            z_bottom = self._elevation_floor_y_px - placement.z_cm * z_scale
            h_px = max(3.0, placement.size_cm.z_cm * z_scale)
            y_px = z_bottom - h_px
            color = placement.color or "#64748b"
            dash = ' stroke-dasharray="6 3"' if placement.wall_mounted else ""
            parts.append(
                f'<rect x="{x_px:.1f}" y="{y_px:.1f}" width="{w_px:.1f}" height="{h_px:.1f}" '
                f'fill="{color}" fill-opacity="0.5" stroke="#0f172a" stroke-width="1"{dash}/>'
            )
            label_y = y_px - 6 - (idx % 3) * 12
            parts.append(
                f'<text x="{x_px + w_px / 2:.1f}" y="{label_y:.1f}" font-size="10" '
                f'text-anchor="middle" fill="#334155">{placement.name}</text>'
            )

        parts.append("</g>")
        return parts

    def _legend_svg(self, legend_items: list[str], warnings: list[RenderWarning]) -> list[str]:
        start_x = self._elevation_x_px
        start_y = self._canvas_height_px - 190
        parts = [
            '<g id="legend">',
            f'<rect x="{start_x}" y="{start_y}" width="{self._elevation_width_px}" height="170" '
            'fill="#ffffff" stroke="#d6d3d1" stroke-width="1.5"/>',
            f'<text x="{start_x + 12}" y="{start_y + 22}" font-size="13" fill="#111827" '
            'font-weight="600">Legend</text>',
        ]

        for idx, item in enumerate(legend_items):
            parts.append(
                f'<text x="{start_x + 12}" y="{start_y + 42 + idx * 16}" '
                f'font-size="11" fill="#334155">- {item}</text>'
            )

        warning_offset = start_y + 108
        parts.append(
            f'<text x="{start_x + 12}" y="{warning_offset}" font-size="12" fill="#7c2d12" '
            'font-weight="600">Warnings</text>'
        )
        if not warnings:
            parts.append(
                f'<text x="{start_x + 12}" y="{warning_offset + 16}" font-size="11" fill="#166534">'
                "none</text>"
            )
        else:
            for idx, warning in enumerate(warnings[:3]):
                parts.append(
                    f'<text x="{start_x + 12}" y="{warning_offset + 16 + idx * 14}" '
                    f'font-size="10" fill="#7c2d12">{warning.code}: {warning.message}</text>'
                )

        parts.append("</g>")
        return parts

    def _render_png(
        self,
        scene: FloorPlanScene,
        transform: _Transform,
        warnings: list[RenderWarning],
        legend_items: list[str],
    ) -> Image.Image:
        image = Image.new("RGB", (self._canvas_width_px, self._canvas_height_px), "#fcfcfb")
        draw = ImageDraw.Draw(image)

        dimensions = scene.architecture.dimensions_cm
        for x_cm in range(0, int(dimensions.length_x_cm) + 1, self._major_grid_step_cm):
            x_px, _ = transform.to_px(Point2DCm(x_cm=float(x_cm), y_cm=0.0))
            draw.line(
                (
                    x_px,
                    self._top_margin_px,
                    x_px,
                    self._plan_height_px - self._top_margin_px,
                ),
                fill="#ece8e1",
                width=1,
            )

        for y_cm in range(0, int(dimensions.depth_y_cm) + 1, self._major_grid_step_cm):
            _, y_px = transform.to_px(Point2DCm(x_cm=0.0, y_cm=float(y_cm)))
            draw.line(
                (
                    self._left_margin_px,
                    y_px,
                    self._plan_width_px - self._left_margin_px,
                    y_px,
                ),
                fill="#ece8e1",
                width=1,
            )

        outline = scene.architecture.outline_cm or infer_outline_from_dimensions(
            scene.architecture.dimensions_cm
        )
        outline_px = [transform.to_px(point) for point in outline]
        draw.polygon(outline_px, outline="#2d2b29", fill="#ffffff", width=3)

        for wall in scene.architecture.walls:
            x1, y1 = transform.to_px(wall.start_cm)
            x2, y2 = transform.to_px(wall.end_cm)
            draw.line((x1, y1, x2, y2), fill=wall.color or "#1f2937", width=4)

        for door in scene.architecture.doors:
            x1, y1 = transform.to_px(door.start_cm)
            x2, y2 = transform.to_px(door.end_cm)
            draw.line((x1, y1, x2, y2), fill="#b91c1c", width=5)

        for window in scene.architecture.windows:
            x1, y1 = transform.to_px(window.start_cm)
            x2, y2 = transform.to_px(window.end_cm)
            draw.line((x1, y1, x2, y2), fill="#0369a1", width=6)

        for placement in scene.placements:
            x1, y1 = transform.to_px(placement.position_cm)
            x2, y2 = transform.to_px(
                Point2DCm(
                    x_cm=placement.position_cm.x_cm + placement.size_cm.x_cm,
                    y_cm=placement.position_cm.y_cm + placement.size_cm.y_cm,
                )
            )
            left = min(x1, x2)
            top = min(y1, y2)
            right = max(x1, x2)
            bottom = max(y1, y2)
            fill = placement.color or "#64748b"
            draw.rectangle((left, top, right, bottom), outline="#1f2937", width=2, fill=fill)

        self._render_png_elevation(draw, scene)
        self._render_png_legend(draw, legend_items, warnings)

        draw.text((self._left_margin_px, 28), "Floor Plan (Top + Elevation)", fill="#111827")
        return image

    def _render_png_elevation(self, draw: ImageDraw.ImageDraw, scene: FloorPlanScene) -> None:
        draw.rectangle(
            (
                self._elevation_x_px,
                self._top_margin_px,
                self._elevation_x_px + self._elevation_width_px,
                self._plan_height_px - self._top_margin_px,
            ),
            outline="#d6d3d1",
            width=2,
            fill="#ffffff",
        )
        draw.line(
            (
                self._elevation_x_px,
                self._elevation_floor_y_px,
                self._elevation_x_px + self._elevation_width_px,
                self._elevation_floor_y_px,
            ),
            fill="#1f2937",
            width=2,
        )

        room_w = max(scene.architecture.dimensions_cm.length_x_cm, 1.0)
        room_h = max(scene.architecture.dimensions_cm.height_z_cm, 1.0)
        x_scale = (self._elevation_width_px - 40) / room_w
        z_scale = (self._plan_height_px - 2 * self._top_margin_px - 40) / room_h

        for placement in scene.placements:
            x_px = self._elevation_x_px + 20 + placement.position_cm.x_cm * x_scale
            w_px = max(4.0, placement.size_cm.x_cm * x_scale)
            z_bottom = self._elevation_floor_y_px - placement.z_cm * z_scale
            h_px = max(3.0, placement.size_cm.z_cm * z_scale)
            y_px = z_bottom - h_px
            fill = placement.color or "#64748b"
            draw.rectangle(
                (x_px, y_px, x_px + w_px, y_px + h_px), outline="#0f172a", fill=fill, width=1
            )

    def _render_png_legend(
        self,
        draw: ImageDraw.ImageDraw,
        legend_items: list[str],
        warnings: list[RenderWarning],
    ) -> None:
        start_x = self._elevation_x_px
        start_y = self._canvas_height_px - 190

        draw.rectangle(
            (start_x, start_y, start_x + self._elevation_width_px, start_y + 170),
            outline="#d6d3d1",
            fill="#ffffff",
            width=2,
        )
        draw.text((start_x + 12, start_y + 8), "Legend", fill="#111827")
        for idx, item in enumerate(legend_items):
            draw.text((start_x + 12, start_y + 28 + idx * 16), f"- {item}", fill="#334155")

        draw.text((start_x + 12, start_y + 102), "Warnings", fill="#7c2d12")
        if not warnings:
            draw.text((start_x + 12, start_y + 120), "none", fill="#166534")
        else:
            for idx, warning in enumerate(warnings[:3]):
                draw.text(
                    (start_x + 12, start_y + 120 + idx * 14),
                    f"{warning.code}: {warning.message}",
                    fill="#7c2d12",
                )

    def _collect_warnings(self, scene: FloorPlanScene) -> list[RenderWarning]:
        dims = scene.architecture.dimensions_cm
        warnings: list[RenderWarning] = []
        for placement in scene.placements:
            if placement.position_cm.x_cm < 0 or placement.position_cm.y_cm < 0:
                warnings.append(
                    RenderWarning(
                        severity="warn",
                        code="placement_negative_position",
                        message="Placement has a negative x/y coordinate.",
                        entity_id=placement.placement_id,
                    )
                )
            if placement.position_cm.x_cm + placement.size_cm.x_cm > dims.length_x_cm:
                warnings.append(
                    RenderWarning(
                        severity="warn",
                        code="placement_out_of_bounds_x",
                        message="Placement extends beyond room x-length.",
                        entity_id=placement.placement_id,
                    )
                )
            if placement.position_cm.y_cm + placement.size_cm.y_cm > dims.depth_y_cm:
                warnings.append(
                    RenderWarning(
                        severity="warn",
                        code="placement_out_of_bounds_y",
                        message="Placement extends beyond room y-depth.",
                        entity_id=placement.placement_id,
                    )
                )
            if placement.z_cm + placement.size_cm.z_cm > dims.height_z_cm:
                warnings.append(
                    RenderWarning(
                        severity="warn",
                        code="placement_out_of_bounds_z",
                        message="Placement extends beyond room z-height.",
                        entity_id=placement.placement_id,
                    )
                )

        return warnings

    def _legend_items(self, scene: FloorPlanScene) -> list[str]:
        items = [
            "Walls: dark strokes",
            "Doors: red segments",
            "Windows: blue segments",
            "Dashed furniture: mounted/elevated",
            "Right panel: X/Z elevation",
            f"Scale grid: {self._major_grid_step_cm} cm",
        ]
        if isinstance(scene, DetailedFloorPlanScene) and scene.fixtures:
            items.append("Fixtures: teal sockets, violet lights")
        return items
