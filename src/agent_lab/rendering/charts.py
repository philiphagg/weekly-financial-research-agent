from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape


def write_line_chart_svg(
    points: list[dict],
    output_path: str,
    title: str,
    line_color: str = "#0f766e",
) -> str | None:
    valid_points = [
        point for point in points
        if point.get("date") is not None and point.get("value") is not None
    ]
    if len(valid_points) < 2:
        return None

    values = [float(point["value"]) for point in valid_points]
    min_value = min(values)
    max_value = max(values)
    spread = max_value - min_value or 1.0

    width = 900
    height = 320
    left = 70
    right = 30
    top = 40
    bottom = 45
    plot_width = width - left - right
    plot_height = height - top - bottom

    coords: list[str] = []
    for idx, point in enumerate(valid_points):
        x = left + (idx / (len(valid_points) - 1)) * plot_width
        y = top + (1.0 - ((float(point["value"]) - min_value) / spread)) * plot_height
        coords.append(f"{x:.1f},{y:.1f}")

    y_labels = [min_value, min_value + spread / 2.0, max_value]
    dates = [valid_points[0]["date"], valid_points[len(valid_points) // 2]["date"], valid_points[-1]["date"]]

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="#f8fafc"/>
  <text x="{left}" y="24" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#0f172a">{title}</text>
  <line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#94a3b8" stroke-width="1"/>
  <line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#94a3b8" stroke-width="1"/>
  <polyline fill="none" stroke="{line_color}" stroke-width="3" points="{' '.join(coords)}"/>
  <text x="{left-10}" y="{top+4}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#475569">{y_labels[2]:.2f}</text>
  <text x="{left-10}" y="{top + plot_height / 2 + 4}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#475569">{y_labels[1]:.2f}</text>
  <text x="{left-10}" y="{height-bottom+4}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#475569">{y_labels[0]:.2f}</text>
  <text x="{left}" y="{height-15}" font-family="Arial, sans-serif" font-size="12" fill="#475569">{dates[0]}</text>
  <text x="{left + plot_width / 2}" y="{height-15}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#475569">{dates[1]}</text>
  <text x="{width-right}" y="{height-15}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#475569">{dates[2]}</text>
</svg>
"""

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(svg, encoding="utf-8")
    return str(target)


def write_sector_rotation_scatter_svg(
    observations: list[dict],
    output_path: str,
    title: str = "Sector rotation quadrant",
) -> str | None:
    valid = [
        observation for observation in observations
        if isinstance(observation.get("week_anchor_return"), (int, float))
        and isinstance(observation.get("one_week_return"), (int, float))
    ]
    if len(valid) < 2:
        return None

    width = 980
    height = 560
    left = 90
    right = 30
    top = 55
    bottom = 60
    plot_width = width - left - right
    plot_height = height - top - bottom

    x_values = [float(item["week_anchor_return"]) for item in valid]
    y_values = [float(item["one_week_return"]) for item in valid]
    x_extent = max(abs(min(x_values)), abs(max(x_values)), 0.02)
    y_extent = max(abs(min(y_values)), abs(max(y_values)), 0.02)

    def map_x(value: float) -> float:
        return left + ((value + x_extent) / (2 * x_extent)) * plot_width

    def map_y(value: float) -> float:
        return top + (1 - ((value + y_extent) / (2 * y_extent))) * plot_height

    quadrant_fills = {
        "leading": "#dcfce7",
        "weakening": "#fef3c7",
        "lagging": "#fee2e2",
        "improving": "#dbeafe",
    }
    point_fills = {
        "leading": "#15803d",
        "weakening": "#b45309",
        "lagging": "#b91c1c",
        "improving": "#1d4ed8",
    }
    quadrants = [
        ("leading", left + plot_width / 2, top, plot_width / 2, plot_height / 2, "Leading"),
        ("weakening", left + plot_width / 2, top + plot_height / 2, plot_width / 2, plot_height / 2, "Weakening"),
        ("lagging", left, top + plot_height / 2, plot_width / 2, plot_height / 2, "Lagging"),
        ("improving", left, top, plot_width / 2, plot_height / 2, "Improving"),
    ]

    elements: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'  <rect width="{width}" height="{height}" fill="#f8fafc"/>',
        f'  <text x="{left}" y="28" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#0f172a">{escape(title)}</text>',
        '  <text x="90" y="46" font-family="Arial, sans-serif" font-size="12" fill="#475569">X-axis: week-anchor return. Y-axis: one-week return.</text>',
    ]
    for key, x, y, w, h, label in quadrants:
        elements.append(f'  <rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{quadrant_fills[key]}" opacity="0.65"/>')
        elements.append(f'  <text x="{x + 10:.1f}" y="{y + 18:.1f}" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#334155">{label}</text>')

    x_zero = map_x(0.0)
    y_zero = map_y(0.0)
    elements.extend(
        [
            f'  <line x1="{left}" y1="{y_zero:.1f}" x2="{width-right}" y2="{y_zero:.1f}" stroke="#64748b" stroke-width="1.5" stroke-dasharray="4 4"/>',
            f'  <line x1="{x_zero:.1f}" y1="{top}" x2="{x_zero:.1f}" y2="{height-bottom}" stroke="#64748b" stroke-width="1.5" stroke-dasharray="4 4"/>',
            f'  <rect x="{left}" y="{top}" width="{plot_width}" height="{plot_height}" fill="none" stroke="#94a3b8" stroke-width="1"/>',
            f'  <text x="{width / 2:.1f}" y="{height - 15}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#475569">Week-anchor return</text>',
            f'  <text x="24" y="{height / 2:.1f}" transform="rotate(-90 24 {height / 2:.1f})" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#475569">One-week return</text>',
        ]
    )

    for observation in valid:
        x = map_x(float(observation["week_anchor_return"]))
        y = map_y(float(observation["one_week_return"]))
        label = escape(str(observation.get("name", "Unknown")))
        quadrant = str(observation.get("quadrant") or "unclassified")
        fill = point_fills.get(quadrant, "#475569")
        elements.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="{fill}" fill-opacity="0.9"/>')
        elements.append(f'  <text x="{x + 8:.1f}" y="{y - 8:.1f}" font-family="Arial, sans-serif" font-size="11" fill="#0f172a">{label}</text>')

    elements.append(f'  <text x="{left}" y="{height - 35}" font-family="Arial, sans-serif" font-size="11" fill="#475569">Negative</text>')
    elements.append(f'  <text x="{width - right}" y="{height - 35}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#475569">Positive</text>')
    elements.append(f'  <text x="{left - 12}" y="{height - bottom}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#475569">Negative</text>')
    elements.append(f'  <text x="{left - 12}" y="{top + 10}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#475569">Positive</text>')
    elements.append("</svg>\n")

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(elements), encoding="utf-8")
    return str(target)


def write_sector_rotation_grid_svg(
    observations: list[dict],
    output_path: str,
    title: str = "Sector rotation categories",
    limit_per_quadrant: int = 8,
) -> str | None:
    quadrants = {
        "leading": [],
        "weakening": [],
        "lagging": [],
        "improving": [],
    }
    for observation in observations:
        quadrant = observation.get("quadrant")
        if quadrant in quadrants:
            quadrants[quadrant].append(observation)

    if not any(quadrants.values()):
        return None

    for items in quadrants.values():
        items.sort(key=lambda item: abs(float(item.get("rotation_score") or 0.0)), reverse=True)

    width = 980
    height = 720
    margin = 30
    top = 60
    panel_gap = 20
    panel_width = (width - margin * 2 - panel_gap) / 2
    panel_height = (height - top - margin * 2 - panel_gap) / 2
    panel_positions = {
        "leading": (margin, top),
        "weakening": (margin + panel_width + panel_gap, top),
        "lagging": (margin, top + panel_height + panel_gap),
        "improving": (margin + panel_width + panel_gap, top + panel_height + panel_gap),
    }
    panel_styles = {
        "leading": ("#15803d", "#dcfce7", "Leading"),
        "weakening": ("#b45309", "#fef3c7", "Weakening"),
        "lagging": ("#b91c1c", "#fee2e2", "Lagging"),
        "improving": ("#1d4ed8", "#dbeafe", "Improving"),
    }

    elements: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'  <rect width="{width}" height="{height}" fill="#f8fafc"/>',
        f'  <text x="{margin}" y="30" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#0f172a">{escape(title)}</text>',
        '  <text x="30" y="48" font-family="Arial, sans-serif" font-size="12" fill="#475569">Top rotation scores grouped by quadrant.</text>',
    ]

    for quadrant, (x, y) in panel_positions.items():
        bar_color, panel_fill, label = panel_styles[quadrant]
        items = quadrants[quadrant][:limit_per_quadrant]
        elements.append(f'  <rect x="{x:.1f}" y="{y:.1f}" width="{panel_width:.1f}" height="{panel_height:.1f}" rx="12" fill="{panel_fill}" stroke="#cbd5e1"/>')
        elements.append(f'  <text x="{x + 14:.1f}" y="{y + 24:.1f}" font-family="Arial, sans-serif" font-size="16" font-weight="700" fill="#0f172a">{label}</text>')
        if not items:
            elements.append(f'  <text x="{x + 14:.1f}" y="{y + 48:.1f}" font-family="Arial, sans-serif" font-size="12" fill="#475569">No observations available.</text>')
            continue

        max_score = max(abs(float(item.get("rotation_score") or 0.0)) for item in items) or 1.0
        bar_left = x + 14
        bar_right = x + panel_width - 14
        usable_width = bar_right - bar_left - 160
        start_y = y + 46
        row_gap = 24
        for index, item in enumerate(items):
            item_y = start_y + index * row_gap
            name = escape(str(item.get("name", "Unknown")))
            score = float(item.get("rotation_score") or 0.0)
            bar_width = (abs(score) / max_score) * usable_width
            elements.append(f'  <text x="{bar_left:.1f}" y="{item_y:.1f}" font-family="Arial, sans-serif" font-size="11" fill="#0f172a">{name[:34]}</text>')
            elements.append(f'  <rect x="{bar_left:.1f}" y="{item_y + 4:.1f}" width="{bar_width:.1f}" height="8" rx="4" fill="{bar_color}" fill-opacity="0.85"/>')
            elements.append(f'  <text x="{bar_right:.1f}" y="{item_y + 11:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#334155">{score:.3f}</text>')

    elements.append("</svg>\n")

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(elements), encoding="utf-8")
    return str(target)
