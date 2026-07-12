"""Intent parsing for A2UI.

Converts natural-language strings into structured :class:`Intent` objects.
The parser uses keyword-matching heuristics — no external NLP dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import Any, Optional

from .schema import Schema, FieldType, ViewType


@dataclass
class Filter:
    """A single filter on an entity field.

    Attributes:
        field: The field name to filter on.
        operator: One of ``eq``, ``ne``, ``gt``, ``lt``, ``gte``, ``lte``,
            ``in``, ``contains``, ``startswith``.
        value: The comparison value.
    """

    field: str
    operator: str = "eq"
    value: Any = None

    def to_dict(self) -> dict:
        return {"field": self.field, "operator": self.operator, "value": self.value}


@dataclass
class Sort:
    """A sort directive.

    Attributes:
        field: The field name to sort by.
        direction: ``"asc"`` or ``"desc"``.
    """

    field: str
    direction: str = "asc"

    def to_dict(self) -> dict:
        return {"field": self.field, "direction": self.direction}


@dataclass
class Intent:
    """A parsed user intent.

    Attributes:
        action: ``"list"``, ``"create"``, ``"edit"``, ``"detail"``, ``"delete"``, ``"chart"``.
        entity: The target entity name from the schema.
        filters: List of :class:`Filter` objects.
        sort: Optional :class:`Sort` directive.
        raw: The original input string.
        view_hint: Optional :class:`ViewType` suggested by the intent.
    """

    action: str = "list"
    entity: str = ""
    filters: list[Filter] = dc_field(default_factory=list)
    sort: Optional[Sort] = None
    raw: str = ""
    view_hint: Optional[ViewType] = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "action": self.action,
            "entity": self.entity,
            "filters": [f.to_dict() for f in self.filters],
        }
        if self.sort:
            d["sort"] = self.sort.to_dict()
        d["raw"] = self.raw
        if self.view_hint:
            d["view_hint"] = self.view_hint.value
        return d


# --- Keywords ---

_ACTION_KEYWORDS: dict[str, str] = {
    "show": "list",
    "list": "list",
    "display": "list",
    "view": "detail",
    "see": "detail",
    "new": "create",
    "add": "create",
    "create": "create",
    "edit": "edit",
    "modify": "edit",
    "update": "edit",
    "delete": "delete",
    "remove": "delete",
    "chart": "chart",
    "plot": "chart",
    "graph": "chart",
    "dashboard": "list",
}

_SORT_RE = re.compile(
    r"\bsorted\s+by\s+(\w+)(?:\s+(ascending|descending|asc|desc))?",
    re.IGNORECASE,
)
_SORT_RE_ALT = re.compile(
    r"\border\s+by\s+(\w+)(?:\s+(ascending|descending|asc|desc))?",
    re.IGNORECASE,
)

# Comparison patterns: "over 50ft", "under 100", "greater than 50", "less than 10"
_COMP_RE = re.compile(
    r"\b(over|under|above|below|greater\s+than|less\s+than|more\s+than|at\s+least|at\s+most)"
    r"\s+(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

# Equality patterns: "status is active", "status = active"
_EQ_RE = re.compile(
    r"\b(\w+)\s+(?:is|=|equals?|==)\s+(\w+)",
    re.IGNORECASE,
)

# "with" or "where" prefix
_WHERE_RE = re.compile(r"\b(?:where|with|having)\s+(.+)", re.IGNORECASE)


def parse_intent(text: str, schema: Schema) -> Intent:
    """Parse a natural-language string into an :class:`Intent`.

    Args:
        text: Natural language input.
        schema: The data schema, used to resolve entity names and field references.

    Returns:
        A structured :class:`Intent`.
    """
    raw = text.strip()
    lower = raw.lower()

    # Determine action
    action = "list"
    first_word = ""
    words = lower.split()
    if words:
        first_word = words[0]
    if first_word in _ACTION_KEYWORDS:
        action = _ACTION_KEYWORDS[first_word]

    # Also scan all words for action keywords (e.g. "chart" might appear later)
    if action == "list":
        for w in words:
            if w in ("chart", "plot", "graph"):
                action = "chart"
                break

    # Determine entity
    entity = ""
    for ent in schema.entities:
        # Match entity name or label (plural or singular)
        candidates = {ent.name.lower(), ent.label.lower() if ent.label else ""}
        # Add plurals
        for c in list(candidates):
            candidates.add(c + "s")
        for w in words:
            if w in candidates:
                entity = ent.name
                break
        if entity:
            break

    if not entity and schema.entities:
        entity = schema.entities[0].name

    # Parse filters
    filters: list[Filter] = []

    # Comparison filters
    for m in _COMP_RE.finditer(lower):
        op_word = m.group(1).lower().replace(" ", "")
        value = float(m.group(2))
        operator = "gt"
        if op_word in ("over", "above", "greaterthan", "morethan"):
            operator = "gt"
        elif op_word in ("under", "below", "lessthan"):
            operator = "lt"
        elif op_word == "atleast":
            operator = "gte"
        elif op_word == "atmost":
            operator = "lte"

        # Try to find the field being compared
        field_name = _find_field_before(text, m.start(), schema, entity)
        if field_name:
            filters.append(Filter(field=field_name, operator=operator, value=value))
        else:
            # If we know the entity, try numeric fields
            ent = schema.get_entity(entity) if entity else None
            if ent:
                for f in ent.fields:
                    if f.type == FieldType.NUMBER:
                        filters.append(Filter(field=f.name, operator=operator, value=value))
                        break

    # Equality filters
    for m in _EQ_RE.finditer(lower):
        field_name = m.group(1).lower()
        value = m.group(2).strip()
        # Validate against schema
        ent = schema.get_entity(entity) if entity else None
        if ent:
            schema_field = ent.get_field(field_name)
            if schema_field:
                filters.append(Filter(field=schema_field.name, operator="eq", value=value))

    # Parse sort
    sort = None
    for pattern in (_SORT_RE, _SORT_RE_ALT):
        m = pattern.search(lower)
        if m:
            sort_field = m.group(1)
            direction = "asc"
            if m.group(2):
                d = m.group(2).lower()
                if d in ("desc", "descending"):
                    direction = "desc"
            # Validate field name
            ent = schema.get_entity(entity) if entity else None
            if ent and ent.get_field(sort_field):
                sort = Sort(field=sort_field, direction=direction)
            elif ent:
                # Try fuzzy match
                for f in ent.fields:
                    if sort_field in f.name.lower():
                        sort = Sort(field=f.name, direction=direction)
                        break
            break

    # Determine view hint
    view_hint = None
    if action == "chart":
        view_hint = ViewType.CHART
    elif action == "create" or action == "edit":
        view_hint = ViewType.FORM
    elif action == "detail":
        view_hint = ViewType.DETAIL
    elif action == "list":
        view_hint = ViewType.LIST

    return Intent(
        action=action,
        entity=entity,
        filters=filters,
        sort=sort,
        raw=raw,
        view_hint=view_hint,
    )


def _find_field_before(
    text: str, pos: int, schema: Schema, entity: str
) -> Optional[str]:
    """Try to find a field name mentioned before a comparison operator."""
    before = text[:pos].lower().split()
    if not before:
        return None
    ent = schema.get_entity(entity) if entity else None
    if not ent:
        return None
    # Check last 3 words before the operator
    for w in reversed(before[-3:]):
        for f in ent.fields:
            if w == f.name.lower() or w == (f.label or "").lower():
                return f.name
            if w in f.name.lower() and len(w) >= 3:
                return f.name
    return None
