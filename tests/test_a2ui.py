"""Tests for A2UI — Adaptive Interface."""

import json
import pytest

from a2ui import (
    AdaptiveInterface,
    Schema,
    Entity,
    Field,
    FieldType,
    ViewType,
    Intent,
    parse_intent,
    InterfaceSpec,
    InterfaceComponent,
    HTMLRenderer,
    MarkdownRenderer,
    JSONRenderer,
)
from a2ui.intent import Filter, Sort


# --- Fixtures ---

@pytest.fixture
def vessel_schema():
    return Schema(
        entities=[
            Entity(
                name="vessel",
                label="Vessel",
                fields=[
                    Field(name="name", type="text", label="Vessel Name", required=True),
                    Field(name="length", type="number", label="Length", unit="ft"),
                    Field(name="home_port", type="text", label="Home Port"),
                    Field(name="status", type="enum", label="Status",
                          options=["active", "docked", "maintenance"]),
                    Field(name="acquired", type="date", label="Acquired Date"),
                ],
            ),
            Entity(
                name="catch",
                label="Catch Log",
                fields=[
                    Field(name="species", type="text", label="Species"),
                    Field(name="weight", type="number", label="Weight", unit="kg"),
                    Field(name="vessel_id", type="reference", label="Vessel", reference="vessel"),
                ],
            ),
        ],
    )


@pytest.fixture
def ai(vessel_schema):
    return AdaptiveInterface(vessel_schema)


# --- Schema Tests ---

class TestSchema:
    def test_field_type_enum(self):
        f = Field(name="status", type="enum", options=["a", "b"])
        assert f.type == FieldType.ENUM
        assert f.options == ["a", "b"]

    def test_field_default_label(self):
        f = Field(name="home_port", type="text")
        assert f.label == "Home Port"

    def test_entity_get_field(self):
        e = Entity(name="vessel", fields=[Field(name="length", type="number")])
        assert e.get_field("length") is not None
        assert e.get_field("nonexistent") is None

    def test_entity_default_primary_key(self):
        e = Entity(name="vessel", fields=[Field(name="id", type="text"), Field(name="name", type="text")])
        assert e.primary_key == "id"

    def test_schema_get_entity(self, vessel_schema):
        assert vessel_schema.get_entity("vessel") is not None
        assert vessel_schema.get_entity("Vessel") is not None
        assert vessel_schema.get_entity("Vessels") is not None
        assert vessel_schema.get_entity("nonexistent") is None

    def test_schema_entity_names(self, vessel_schema):
        assert "vessel" in vessel_schema.entity_names()
        assert "catch" in vessel_schema.entity_names()

    def test_field_to_dict(self):
        f = Field(name="weight", type="number", label="Weight", unit="kg", required=True)
        d = f.to_dict()
        assert d["name"] == "weight"
        assert d["type"] == "number"
        assert d["unit"] == "kg"
        assert d["required"] is True

    def test_entity_to_dict(self):
        e = Entity(name="vessel", fields=[Field(name="name", type="text")])
        d = e.to_dict()
        assert d["name"] == "vessel"
        assert len(d["fields"]) == 1

    def test_schema_to_dict(self, vessel_schema):
        d = vessel_schema.to_dict()
        assert "entities" in d
        assert len(d["entities"]) == 2


# --- Intent Parsing Tests ---

class TestIntentParsing:
    def test_list_intent(self, vessel_schema):
        intent = parse_intent("show all vessels", vessel_schema)
        assert intent.action == "list"
        assert intent.entity == "vessel"

    def test_create_intent(self, vessel_schema):
        intent = parse_intent("new vessel", vessel_schema)
        assert intent.action == "create"
        assert intent.entity == "vessel"

    def test_edit_intent(self, vessel_schema):
        intent = parse_intent("edit vessel", vessel_schema)
        assert intent.action == "edit"

    def test_detail_intent(self, vessel_schema):
        intent = parse_intent("view vessel", vessel_schema)
        assert intent.action == "detail"

    def test_chart_intent(self, vessel_schema):
        intent = parse_intent("chart vessels", vessel_schema)
        assert intent.action == "chart"
        assert intent.view_hint == ViewType.CHART

    def test_entity_resolution_plural(self, vessel_schema):
        intent = parse_intent("show vessels", vessel_schema)
        assert intent.entity == "vessel"

    def test_entity_resolution_label(self, vessel_schema):
        intent = parse_intent("show catch logs", vessel_schema)
        assert intent.entity == "catch"

    def test_comparison_filter(self, vessel_schema):
        intent = parse_intent("show vessels over 50", vessel_schema)
        assert len(intent.filters) >= 1
        assert intent.filters[0].operator == "gt"
        assert intent.filters[0].value == 50.0

    def test_comparison_filter_under(self, vessel_schema):
        intent = parse_intent("show vessels under 100", vessel_schema)
        assert len(intent.filters) >= 1
        assert any(f.operator == "lt" for f in intent.filters)

    def test_equality_filter(self, vessel_schema):
        intent = parse_intent("show vessels where status is active", vessel_schema)
        eq_filters = [f for f in intent.filters if f.operator == "eq"]
        assert len(eq_filters) >= 1
        assert eq_filters[0].field == "status"
        assert eq_filters[0].value == "active"

    def test_sort_parsing(self, vessel_schema):
        intent = parse_intent("show vessels sorted by length descending", vessel_schema)
        assert intent.sort is not None
        assert intent.sort.field == "length"
        assert intent.sort.direction == "desc"

    def test_sort_asc(self, vessel_schema):
        intent = parse_intent("show vessels sorted by name asc", vessel_schema)
        assert intent.sort is not None
        assert intent.sort.direction == "asc"

    def test_order_by(self, vessel_schema):
        intent = parse_intent("show vessels order by length", vessel_schema)
        assert intent.sort is not None
        assert intent.sort.field == "length"

    def test_intent_to_dict(self, vessel_schema):
        intent = parse_intent("show vessels over 50 sorted by length", vessel_schema)
        d = intent.to_dict()
        assert d["action"] == "list"
        assert d["entity"] == "vessel"
        assert "filters" in d

    def test_raw_preserved(self, vessel_schema):
        raw = "show all active vessels sorted by length"
        intent = parse_intent(raw, vessel_schema)
        assert intent.raw == raw

    def test_empty_entity_fallback(self, vessel_schema):
        intent = parse_intent("show everything", vessel_schema)
        # Falls back to first entity
        assert intent.entity == vessel_schema.entities[0].name


# --- AdaptiveInterface Tests ---

class TestAdaptiveInterface:
    def test_render_list(self, ai):
        spec = ai.render("show all vessels")
        assert spec.view_type == ViewType.LIST
        assert spec.entity == "vessel"
        assert len(spec.components) > 0

    def test_render_list_has_columns(self, ai):
        spec = ai.render("show vessels")
        columns = [c for c in spec.components if c.component_type == "column"]
        assert len(columns) == 5  # 5 fields on vessel entity

    def test_render_form(self, ai):
        spec = ai.render("new vessel")
        assert spec.view_type == ViewType.FORM
        inputs = [c for c in spec.components if c.component_type == "input"]
        assert len(inputs) == 5

    def test_render_form_has_submit(self, ai):
        spec = ai.render("new vessel")
        buttons = [c for c in spec.components if c.component_type == "button"]
        assert len(buttons) >= 1
        assert any("Submit" in b.label for b in buttons)

    def test_render_detail(self, ai):
        spec = ai.render("view vessel")
        assert spec.view_type == ViewType.DETAIL

    def test_render_chart(self, ai):
        spec = ai.render("chart vessels")
        assert spec.view_type == ViewType.CHART

    def test_render_preserves_filters(self, ai):
        spec = ai.render("show vessels over 50")
        assert len(spec.filters) >= 1

    def test_render_preserves_sort(self, ai):
        spec = ai.render("show vessels sorted by length desc")
        assert spec.sort is not None
        assert spec.sort.direction == "desc"

    def test_render_unknown_entity(self, ai):
        spec = ai.render("show xyz")
        # Falls back to nav list
        assert len(spec.components) > 0

    def test_render_intent_object(self, ai, vessel_schema):
        intent = parse_intent("new catch", vessel_schema)
        spec = ai.render_intent(intent)
        assert spec.view_type == ViewType.FORM
        assert spec.entity == "catch"

    def test_to_html(self, ai):
        html = ai.to_html("show vessels")
        assert "<html" in html.lower()
        assert "lcars" in html.lower()

    def test_to_markdown(self, ai):
        md = ai.to_markdown("show vessels")
        assert "# " in md
        assert "Vessel" in md or "vessel" in md

    def test_to_json(self, ai):
        j = ai.to_json("show vessels")
        data = json.loads(j)
        assert "title" in data
        assert "components" in data

    def test_form_enum_has_options(self, ai):
        spec = ai.render("new vessel")
        for c in spec.components:
            if c.component_type == "input" and c.field == "status":
                assert c.options == ["active", "docked", "maintenance"]
                assert c.input_type == "select"

    def test_form_reference_input(self, vessel_schema):
        ai = AdaptiveInterface(vessel_schema)
        spec = ai.render("new catch")
        for c in spec.components:
            if c.component_type == "input" and c.field == "vessel_id":
                assert c.input_type == "reference"
                assert c.reference == "vessel"

    def test_required_propagates_to_form_input(self, vessel_schema):
        """Regression: Field.required must propagate to InterfaceComponent.required.

        Previously the form builder dropped the required flag, so HTML output
        omitted the ``required`` attribute and the Markdown form renderer showed
        "Yes" for every field.
        """
        ai = AdaptiveInterface(vessel_schema)
        spec = ai.render("new vessel")
        inputs_by_field = {
            c.field: c for c in spec.components if c.component_type == "input"
        }
        # ``name`` is declared required=True on vessel
        assert inputs_by_field["name"].required is True
        # Fields without ``required`` default to False
        assert inputs_by_field["length"].required is False
        assert inputs_by_field["home_port"].required is False

    def test_required_renders_html_attribute(self, vessel_schema):
        """Regression: required inputs must emit the ``required`` HTML attribute."""
        ai = AdaptiveInterface(vessel_schema)
        html = ai.to_html("new vessel")
        # The required name input should include required
        name_input = 'name="name"'
        assert name_input in html
        # Find the input tag for name and verify required attribute
        import re
        m = re.search(r'<input[^>]*name="name"[^>]*>', html)
        assert m is not None
        assert "required" in m.group(0)
        # The non-required length input should NOT have required
        m = re.search(r'<input[^>]*name="length"[^>]*>', html)
        assert m is not None
        assert "required" not in m.group(0)

    def test_required_renders_markdown_column(self, vessel_schema):
        """Regression: Markdown form Required column must reflect field.required."""
        ai = AdaptiveInterface(vessel_schema)
        md = ai.to_markdown("new vessel")
        lines = md.splitlines()
        # Find the table row for the required name field
        name_row = next(ln for ln in lines if "| Vessel Name |" in ln)
        assert "Yes" in name_row
        # Find a non-required field row
        length_row = next(ln for ln in lines if "| Length |" in ln)
        # The Required column should NOT say Yes for length
        assert not length_row.endswith("| Yes |")


# --- Renderer Tests ---

class TestRenderers:
    def test_html_renderer(self, ai):
        spec = ai.render("show vessels")
        html = HTMLRenderer().render(spec)
        assert "<!DOCTYPE html>" in html
        assert "<table" in html
        assert spec.title in html

    def test_html_escapes(self):
        spec = InterfaceSpec(
            title="<script>alert(1)</script>",
            view_type=ViewType.LIST,
            components=[],
        )
        html = HTMLRenderer().render(spec)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_html_form(self, ai):
        spec = ai.render("new vessel")
        html = HTMLRenderer().render(spec)
        assert "<input" in html
        assert "<select" in html  # for enum field

    def test_html_detail(self, ai):
        spec = ai.render("view vessel")
        html = HTMLRenderer().render(spec)
        assert "lcars-detail" in html

    def test_markdown_list(self, ai):
        spec = ai.render("show vessels")
        md = MarkdownRenderer().render(spec)
        assert "| " in md  # has a table
        assert "---" in md

    def test_markdown_form(self, ai):
        spec = ai.render("new vessel")
        md = MarkdownRenderer().render(spec)
        assert "Field" in md
        assert "Type" in md

    def test_markdown_detail(self, ai):
        spec = ai.render("view vessel")
        md = MarkdownRenderer().render(spec)
        assert "**" in md  # bold labels

    def test_json_renderer(self, ai):
        spec = ai.render("show vessels")
        j = JSONRenderer().render(spec)
        data = json.loads(j)
        assert data["view_type"] == "list"
        assert "components" in data

    def test_json_renderer_indent(self, ai):
        spec = ai.render("show vessels")
        j = JSONRenderer().render(spec, indent=4)
        assert "    " in j  # 4-space indent


# --- InterfaceSpec Tests ---

class TestInterfaceSpec:
    def test_to_dict(self):
        spec = InterfaceSpec(
            title="Test",
            view_type=ViewType.LIST,
            entity="test",
            components=[InterfaceComponent(component_type="column", label="Name", field="name")],
        )
        d = spec.to_dict()
        assert d["title"] == "Test"
        assert d["view_type"] == "list"
        assert len(d["components"]) == 1

    def test_to_json(self):
        spec = InterfaceSpec(title="Test", view_type=ViewType.FORM)
        j = spec.to_json()
        data = json.loads(j)
        assert data["title"] == "Test"

    def test_to_html(self):
        spec = InterfaceSpec(title="Test", view_type=ViewType.LIST)
        html = spec.to_html()
        assert "<!DOCTYPE html>" in html

    def test_to_markdown(self):
        spec = InterfaceSpec(title="Test", view_type=ViewType.LIST)
        md = spec.to_markdown()
        assert "# Test" in md


# --- Integration Tests ---

class TestIntegration:
    def test_full_flow_list(self, vessel_schema):
        ai = AdaptiveInterface(vessel_schema)
        spec = ai.render("show active vessels over 30 sorted by length desc")
        assert spec.view_type == ViewType.LIST
        assert len(spec.filters) >= 1
        assert spec.sort is not None

    def test_full_flow_html_output(self, vessel_schema):
        ai = AdaptiveInterface(vessel_schema)
        html = ai.to_html("show vessels")
        assert "<!DOCTYPE html>" in html
        assert "lcars" in html.lower()

    def test_full_flow_json_valid(self, vessel_schema):
        ai = AdaptiveInterface(vessel_schema)
        j = ai.to_json("new vessel")
        data = json.loads(j)
        assert data["view_type"] == "form"

    def test_catch_entity_form(self, vessel_schema):
        ai = AdaptiveInterface(vessel_schema)
        spec = ai.render("new catch")
        assert spec.entity == "catch"
        assert spec.view_type == ViewType.FORM

    def test_multi_entity_schema(self, vessel_schema):
        ai = AdaptiveInterface(vessel_schema)
        v_spec = ai.render("show vessels")
        c_spec = ai.render("show catch logs")
        assert v_spec.entity == "vessel"
        assert c_spec.entity == "catch"
