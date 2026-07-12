"""
Renderers — turn an InterfaceSpec into actual output.

HTML, Markdown, JSON. The interface is the same; the output adapts.
"""

from __future__ import annotations

import html
import json
from typing import Any

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import InterfaceSpec


class BaseRenderer:
    """Base class for renderers."""

    def render(self, spec: InterfaceSpec) -> str:
        """Render the spec to a string."""
        raise NotImplementedError


class HTMLRenderer(BaseRenderer):
    """
    Generates clean HTML — no frameworks, no build step.

    The output is self-contained and can be dropped into any page.
    """

    def render(self, spec: InterfaceSpec) -> str:
        if spec.view_type == "table":
            return self._render_table(spec)
        elif spec.view_type == "detail":
            return self._render_detail(spec)
        elif spec.view_type == "form":
            return self._render_form(spec)
        elif spec.view_type == "summary":
            return self._render_summary(spec)
        return self._render_table(spec)

    def _render_table(self, spec: InterfaceSpec) -> str:
        rows = spec.data
        cols = spec.columns

        parts = [
            '<div class="a2ui-container">',
            f'<h2 class="a2ui-title">{html.escape(spec.title)}</h2>',
        ]

        if not rows:
            parts.append('<p class="a2ui-empty">No matching records.</p>')
            parts.append("</div>")
            return "\n".join(parts)

        parts.append('<table class="a2ui-table">')
        parts.append("<thead><tr>")
        for col in cols:
            label = self._col_label(spec, col)
            arrow = ""
            if spec.sort_by and spec.sort_by[0] == col:
                arrow = " ↓" if spec.sort_by[1] == "desc" else " ↑"
            parts.append(f"<th>{html.escape(label)}{arrow}</th>")
        parts.append("</tr></thead>")
        parts.append("<tbody>")
        for row in rows:
            parts.append("<tr>")
            for col in cols:
                val = row.get(col, "")
                formatted = self._format_value(val)
                parts.append(f"<td>{formatted}</td>")
            parts.append("</tr>")
        parts.append("</tbody>")
        parts.append("</table>")
        parts.append(f'<p class="a2ui-count">{len(rows)} record(s)</p>')
        parts.append("</div>")
        return "\n".join(parts)

    def _render_detail(self, spec: InterfaceSpec) -> str:
        rows = spec.data
        cols = spec.columns

        parts = [
            '<div class="a2ui-container">',
            f'<h2 class="a2ui-title">{html.escape(spec.title)}</h2>',
        ]

        if not rows:
            parts.append('<p class="a2ui-empty">No matching records.</p>')
            parts.append("</div>")
            return "\n".join(parts)

        for row in rows:
            parts.append('<div class="a2ui-detail">')
            for col in cols:
                label = self._col_label(spec, col)
                val = row.get(col, "")
                formatted = self._format_value(val)
                parts.append(
                    f'<div class="a2ui-field">'
                    f'<span class="a2ui-label">{html.escape(label)}:</span> '
                    f'<span class="a2ui-value">{formatted}</span>'
                    f"</div>"
                )
            parts.append("</div>")

        parts.append("</div>")
        return "\n".join(parts)

    def _render_form(self, spec: InterfaceSpec) -> str:
        cols = spec.columns

        parts = [
            '<div class="a2ui-container">',
            f'<h2 class="a2ui-title">{html.escape(spec.title)}</h2>',
            '<form class="a2ui-form">',
        ]

        for col in cols:
            label = self._col_label(spec, col)
            parts.append(
                f'<div class="a2ui-form-field">'
                f'<label for="a2ui-{html.escape(col)}">{html.escape(label)}</label>'
                f'<input type="text" id="a2ui-{html.escape(col)}" name="{html.escape(col)}" />'
                f"</div>"
            )

        parts.append('<button type="submit">Submit</button>')
        parts.append("</form>")
        parts.append("</div>")
        return "\n".join(parts)

    def _render_summary(self, spec: InterfaceSpec) -> str:
        rows = spec.data
        cols = spec.columns

        parts = [
            '<div class="a2ui-container">',
            f'<h2 class="a2ui-title">{html.escape(spec.title)}</h2>',
        ]

        if not rows:
            parts.append('<p class="a2ui-empty">No data to summarize.</p>')
            parts.append("</div>")
            return "\n".join(parts)

        parts.append('<div class="a2ui-summary">')
        parts.append(f"<p><strong>Total records:</strong> {len(rows)}</p>")

        # Numeric field stats
        for col in cols:
            values = [r.get(col) for r in rows if r.get(col) is not None]
            if values and all(isinstance(v, (int, float)) for v in values):
                parts.append(
                    f"<p><strong>{html.escape(self._col_label(spec, col))}:</strong> "
                    f"min={min(values)}, max={max(values)}, "
                    f"avg={sum(values) / len(values):.1f}</p>"
                )

        parts.append("</div>")
        parts.append("</div>")
        return "\n".join(parts)

    def _col_label(self, spec: InterfaceSpec, col: str) -> str:
        """Get a human-readable label for a column."""
        try:
            fields = spec.intent._parser_schema_fields if hasattr(spec.intent, "_parser_schema_fields") else {}
            if col in fields:
                return fields[col].display_label
        except Exception:
            pass
        return col.replace("_", " ").title()

    def _format_value(self, val: Any) -> str:
        """Format a value for HTML display."""
        if val is None:
            return '<span class="a2ui-null">—</span>'
        if isinstance(val, bool):
            return "✓" if val else "✗"
        return html.escape(str(val))


class MarkdownRenderer(BaseRenderer):
    """Renders to clean Markdown — great for terminal output and docs."""

    def render(self, spec: InterfaceSpec) -> str:
        if spec.view_type == "table":
            return self._render_table(spec)
        elif spec.view_type == "detail":
            return self._render_detail(spec)
        elif spec.view_type == "form":
            return self._render_form(spec)
        elif spec.view_type == "summary":
            return self._render_summary(spec)
        return self._render_table(spec)

    def _render_table(self, spec: InterfaceSpec) -> str:
        rows = spec.data
        cols = spec.columns

        lines = [f"## {spec.title}", ""]

        if not rows:
            lines.append("No matching records.")
            return "\n".join(lines)

        # Header
        headers = [self._col_label(spec, c) for c in cols]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join("---" for _ in cols) + " |")

        # Rows
        for row in rows:
            values = [self._format_value(row.get(c, "")) for c in cols]
            lines.append("| " + " | ".join(values) + " |")

        lines.append("")
        lines.append(f"*{len(rows)} record(s)*")
        return "\n".join(lines)

    def _render_detail(self, spec: InterfaceSpec) -> str:
        rows = spec.data
        cols = spec.columns

        lines = [f"## {spec.title}", ""]

        for i, row in enumerate(rows):
            if i > 0:
                lines.append("---")
                lines.append("")
            for col in cols:
                label = self._col_label(spec, col)
                val = self._format_value(row.get(col, ""))
                lines.append(f"**{label}:** {val}")

        if not rows:
            lines.append("No matching records.")
        return "\n".join(lines)

    def _render_form(self, spec: InterfaceSpec) -> str:
        cols = spec.columns
        lines = [f"## {spec.title}", ""]
        for col in cols:
            label = self._col_label(spec, col)
            lines.append(f"**{label}:** `[_______________]`")
        lines.append("")
        lines.append("`[ Submit ]`")
        return "\n".join(lines)

    def _render_summary(self, spec: InterfaceSpec) -> str:
        rows = spec.data
        cols = spec.columns

        lines = [f"## {spec.title}", ""]
        lines.append(f"**Total records:** {len(rows)}")
        lines.append("")

        for col in cols:
            values = [r.get(col) for r in rows if r.get(col) is not None]
            if values and all(isinstance(v, (int, float)) for v in values):
                label = self._col_label(spec, col)
                lines.append(
                    f"**{label}:** min={min(values)}, "
                    f"max={max(values)}, avg={sum(values) / len(values):.1f}"
                )

        if not rows:
            lines.append("No data to summarize.")
        return "\n".join(lines)

    def _col_label(self, spec: InterfaceSpec, col: str) -> str:
        return col.replace("_", " ").title()

    def _format_value(self, val: Any) -> str:
        if val is None:
            return "—"
        if isinstance(val, bool):
            return "✓" if val else "✗"
        return str(val)


class JSONRenderer(BaseRenderer):
    """Renders to JSON for API/programmatic consumption."""

    def render(self, spec: InterfaceSpec) -> str:
        output = {
            "title": spec.title,
            "view_type": spec.view_type,
            "columns": spec.columns,
            "filters": spec.filters,
            "sort_by": list(spec.sort_by) if spec.sort_by else None,
            "count": len(spec.data),
            "data": spec.data,
        }
        return json.dumps(output, indent=2, default=str)
