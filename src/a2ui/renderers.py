"""Renderers for A2UI InterfaceSpecs.

Three output formats are supported:

- :class:`HTMLRenderer` — LCARS-inspired HTML with inline CSS
- :class:`MarkdownRenderer` — Clean Markdown for terminals and docs
- :class:`JSONRenderer` — Structured JSON for programmatic consumption
"""

from __future__ import annotations

import json
from typing import Any

from .interface import InterfaceSpec, InterfaceComponent
from .schema import ViewType


class BaseRenderer:
    """Base class for renderers."""

    def render(self, spec: InterfaceSpec) -> str:  # pragma: no cover
        raise NotImplementedError


class HTMLRenderer(BaseRenderer):
    """Render an :class:`InterfaceSpec` to LCARS-inspired HTML.

    The output is a complete, self-contained HTML document with inline CSS.
    The aesthetic is dark-background, bold colors, rounded elements —
    inspired by the Star Trek LCARS computer interface.
    """

    def render(self, spec: InterfaceSpec) -> str:
        body = self._render_body(spec)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{self._esc(spec.title)}</title>
<style>
{self._css()}
</style>
</head>
<body>
<div class="lcars-container">
  <header class="lcars-header">
    <div class="lcars-bar"></div>
    <h1>{self._esc(spec.title)}</h1>
    <div class="lcars-bar right"></div>
  </header>
  <main class="lcars-main">
{body}
  </main>
  <footer class="lcars-footer">
    <div class="lcars-bar"></div>
    <span class="lcars-stardate">A2UI · {self._esc(spec.view_type.value)}</span>
  </footer>
</div>
</body>
</html>"""

    def _render_body(self, spec: InterfaceSpec) -> str:
        if spec.view_type == ViewType.LIST:
            return self._render_list(spec)
        elif spec.view_type == ViewType.FORM:
            return self._render_form(spec)
        elif spec.view_type == ViewType.DETAIL:
            return self._render_detail(spec)
        elif spec.view_type == ViewType.CHART:
            return self._render_chart(spec)
        elif spec.view_type == ViewType.DASHBOARD:
            return self._render_dashboard(spec)
        return ""

    def _render_list(self, spec: InterfaceSpec) -> str:
        columns = [c for c in spec.components if c.component_type == "column"]
        actions = next((c for c in spec.components if c.component_type == "actions"), None)

        header_cells = "".join(
            f'<th class="lcars-th">{self._esc(c.label)}</th>' for c in columns
        )
        if actions:
            header_cells += f'<th class="lcars-th">{self._esc(actions.label)}</th>'

        # Sample empty row
        row_cells = "".join(
            f'<td class="lcars-td" data-field="{self._esc(c.field or "")}">—</td>'
            for c in columns
        )
        if actions:
            action_buttons = ""
            if actions.actions:
                for a in actions.actions:
                    action_buttons += (
                        f'<button class="lcars-btn-sm" data-action="{self._esc(a.get("action", ""))}">'
                        f'{self._esc(a["label"])}</button>'
                    )
            row_cells += f'<td class="lcars-td">{action_buttons}</td>'

        filter_html = ""
        if spec.filters:
            filter_parts = []
            for f in spec.filters:
                if hasattr(f, "to_dict"):
                    fd = f.to_dict()
                else:
                    fd = f
                filter_parts.append(
                    f'<span class="lcars-filter">{self._esc(fd.get("field", ""))} '
                    f'{self._esc(fd.get("operator", ""))} {self._esc(str(fd.get("value", "")))}</span>'
                )
            filter_html = f'<div class="lcars-filters">{" · ".join(filter_parts)}</div>'

        sort_html = ""
        if spec.sort:
            sd = spec.sort.to_dict() if hasattr(spec.sort, "to_dict") else spec.sort
            sort_html = (
                f'<div class="lcars-sort">Sorted by {self._esc(sd.get("field", ""))} '
                f'{self._esc(sd.get("direction", ""))}</div>'
            )

        return f"""{filter_html}{sort_html}
<table class="lcars-table">
  <thead><tr>{header_cells}</tr></thead>
  <tbody>
    <tr>{row_cells}</tr>
  </tbody>
</table>"""

    def _render_form(self, spec: InterfaceSpec) -> str:
        rows = []
        for c in spec.components:
            if c.component_type == "input":
                rows.append(self._render_input(c))
            elif c.component_type == "button":
                rows.append(
                    f'<button class="lcars-btn lcars-btn-{self._esc(c.variant or "primary")}">'
                    f'{self._esc(c.label)}</button>'
                )
        return "\n".join(f'<div class="lcars-form-row">{r}</div>' for r in rows)

    def _render_input(self, c: InterfaceComponent) -> str:
        label = self._esc(c.label)
        field_name = self._esc(c.field or c.label)
        if c.input_type == "select" and c.options:
            opts = "".join(
                f'<option value="{self._esc(o)}">{self._esc(o)}</option>' for o in c.options
            )
            return f'<label class="lcars-label">{label}</label><select class="lcars-input" name="{field_name}">{opts}</select>'
        elif c.input_type == "reference" and c.reference:
            return (
                f'<label class="lcars-label">{label}</label>'
                f'<input class="lcars-input" type="text" name="{field_name}" '
                f'data-reference="{self._esc(c.reference)}" placeholder="Search {self._esc(c.reference)}...">'
            )
        else:
            itype = self._esc(c.input_type or "text")
            default = f' value="{self._esc(str(c.default))}"' if c.default is not None else ""
            req = " required" if c.required else ""
            field_id = f' id="field-{field_name}"'
            return (
                f'<label class="lcars-label" for="field-{field_name}">{label}</label>'
                f'<input class="lcars-input" type="{itype}" name="{field_name}"{field_id}{default}{req}>'
            )

    def _render_detail(self, spec: InterfaceSpec) -> str:
        rows = []
        for c in spec.components:
            if c.component_type == "field":
                rows.append(
                    f'<div class="lcars-detail-row">'
                    f'<span class="lcars-detail-label">{self._esc(c.label)}</span>'
                    f'<span class="lcars-detail-value" data-field="{self._esc(c.field or "")}">—</span>'
                    f'</div>'
                )
            elif c.component_type == "button":
                rows.append(
                    f'<button class="lcars-btn lcars-btn-{self._esc(c.variant or "primary")}" '
                    f'data-action="{self._esc(c.action or "")}">{self._esc(c.label)}</button>'
                )
        return "\n".join(rows)

    def _render_chart(self, spec: InterfaceSpec) -> str:
        return '<div class="lcars-chart-placeholder">Chart view — bind to data source</div>'

    def _render_dashboard(self, spec: InterfaceSpec) -> str:
        cards = []
        for c in spec.components:
            cards.append(
                f'<div class="lcars-card"><h3>{self._esc(c.label)}</h3>'
                f'<div data-field="{self._esc(c.field or "")}">—</div></div>'
            )
        return f'<div class="lcars-dashboard">{" ".join(cards)}</div>'

    @staticmethod
    def _esc(text: str) -> str:
        if text is None:
            return ""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    @staticmethod
    def _css() -> str:
        return """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #000; color: #ffcc00; font-family: 'Helvetica Neue', sans-serif; }
.lcars-container { max-width: 960px; margin: 0 auto; padding: 20px; }
.lcars-header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
.lcars-bar { flex: 1; height: 48px; background: #cc66cc; border-radius: 24px; }
.lcars-bar.right { background: #ff9933; }
.lcars-header h1 { color: #ffcc00; font-size: 1.4rem; white-space: nowrap; }
.lcars-main { background: #110022; border-radius: 16px; padding: 24px; min-height: 300px; }
.lcars-table { width: 100%; border-collapse: separate; border-spacing: 0; }
.lcars-th { background: #5544aa; color: #fff; padding: 10px 14px; text-align: left; border-radius: 8px 8px 0 0; }
.lcars-td { padding: 10px 14px; border-bottom: 1px solid #332255; color: #ffcc00; }
.lcars-btn { background: #ff9933; color: #000; border: none; border-radius: 20px; padding: 10px 28px; font-size: 1rem; cursor: pointer; margin: 4px; }
.lcars-btn-primary { background: #ff9933; }
.lcars-btn-secondary { background: #5544aa; color: #fff; }
.lcars-btn-danger { background: #cc3333; color: #fff; }
.lcars-btn-sm { background: #5544aa; color: #fff; border: none; border-radius: 12px; padding: 4px 12px; font-size: 0.75rem; cursor: pointer; margin: 2px; }
.lcars-form-row { margin-bottom: 16px; }
.lcars-label { display: block; color: #ff9933; margin-bottom: 4px; font-size: 0.85rem; }
.lcars-input { width: 100%; background: #220044; border: 1px solid #5544aa; border-radius: 8px; padding: 10px; color: #ffcc00; font-size: 1rem; }
.lcars-input:focus { outline: 2px solid #ff9933; }
.lcars-detail-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #332255; }
.lcars-detail-label { color: #ff9933; }
.lcars-detail-value { color: #ffcc00; }
.lcars-filters { margin-bottom: 12px; color: #cc66cc; font-size: 0.85rem; }
.lcars-sort { margin-bottom: 12px; color: #5599ff; font-size: 0.85rem; }
.lcars-card { background: #220044; border-radius: 12px; padding: 16px; }
.lcars-dashboard { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; }
.lcars-footer { display: flex; align-items: center; gap: 16px; margin-top: 24px; }
.lcars-stardate { color: #5599ff; font-size: 0.75rem; white-space: nowrap; }
.lcars-chart-placeholder { text-align: center; padding: 60px 0; color: #5599ff; }
"""


class MarkdownRenderer(BaseRenderer):
    """Render an :class:`InterfaceSpec` to Markdown."""

    def render(self, spec: InterfaceSpec) -> str:
        lines = [f"# {spec.title}", ""]

        if spec.filters:
            lines.append("**Filters:**")
            for f in spec.filters:
                fd = f.to_dict() if hasattr(f, "to_dict") else f
                lines.append(f"- `{fd.get('field', '')}` {fd.get('operator', '')} `{fd.get('value', '')}`")
            lines.append("")

        if spec.sort:
            sd = spec.sort.to_dict() if hasattr(spec.sort, "to_dict") else spec.sort
            lines.append(f"**Sort:** {sd.get('field', '')} ({sd.get('direction', '')})")
            lines.append("")

        if spec.view_type == ViewType.LIST:
            lines.append(self._render_list(spec))
        elif spec.view_type == ViewType.FORM:
            lines.append(self._render_form(spec))
        elif spec.view_type == ViewType.DETAIL:
            lines.append(self._render_detail(spec))
        elif spec.view_type == ViewType.CHART:
            lines.append("*Chart view — bind to data source*\n")
        elif spec.view_type == ViewType.DASHBOARD:
            lines.append(self._render_dashboard(spec))

        return "\n".join(lines)

    def _render_list(self, spec: InterfaceSpec) -> str:
        columns = [c for c in spec.components if c.component_type == "column"]
        actions = next((c for c in spec.components if c.component_type == "actions"), None)

        if not columns:
            return "*No columns defined*"

        header = "| " + " | ".join(c.label for c in columns)
        if actions:
            header += f" | {actions.label}"
        header += " |"

        separator = "| " + " | ".join("---" for _ in columns)
        if actions:
            separator += " | ---"
        separator += " |"

        # One empty row
        row = "| " + " | ".join("—" for _ in columns)
        if actions and actions.actions:
            row += " | " + " ".join(a["label"] for a in actions.actions)
        row += " |"

        return "\n".join([header, separator, row])

    def _render_form(self, spec: InterfaceSpec) -> str:
        lines = ["| Field | Type | Required |", "| --- | --- | --- |"]
        for c in spec.components:
            if c.component_type == "input":
                itype = c.input_type or "text"
                if c.options:
                    itype = f"select ({', '.join(c.options)})"
                lines.append(f"| {c.label} | {itype} | {'Yes' if c.required else ''} |")
            elif c.component_type == "button":
                lines.append(f"\n**[{c.label}]**")
        return "\n".join(lines)

    def _render_detail(self, spec: InterfaceSpec) -> str:
        lines = []
        for c in spec.components:
            if c.component_type == "field":
                lines.append(f"**{c.label}:** —")
        for c in spec.components:
            if c.component_type == "button":
                lines.append(f"\n**[{c.label}]**")
        return "\n".join(lines)

    def _render_dashboard(self, spec: InterfaceSpec) -> str:
        lines = []
        for c in spec.components:
            lines.append(f"### {c.label}\n—")
        return "\n".join(lines)


class JSONRenderer(BaseRenderer):
    """Render an :class:`InterfaceSpec` to JSON."""

    def render(self, spec: InterfaceSpec, indent: int = 2) -> str:
        return json.dumps(spec.to_dict(), indent=indent)
