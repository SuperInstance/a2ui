"""
Comprehensive tests for A2UI — Adaptive Interface.
"""

import pytest

from a2ui import (
    AdaptiveInterface,
    InterfaceSpec,
    Schema,
    FieldType,
    Intent,
    IntentParser,
    HTMLRenderer,
    MarkdownRenderer,
    JSONRenderer,
)


# ─── Test Schema ───


@pytest.fixture
def vessel_schema():
    return {
        "vessels": {
            "fields": {
                "name": {"type": "string", "label": "Vessel Name"},
                "length": {"type": "number", "unit": "ft"},
                "engine_hours": {"type": "number", "label": "Engine Hours"},
                "status": {
                    "type": "enum",
                    "options": ["active", "docked", "maintenance"],
                },
                "home_port": {"type": "string"},
            },
            "primary_key": "name",
        }
    }


@pytest.fixture
def vessel_data():
    return {
        "vessels": [
            {"name": "Ocean Rover", "length": 45, "engine_hours": 6000, "status": "active", "home_port": "Newport"},
            {"name": "Sea Sprite", "length": 32, "engine_hours": 3200, "status": "docked", "home_port": "Boston"},
            {"name": "Wave Dancer", "length": 55, "engine_hours": 8000, "status": "maintenance", "home_port": "Gloucester"},
            {"name": "Morning Star", "length": 28, "engine_hours": 1500, "status": "active", "home_port": "Portland"},
            {"name": "Storm Runner", "length": 60, "engine_hours": 7500, "status": "active", "home_port": "Newport"},
        ]
    }


@pytest.fixture
def ai(vessel_schema, vessel_data):
    return AdaptiveInterface(vessel_schema, vessel_data)


class TestSchema:
    def test_loads_entities(self, vessel_schema):
        s = Schema(vessel_schema)
        assert "vessels" in s.entities

    def test_get_entity(self, vessel_schema):
        s = Schema(vessel_schema)
        entity = s.get_entity("vessels")
        assert "fields" in entity
        assert entity["primary_key"] == "name"

    def test_get_entity_case_insensitive(self, vessel_schema):
        s = Schema(vessel_schema)
        assert s.has_entity("Vessels")
        assert s.has_entity("VESSELS")
        assert not s.has_entity("ships")

    def test_get_fields(self, vessel_schema):
        s = Schema(vessel_schema)
        fields = s.get_fields("vessels")
        assert "name" in fields
        assert fields["name"].type == FieldType.STRING
        assert fields["length"].type == FieldType.NUMBER
        assert fields["length"].unit == "ft"

    def test_field_label_generation(self, vessel_schema):
        s = Schema(vessel_schema)
        fields = s.get_fields("vessels")
        assert fields["engine_hours"].label == "Engine Hours"
        assert fields["length"].display_label == "Length (ft)"

    def test_resolve_field_name(self, vessel_schema):
        s = Schema(vessel_schema)
        assert s.resolve_field_name("vessels", "engine_hours") == "engine_hours"

    def test_enum_field(self, vessel_schema):
        s = Schema(vessel_schema)
        fields = s.get_fields("vessels")
        assert fields["status"].type == FieldType.ENUM
        assert "active" in fields["status"].options


class TestFieldType:
    def test_from_string_basic(self):
        assert FieldType.from_string("string") == FieldType.STRING
        assert FieldType.from_string("number") == FieldType.NUMBER

    def test_from_string_aliases(self):
        assert FieldType.from_string("int") == FieldType.NUMBER
        assert FieldType.from_string("bool") == FieldType.BOOLEAN
        assert FieldType.from_string("text") == FieldType.STRING

    def test_from_string_unknown(self):
        assert FieldType.from_string("unknown") == FieldType.STRING


class TestIntentParsing:
    def test_basic_action(self, vessel_schema):
        parser = IntentParser(Schema(vessel_schema))
        intent = parser.parse("show all vessels")
        assert intent.action == "show"
        assert intent.entity == "vessels"

    def test_list_action(self, vessel_schema):
        parser = IntentParser(Schema(vessel_schema))
        intent = parser.parse("list vessels")
        assert intent.action == "list"

    def test_find_action(self, vessel_schema):
        parser = IntentParser(Schema(vessel_schema))
        intent = parser.parse("find vessels")
        assert intent.action == "find"

    def test_entity_resolution(self, vessel_schema):
        parser = IntentParser(Schema(vessel_schema))
        intent = parser.parse("show me all vessels")
        assert intent.entity == "vessels"

    def test_filter_gt(self, vessel_schema):
        parser = IntentParser(Schema(vessel_schema))
        intent = parser.parse("show vessels with engine hours over 5000")
        assert len(intent.filters) == 1
        assert intent.filters[0]["field"] == "engine_hours"
        assert intent.filters[0]["op"] == "gt"
        assert intent.filters[0]["value"] == 5000

    def test_filter_lt(self, vessel_schema):
        parser = IntentParser(Schema(vessel_schema))
        intent = parser.parse("show vessels with length under 40")
        assert len(intent.filters) == 1
        assert intent.filters[0]["op"] == "lt"
        assert intent.filters[0]["value"] == 40

    def test_filter_gte(self, vessel_schema):
        parser = IntentParser(Schema(vessel_schema))
        intent = parser.parse("show vessels with engine hours at least 5000")
        assert len(intent.filters) == 1
        assert intent.filters[0]["op"] == "gte"

    def test_filter_lte(self, vessel_schema):
        parser = IntentParser(Schema(vessel_schema))
        intent = parser.parse("vessels with length at most 50")
        assert any(f["op"] == "lte" for f in intent.filters)

    def test_filter_enum(self, vessel_schema):
        parser = IntentParser(Schema(vessel_schema))
        intent = parser.parse("show active vessels")
        # Should pick up "active" as enum filter
        assert any(
            f["field"] == "status" and f["value"] == "active"
            for f in intent.filters
        )

    def test_sort_ascending(self, vessel_schema):
        parser = IntentParser(Schema(vessel_schema))
        intent = parser.parse("list vessels sorted by length ascending")
        assert intent.sort_by is not None
        assert intent.sort_by[0] == "length"
        assert intent.sort_by[1] == "asc"

    def test_sort_descending(self, vessel_schema):
        parser = IntentParser(Schema(vessel_schema))
        intent = parser.parse("show vessels sorted by engine hours descending")
        assert intent.sort_by is not None
        assert intent.sort_by[0] == "engine_hours"
        assert intent.sort_by[1] == "desc"

    def test_sort_short_form(self, vessel_schema):
        parser = IntentParser(Schema(vessel_schema))
        intent = parser.parse("vessels ordered by length desc")
        assert intent.sort_by is not None
        assert intent.sort_by[1] == "desc"

    def test_multiple_filters(self, vessel_schema):
        parser = IntentParser(Schema(vessel_schema))
        intent = parser.parse("show active vessels with engine hours over 3000")
        assert len(intent.filters) >= 2

    def test_default_action_is_show(self, vessel_schema):
        parser = IntentParser(Schema(vessel_schema))
        intent = parser.parse("vessels")
        assert intent.action == "show"

    def test_raw_text_preserved(self, vessel_schema):
        parser = IntentParser(Schema(vessel_schema))
        raw = "show me the vessels"
        intent = parser.parse(raw)
        assert intent.raw == raw


class TestAdaptiveInterface:
    def test_ask_returns_spec(self, ai):
        spec = ai.ask("show all vessels")
        assert isinstance(spec, InterfaceSpec)

    def test_view_type_table(self, ai):
        spec = ai.ask("show all vessels")
        assert spec.view_type == "table"

    def test_filter_applied(self, ai):
        spec = ai.ask("show vessels with engine hours over 5000")
        assert len(spec.data) == 3  # Ocean Rover, Wave Dancer, Storm Runner
        names = [r["name"] for r in spec.data]
        assert "Ocean Rover" in names
        assert "Sea Sprite" not in names

    def test_sort_applied(self, ai):
        spec = ai.ask("list vessels sorted by length descending")
        lengths = [r["length"] for r in spec.data]
        assert lengths == sorted(lengths, reverse=True)

    def test_sort_ascending(self, ai):
        spec = ai.ask("show vessels sorted by engine hours ascending")
        hours = [r["engine_hours"] for r in spec.data]
        assert hours == sorted(hours)

    def test_combined_filter_and_sort(self, ai):
        spec = ai.ask("show active vessels with engine hours over 3000 sorted by length desc")
        assert len(spec.data) == 2  # Ocean Rover (6000, 45ft) and Storm Runner (7500, 60ft)
        lengths = [r["length"] for r in spec.data]
        assert lengths == sorted(lengths, reverse=True)

    def test_default_columns(self, ai):
        spec = ai.ask("show all vessels")
        assert "name" in spec.columns  # primary key first

    def test_title_generated(self, ai):
        spec = ai.ask("show vessels with engine hours over 5000")
        assert "Showing vessels" in spec.title
        assert "engine_hours" in spec.title or "Engine Hours" in spec.title

    def test_empty_result(self, ai):
        spec = ai.ask("show vessels with engine hours over 99999")
        assert len(spec.data) == 0

    def test_render_html(self, ai):
        output = ai.render("show all vessels", format="html")
        assert "<table" in output
        assert "Ocean Rover" in output

    def test_render_markdown(self, ai):
        output = ai.render("show all vessels", format="markdown")
        assert "|" in output
        assert "Ocean Rover" in output

    def test_render_json(self, ai):
        output = ai.render("show all vessels", format="json")
        import json
        parsed = json.loads(output)
        assert "data" in parsed
        assert len(parsed["data"]) == 5
        assert parsed["view_type"] == "table"


class TestRenderers:
    def test_html_table(self, ai):
        spec = ai.ask("show all vessels")
        html_out = HTMLRenderer().render(spec)
        assert "<table" in html_out
        assert "</table>" in html_out

    def test_html_empty(self, ai):
        spec = ai.ask("show vessels with engine hours over 99999")
        html_out = HTMLRenderer().render(spec)
        assert "No matching records" in html_out

    def test_html_count(self, ai):
        spec = ai.ask("show all vessels")
        html_out = HTMLRenderer().render(spec)
        assert "5 record(s)" in html_out

    def test_html_sort_indicator(self, ai):
        spec = ai.ask("show vessels sorted by length desc")
        html_out = HTMLRenderer().render(spec)
        assert "↓" in html_out

    def test_markdown_table(self, ai):
        spec = ai.ask("show all vessels")
        md = MarkdownRenderer().render(spec)
        assert md.startswith("## ")
        assert "|" in md
        assert "---" in md

    def test_markdown_empty(self, ai):
        spec = ai.ask("show vessels with engine hours over 99999")
        md = MarkdownRenderer().render(spec)
        assert "No matching records" in md

    def test_json_structure(self, ai):
        spec = ai.ask("show all vessels")
        j = JSONRenderer().render(spec)
        import json
        data = json.loads(j)
        assert data["view_type"] == "table"
        assert "columns" in data
        assert "data" in data
        assert "count" in data

    def test_json_count(self, ai):
        spec = ai.ask("show all vessels")
        j = JSONRenderer().render(spec)
        import json
        data = json.loads(j)
        assert data["count"] == 5

    def test_spec_render_html(self, ai):
        spec = ai.ask("show all vessels")
        out = spec.render("html")
        assert "<table" in out

    def test_spec_render_markdown(self, ai):
        spec = ai.ask("show all vessels")
        out = spec.render("markdown")
        assert "|" in out

    def test_spec_render_json(self, ai):
        spec = ai.ask("show all vessels")
        out = spec.render("json")
        import json
        json.loads(out)  # should not raise

    def test_spec_render_bad_format(self, ai):
        spec = ai.ask("show all vessels")
        with pytest.raises(ValueError, match="Unknown format"):
            spec.render("xml")


class TestSummaryView:
    def test_summary_view(self, ai):
        spec = ai.ask("summary of all vessels")
        assert spec.view_type == "summary"
        html = spec.render("html")
        assert "Total records" in html

    def test_summary_markdown(self, ai):
        spec = ai.ask("overview of vessels")
        md = spec.render("markdown")
        assert "Total records" in md


class TestEdgeCases:
    def test_unknown_entity(self, vessel_schema):
        ai = AdaptiveInterface(vessel_schema)
        spec = ai.ask("show me the widgets")
        # Falls back to first entity
        assert spec.intent.entity in ("vessels", "")

    def test_no_filters(self, ai):
        spec = ai.ask("show vessels")
        assert len(spec.filters) == 0
        assert len(spec.data) == 5

    def test_exact_value_filter(self, ai):
        spec = ai.ask("show vessels from Newport")
        # "from" might be interpreted differently, but Newport should match
        # as a contains filter or direct match
        assert len(spec.data) >= 1

    def test_multiple_sorts_same_field(self, ai):
        spec_asc = ai.ask("vessels sorted by length ascending")
        spec_desc = ai.ask("vessels sorted by length descending")
        assert spec_asc.sort_by[1] == "asc"
        assert spec_desc.sort_by[1] == "desc"

    def test_interface_spec_repr(self, ai):
        spec = ai.ask("show all vessels")
        r = repr(spec)
        assert "InterfaceSpec" in r
        assert "table" in r


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
