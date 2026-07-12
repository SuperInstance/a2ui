"""
Core AdaptiveInterface — the main entry point.

User states intent → system reads schema → generates appropriate interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .schema import Schema
from .intent import Intent, IntentParser


@dataclass
class InterfaceSpec:
    """A generated interface specification — the output of the Whistle Layer."""

    intent: Intent
    view_type: str  # "table", "detail", "form", "summary"
    columns: list[str] = field(default_factory=list)
    filters: list[dict] = field(default_factory=list)
    sort_by: Optional[tuple[str, str]] = None  # (field, direction)
    title: str = ""
    data: list[dict] = field(default_factory=list)
    actions: list[str] = field(default_factory=lambda: ["view", "edit"])
    format: str = "html"  # html, markdown, json
    _schema: Optional[Schema] = None  # reference back to schema for label resolution

    def render(self, format: Optional[str] = None) -> str:
        """Render this spec to the requested format."""
        # Lazy import to avoid circular dependency
        from .renderers import HTMLRenderer, MarkdownRenderer, JSONRenderer

        fmt = format or self.format
        if fmt == "html":
            return HTMLRenderer().render(self)
        elif fmt == "markdown":
            return MarkdownRenderer().render(self)
        elif fmt == "json":
            return JSONRenderer().render(self)
        raise ValueError(f"Unknown format: {fmt}")

    def __repr__(self) -> str:
        return (
            f"InterfaceSpec(view={self.view_type}, entity={self.intent.entity}, "
            f"cols={len(self.columns)}, rows={len(self.data)})"
        )


class AdaptiveInterface:
    """
    The main entry point for A2UI.

        >>> ai = AdaptiveInterface(schema)
        >>> spec = ai.render("show me all vessels with engine hours over 5000")
        >>> print(spec.render("html"))
    """

    def __init__(self, schema: dict | Schema, data: Optional[dict[str, list[dict]]] = None):
        self.schema = schema if isinstance(schema, Schema) else Schema(schema)
        self.data = data or {}
        self._parser = IntentParser(self.schema)

    def parse(self, natural_language: str) -> Intent:
        """Parse natural language into a structured Intent."""
        return self._parser.parse(natural_language)

    def render(self, natural_language: str, format: str = "html") -> str:
        """Parse intent from natural language and render a complete interface."""
        spec = self.ask(natural_language)
        return spec.render(format)

    def ask(self, natural_language: str) -> InterfaceSpec:
        """Parse intent and build an InterfaceSpec (without rendering)."""
        intent = self._parser.parse(natural_language)
        return self._build_spec(intent)

    def _build_spec(self, intent: Intent) -> InterfaceSpec:
        """Build a complete InterfaceSpec from an Intent."""
        entity_schema = self.schema.get_entity(intent.entity)

        view_type = self._determine_view(intent)

        if intent.fields:
            columns = intent.fields
        else:
            columns = self._default_columns(entity_schema)

        entity_data = self.data.get(intent.entity, [])
        filtered = self._apply_filters(entity_data, intent.filters)

        if intent.sort_by:
            filtered = self._apply_sort(filtered, intent.sort_by)

        title = self._build_title(intent)

        return InterfaceSpec(
            intent=intent,
            view_type=view_type,
            columns=columns,
            filters=intent.filters,
            sort_by=intent.sort_by,
            title=title,
            data=filtered,
            format="html",
            _schema=self.schema,
        )

    def _determine_view(self, intent: Intent) -> str:
        """Map intent action to a view type."""
        action = intent.action.lower()
        if action in ("show", "list", "find", "search", "which", "get"):
            return "table"
        elif action in ("detail", "inspect"):
            return "detail"
        elif action in ("add", "create", "new", "edit", "update"):
            return "form"
        elif action in ("summary", "overview", "stats"):
            return "summary"
        return "table"

    def _default_columns(self, entity_schema: dict) -> list[str]:
        """Pick sensible default columns."""
        fields = entity_schema.get("fields", {})
        pk = entity_schema.get("primary_key")
        cols = []
        if pk and pk in fields:
            cols.append(pk)
        for name in fields:
            if name not in cols:
                cols.append(name)
            if len(cols) >= 6:
                break
        return cols

    def _apply_filters(self, data: list[dict], filters: list[dict]) -> list[dict]:
        """Apply filter conditions to the data."""
        result = data
        for f in filters:
            field_name = f["field"]
            op = f["op"]
            value = f["value"]
            result = [
                row for row in result
                if self._matches(row.get(field_name), op, value)
            ]
        return result

    def _matches(self, actual: Any, op: str, expected: Any) -> bool:
        """Check if a value matches a filter condition."""
        try:
            if op == "eq":
                return actual == expected
            elif op == "ne":
                return actual != expected
            elif op == "gt":
                return actual is not None and float(actual) > float(expected)
            elif op == "gte":
                return actual is not None and float(actual) >= float(expected)
            elif op == "lt":
                return actual is not None and float(actual) < float(expected)
            elif op == "lte":
                return actual is not None and float(actual) <= float(expected)
            elif op == "contains":
                return expected.lower() in str(actual).lower()
            elif op == "in":
                return actual in expected
        except (TypeError, ValueError):
            return False
        return False

    def _apply_sort(self, data: list[dict], sort_by: tuple[str, str]) -> list[dict]:
        """Sort data by field and direction."""
        field_name, direction = sort_by
        reverse = direction == "desc"
        try:
            return sorted(data, key=lambda r: (r.get(field_name) is None, r.get(field_name)), reverse=reverse)
        except TypeError:
            return sorted(data, key=lambda r: str(r.get(field_name, "")), reverse=reverse)

    def _build_title(self, intent: Intent) -> str:
        """Generate a human-readable title for the interface."""
        parts = []
        action_labels = {
            "show": "Showing",
            "list": "Listing",
            "find": "Found",
            "search": "Searching",
            "which": "Matching",
            "get": "Retrieving",
        }
        label = action_labels.get(intent.action.lower(), intent.action.capitalize())
        parts.append(f"{label} {intent.entity}")
        if intent.filters:
            filter_descs = []
            for f in intent.filters:
                op_labels = {
                    "eq": "=",
                    "ne": "≠",
                    "gt": ">",
                    "gte": "≥",
                    "lt": "<",
                    "lte": "≤",
                    "contains": "contains",
                    "in": "in",
                }
                op_label = op_labels.get(f["op"], f["op"])
                filter_descs.append(f"{f['field']} {op_label} {f['value']}")
            parts.append("where " + " AND ".join(filter_descs))
        if intent.sort_by:
            direction_label = "descending" if intent.sort_by[1] == "desc" else "ascending"
            parts.append(f"sorted by {intent.sort_by[0]} ({direction_label})")
        return " — ".join(parts)
