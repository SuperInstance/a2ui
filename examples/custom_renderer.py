"""Example: Custom Renderer (terminal / plain-text).

A2UI ships with HTML, Markdown, and JSON renderers. The architecture is
deliberately open — subclass :class:`BaseRenderer` to produce any other
format. This example emits a plain-text terminal-friendly view.
"""

from a2ui import AdaptiveInterface, Schema, Entity, Field
from a2ui.renderers import BaseRenderer
from a2ui.interface import InterfaceSpec
from a2ui.schema import ViewType


# -- A custom renderer ----------------------------------------------------

class TerminalRenderer(BaseRenderer):
    """Render an InterfaceSpec as ANSI-coloured terminal output.

    Demonstrates the rendering layer is fully pluggable.
    """

    BOLD = "\033[1m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"

    def render(self, spec: InterfaceSpec) -> str:
        lines = []
        lines.append(f"{self.BOLD}{self.CYAN}== {spec.title} =={self.RESET}")
        lines.append(f"{self.MAGENTA}view_type:{self.RESET} {spec.view_type.value}")
        if spec.entity:
            lines.append(f"{self.MAGENTA}entity:{self.RESET} {spec.entity}")

        if spec.filters:
            parts = []
            for f in spec.filters:
                d = f.to_dict() if hasattr(f, "to_dict") else f
                parts.append(f"{d.get('field')} {d.get('operator')} {d.get('value')}")
            lines.append(f"{self.MAGENTA}filters:{self.RESET} " + ", ".join(parts))

        if spec.sort:
            s = spec.sort.to_dict() if hasattr(spec.sort, "to_dict") else spec.sort
            lines.append(f"{self.MAGENTA}sort:{self.RESET} {s.get('field')} {s.get('direction')}")

        lines.append("")

        if spec.view_type == ViewType.LIST:
            lines.extend(self._render_list(spec))
        elif spec.view_type == ViewType.FORM:
            lines.extend(self._render_form(spec))
        elif spec.view_type == ViewType.DETAIL:
            lines.extend(self._render_detail(spec))
        elif spec.view_type == ViewType.CHART:
            lines.append(f"{self.YELLOW}[chart placeholder]{self.RESET}")
        elif spec.view_type == ViewType.DASHBOARD:
            lines.extend(self._render_dashboard(spec))

        return "\n".join(lines)

    def _render_list(self, spec: InterfaceSpec) -> list[str]:
        columns = [c for c in spec.components if c.component_type == "column"]
        actions = next((c for c in spec.components if c.component_type == "actions"), None)

        # Column widths from label length
        widths = [len(c.label) for c in columns]
        if actions:
            widths.append(len(actions.label))

        lines = []
        # Header
        header_parts = []
        for c, w in zip(columns, widths):
            header_parts.append(f"{self.BOLD}{c.label:<{w}}{self.RESET}")
        if actions and actions.label:
            header_parts.append(f"{self.BOLD}{actions.label}{self.RESET}")
        lines.append(" | ".join(header_parts))
        # Separator
        lines.append("-+-".join("-" * w for w in widths))
        # Empty row
        row_parts = ["—" * w for w in widths]
        lines.append(" | ".join(row_parts))
        return lines

    def _render_form(self, spec: InterfaceSpec) -> list[str]:
        lines = []
        for c in spec.components:
            if c.component_type == "input":
                marker = "*" if c.required else " "
                itype = c.input_type or "text"
                extras = ""
                if c.options:
                    extras = f" (options: {', '.join(c.options)})"
                if c.reference:
                    extras = f" (ref: {c.reference})"
                if c.default is not None:
                    extras += f" (default: {c.default})"
                lines.append(f"  {marker} {self.BOLD}{c.label}{self.RESET}: {itype}{extras}")
            elif c.component_type == "button":
                lines.append(f"  [{c.label}]")
        return lines

    def _render_detail(self, spec: InterfaceSpec) -> list[str]:
        lines = []
        for c in spec.components:
            if c.component_type == "field":
                lines.append(f"  {self.BOLD}{c.label}:{self.RESET} —")
            elif c.component_type == "button":
                lines.append(f"  [{c.label}]")
        return lines

    def _render_dashboard(self, spec: InterfaceSpec) -> list[str]:
        lines = []
        for c in spec.components:
            lines.append(f"  ▢ {c.label}: —")
        return lines


# -- A schema + driving the renderer ---------------------------------------

def build_schema() -> Schema:
    return Schema(
        entities=[
            Entity(
                name="vessel",
                label="Vessel",
                fields=[
                    Field(name="name", type="text", label="Vessel Name", required=True),
                    Field(name="length", type="number", label="Length", unit="ft"),
                    Field(
                        name="status",
                        type="enum",
                        label="Status",
                        options=["active", "docked", "maintenance"],
                    ),
                ],
            ),
        ],
    )


def main():
    schema = build_schema()
    ai = AdaptiveInterface(schema)
    renderer = TerminalRenderer()

    intents = [
        "show active vessels over 50 sorted by length desc",
        "new vessel",
        "view vessel",
    ]

    for intent in intents:
        print(f"\n>>> Intent: {intent!r}\n")
        spec = ai.render(intent)
        print(renderer.render(spec))


if __name__ == "__main__":
    main()
