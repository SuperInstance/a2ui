"""A2UI — Adaptive Interface. The Whistle Layer."""

from .schema import Schema, Entity, Field, FieldType, ViewType
from .intent import Intent, parse_intent
from .renderers import HTMLRenderer, MarkdownRenderer, JSONRenderer
from .interface import InterfaceSpec, InterfaceComponent

__version__ = "0.1.0"

__all__ = [
    "AdaptiveInterface",
    "Schema",
    "Entity",
    "Field",
    "FieldType",
    "ViewType",
    "Intent",
    "parse_intent",
    "InterfaceSpec",
    "InterfaceComponent",
    "HTMLRenderer",
    "MarkdownRenderer",
    "JSONRenderer",
]


class AdaptiveInterface:
    """The main entry point for A2UI.

    Give it a schema, then call ``render(intent_string)`` to get
    an :class:`InterfaceSpec` you can turn into HTML, Markdown, or JSON.
    """

    def __init__(self, schema: Schema):
        self.schema = schema

    def render(self, intent_str: str) -> InterfaceSpec:
        """Parse a natural-language intent and produce an InterfaceSpec.

        Args:
            intent_str: Natural language like ``"show all vessels over 50ft"``.

        Returns:
            An :class:`InterfaceSpec` ready to render.
        """
        intent = parse_intent(intent_str, self.schema)
        return self._build_spec(intent)

    def render_intent(self, intent: Intent) -> InterfaceSpec:
        """Render an already-parsed :class:`Intent`."""
        return self._build_spec(intent)

    def _build_spec(self, intent: Intent) -> InterfaceSpec:
        entity = self.schema.get_entity(intent.entity)
        if entity is None:
            # Unknown entity — produce a navigation list
            components = []
            for ent in self.schema.entities:
                components.append(
                    InterfaceComponent(
                        component_type="nav_item",
                        label=ent.label or ent.name,
                        action=f"show {ent.name}",
                    )
                )
            return InterfaceSpec(
                title="Select an entity",
                view_type=ViewType.LIST,
                components=components,
                intent=intent,
            )

        if intent.action == "create" or intent.action == "edit":
            return self._build_form(entity, intent)
        elif intent.action == "detail":
            return self._build_detail(entity, intent)
        elif intent.action == "chart" or intent.view_hint == ViewType.CHART:
            return self._build_chart(entity, intent)
        else:
            return self._build_list(entity, intent)

    def _build_list(self, entity: Entity, intent: Intent) -> InterfaceSpec:
        components = []
        for field in entity.fields:
            components.append(
                InterfaceComponent(
                    component_type="column",
                    label=field.label or field.name,
                    field=field.name,
                    sortable=field.type in (FieldType.TEXT, FieldType.NUMBER, FieldType.DATE),
                )
            )
        # Add row actions
        components.append(
            InterfaceComponent(
                component_type="actions",
                label="Actions",
                actions=[
                    {"label": "View", "action": f"detail {entity.name}"},
                    {"label": "Edit", "action": f"edit {entity.name}"},
                ],
            )
        )
        return InterfaceSpec(
            title=f"{entity.label or entity.name.title()}s",
            view_type=ViewType.LIST,
            entity=entity.name,
            components=components,
            filters=intent.filters,
            sort=intent.sort,
            intent=intent,
        )

    def _build_form(self, entity: Entity, intent: Intent) -> InterfaceSpec:
        components = []
        for field in entity.fields:
            comp = InterfaceComponent(
                component_type="input",
                label=field.label or field.name,
                field=field.name,
                input_type=self._input_type_for(field),
                required=field.required,
            )
            if field.type == FieldType.ENUM:
                comp.options = field.options
            if field.type == FieldType.REFERENCE:
                comp.reference = field.reference
            if field.default is not None:
                comp.default = field.default
            components.append(comp)
        components.append(
            InterfaceComponent(
                component_type="button",
                label="Submit",
                action="submit",
                variant="primary",
            )
        )
        return InterfaceSpec(
            title=f"{'Edit' if intent.action == 'edit' else 'New'} {entity.label or entity.name}",
            view_type=ViewType.FORM,
            entity=entity.name,
            components=components,
            intent=intent,
        )

    def _build_detail(self, entity: Entity, intent: Intent) -> InterfaceSpec:
        components = []
        for field in entity.fields:
            components.append(
                InterfaceComponent(
                    component_type="field",
                    label=field.label or field.name,
                    field=field.name,
                )
            )
        components.append(
            InterfaceComponent(
                component_type="button",
                label="Edit",
                action=f"edit {entity.name}",
                variant="secondary",
            )
        )
        return InterfaceSpec(
            title=entity.label or entity.name.title(),
            view_type=ViewType.DETAIL,
            entity=entity.name,
            components=components,
            intent=intent,
        )

    def _build_chart(self, entity: Entity, intent: Intent) -> InterfaceSpec:
        numeric_fields = [f for f in entity.fields if f.type == FieldType.NUMBER]
        components = [
            InterfaceComponent(
                component_type="chart_axis",
                label="Values",
                fields=[f.name for f in numeric_fields],
            )
        ]
        return InterfaceSpec(
            title=f"{entity.label or entity.name.title()} Chart",
            view_type=ViewType.CHART,
            entity=entity.name,
            components=components,
            intent=intent,
        )

    @staticmethod
    def _input_type_for(field: Field) -> str:
        mapping = {
            FieldType.TEXT: "text",
            FieldType.NUMBER: "number",
            FieldType.DATE: "date",
            FieldType.ENUM: "select",
            FieldType.REFERENCE: "reference",
        }
        return mapping.get(field.type, "text")

    # -- Renderer convenience methods ---

    def to_html(self, intent_str: str) -> str:
        return self.render(intent_str).to_html()

    def to_markdown(self, intent_str: str) -> str:
        return self.render(intent_str).to_markdown()

    def to_json(self, intent_str: str) -> str:
        return self.render(intent_str).to_json()
