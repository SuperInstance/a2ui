"""Schema definitions for A2UI.

Describes data entities, their fields, and the view types
the adaptive interface can generate.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from enum import Enum
from typing import Any, Optional


class FieldType(str, Enum):
    """Supported field types in a schema."""

    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    ENUM = "enum"
    REFERENCE = "reference"


class ViewType(str, Enum):
    """Supported view types the interface can produce."""

    LIST = "list"
    DETAIL = "detail"
    FORM = "form"
    DASHBOARD = "dashboard"
    CHART = "chart"


@dataclass
class Field:
    """A single field on an entity.

    Attributes:
        name: Machine name of the field.
        type: One of :class:`FieldType`.
        label: Human-readable label (defaults to ``name.title()``).
        required: Whether this field must have a value.
        unit: Optional unit suffix (e.g. ``"ft"``, ``"kg"``).
        options: For ``enum`` fields, the list of choices.
        reference: For ``reference`` fields, the target entity name.
        default: Default value for forms.
    """

    name: str
    type: FieldType | str = FieldType.TEXT
    label: Optional[str] = None
    required: bool = False
    unit: Optional[str] = None
    options: Optional[list[str]] = None
    reference: Optional[str] = None
    default: Any = None

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = FieldType(self.type)
        if self.label is None:
            self.label = self.name.replace("_", " ").title()

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "type": self.type.value,
            "label": self.label,
            "required": self.required,
        }
        if self.unit:
            d["unit"] = self.unit
        if self.options:
            d["options"] = self.options
        if self.reference:
            d["reference"] = self.reference
        if self.default is not None:
            d["default"] = self.default
        return d


@dataclass
class Entity:
    """A data entity in the schema.

    Attributes:
        name: Machine name (e.g. ``"vessel"``).
        label: Human-readable label.
        fields: List of :class:`Field` objects.
        primary_key: Name of the field that serves as primary key.
    """

    name: str
    label: Optional[str] = None
    fields: list[Field] = dc_field(default_factory=list)
    primary_key: Optional[str] = None

    def __post_init__(self):
        if self.label is None:
            self.label = self.name.replace("_", " ").title()
        if self.primary_key is None and self.fields:
            self.primary_key = self.fields[0].name

    def get_field(self, name: str) -> Optional[Field]:
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "primary_key": self.primary_key,
            "fields": [f.to_dict() for f in self.fields],
        }


@dataclass
class Schema:
    """The full data schema — a collection of entities.

    This is the top-level object passed to :class:`AdaptiveInterface`.
    """

    entities: list[Entity] = dc_field(default_factory=list)

    def get_entity(self, name: str) -> Optional[Entity]:
        for ent in self.entities:
            if ent.name == name or (ent.label and ent.label.lower() == name.lower()):
                return ent
        return None

    def entity_names(self) -> list[str]:
        return [e.name for e in self.entities]

    def to_dict(self) -> dict:
        return {"entities": [e.to_dict() for e in self.entities]}
