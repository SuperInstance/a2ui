"""InterfaceSpec — the intermediate representation between intent and rendering.

An :class:`InterfaceSpec` is what ``AdaptiveInterface.render()`` produces.
It can be serialized to HTML, Markdown, or JSON via the renderer classes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field as dc_field
from typing import Any, Optional

from .schema import ViewType
from .intent import Intent


@dataclass
class InterfaceComponent:
    """A single component in an interface (column, input, button, etc.).

    Attributes:
        component_type: ``"column"``, ``"input"``, ``"field"``, ``"button"``,
            ``"nav_item"``, ``"actions"``, ``"chart_axis"``.
        label: Display label.
        field: Field name this component is bound to.
        sortable: Whether the user can sort by this column.
        input_type: For form inputs: ``"text"``, ``"number"``, ``"date"``, ``"select"``.
        options: For select inputs.
        reference: For reference inputs, the target entity.
        default: Default value.
        required: Whether the value is required (form inputs only).
        action: Action string for buttons / nav items.
        variant: Button variant (``"primary"``, ``"secondary"``, ``"danger"``).
        actions: For action components, a list of action dicts.
    """

    component_type: str = "field"
    label: str = ""
    field: Optional[str] = None
    sortable: bool = False
    input_type: Optional[str] = None
    options: Optional[list[str]] = None
    reference: Optional[str] = None
    default: Any = None
    required: bool = False
    action: Optional[str] = None
    variant: Optional[str] = None
    actions: Optional[list[dict]] = None
    fields: Optional[list[str]] = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "component_type": self.component_type,
            "label": self.label,
        }
        if self.field:
            d["field"] = self.field
        if self.sortable:
            d["sortable"] = True
        if self.input_type:
            d["input_type"] = self.input_type
        if self.options:
            d["options"] = self.options
        if self.reference:
            d["reference"] = self.reference
        if self.default is not None:
            d["default"] = self.default
        if self.required:
            d["required"] = True
        if self.action:
            d["action"] = self.action
        if self.variant:
            d["variant"] = self.variant
        if self.actions:
            d["actions"] = self.actions
        if self.fields:
            d["fields"] = self.fields
        return d


@dataclass
class InterfaceSpec:
    """A complete interface specification.

    Produced by ``AdaptiveInterface.render()``. Contains everything needed
    to render an interface in any format.
    """

    title: str = ""
    view_type: ViewType = ViewType.LIST
    entity: Optional[str] = None
    components: list[InterfaceComponent] = dc_field(default_factory=list)
    filters: list = dc_field(default_factory=list)
    sort: Any = None
    intent: Optional[Intent] = None

    # -- Serialization helpers ---

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "title": self.title,
            "view_type": self.view_type.value,
            "components": [c.to_dict() for c in self.components],
        }
        if self.entity:
            d["entity"] = self.entity
        if self.filters:
            d["filters"] = [f.to_dict() if hasattr(f, "to_dict") else f for f in self.filters]
        if self.sort:
            d["sort"] = self.sort.to_dict() if hasattr(self.sort, "to_dict") else self.sort
        if self.intent:
            d["intent"] = self.intent.to_dict()
        return d

    def to_json(self, indent: int = 2) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_html(self) -> str:
        """Serialize to an LCARS-inspired HTML document."""
        from .renderers import HTMLRenderer
        return HTMLRenderer().render(self)

    def to_markdown(self) -> str:
        """Serialize to a Markdown document."""
        from .renderers import MarkdownRenderer
        return MarkdownRenderer().render(self)
