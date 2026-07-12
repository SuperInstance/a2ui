# A2UI — Adaptive Interface

> The whistle layer of Working Animal Architecture. Describe your data, state your intent, get an interface.

[![Python](https://img.shields.io/python/required-version-toml?toml=pyproject.toml)](https://python.org)
[![License](https://img.shields.io/github/license/SuperInstance/a2ui)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](tests/)

You don't design UI. You describe your data, say what you want to do with it, and the interface generates itself. A2UI reads a schema, parses a natural-language intent string, and produces a structured `InterfaceSpec` that can render to HTML, Markdown, or JSON. It's LCARS-inspired — the computer figures out the buttons, fields, and layout. You just tell it what you need.

## What It Does

A2UI takes a declarative schema (entities, fields, relationships) and a natural-language intent string like "show all active vessels over 50ft" and produces a structured interface specification. The intent parser uses heuristic keyword matching — no external NLP dependencies, no API calls. It detects the action (list, create, edit, detail, chart), the target entity, filters, sort directives, and view hints from plain English.

The generated `InterfaceSpec` contains typed components (form fields, list columns, navigation items, chart axes) that render to any output format. The built-in renderers cover HTML (for web dashboards), Markdown (for docs and terminals), and JSON (for programmatic consumption or handoff to a frontend framework). The architecture is intentionally renderer-agnostic — you can write a custom renderer for React, Vue, or a TUI without touching the core.

This is the "whistle" layer of [Working Animal Architecture](https://github.com/SuperInstance/AI-Writings): the shepherd whistles an intent, the system figures out the terrain. In a working animal infrastructure, A2UI sits between the data layer (schemas, registries) and the operator (the shepherd's console, web dashboards, or downstream applications).

## Install

```bash
pip install a2ui
```

For development:

```bash
git clone https://github.com/SuperInstance/a2ui.git
cd a2ui
pip install -e ".[dev]"
```

## Quick Start

```python
from a2ui import AdaptiveInterface, Schema, Entity, Field

schema = Schema(
    entities=[
        Entity(
            name="vessel",
            fields=[
                Field(name="name", type="text", label="Vessel Name", required=True),
                Field(name="length", type="number", unit="ft"),
                Field(name="home_port", type="text"),
                Field(name="status", type="enum",
                      options=["active", "docked", "maintenance"]),
            ],
        ),
        Entity(
            name="catch_log",
            fields=[
                Field(name="species", type="enum",
                      options=["cod", "haddock", "tuna"]),
                Field(name="pounds", type="number", unit="lbs", required=True),
                Field(name="vessel", type="reference", reference="vessel"),
                Field(name="date", type="date"),
            ],
        ),
    ],
)

ai = AdaptiveInterface(schema)

# Natural language in, structured interface out
spec = ai.render("show all active vessels sorted by length")
print(spec.to_html())

# Create forms
form = ai.render("new catch log entry")
print(form.to_markdown())

# Charts
chart = ai.render("chart catch log by species")
print(chart.to_json())
```

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                     A2UI Pipeline                     │
│                                                       │
│   "show all active vessels sorted by length"         │
│                       │                               │
│                       ▼                               │
│   ┌──────────┐   ┌───────────┐   ┌──────────────┐   │
│   │  Schema  │──▶│  Intent   │──▶│  Interface   │   │
│   │ (entity  │   │  Parser   │   │  Builder     │   │
│   │  model)  │   │ (heuristic│   │ (spec factory)│   │
│   └──────────┘   │  keyword  │   └──────┬───────┘   │
│                  │  matching)│          │            │
│                  └───────────┘          │            │
│                                         ▼            │
│                              ┌──────────────────┐    │
│                              │  InterfaceSpec   │    │
│                              │  (components,    │    │
│                              │   view type,     │    │
│                              │   filters, sort) │    │
│                              └────┬─────┬───────┘    │
│                    ┌──────────────┤     │            │
│                    ▼              ▼     ▼            │
│              ┌─────────┐  ┌─────────┐ ┌──────┐      │
│              │  HTML   │  │Markdown │ │ JSON │      │
│              │Renderer │  │Renderer │ │Render│      │
│              └─────────┘  └─────────┘ └──────┘      │
└──────────────────────────────────────────────────────┘
```

### Pipeline Stages

1. **Schema** — Define entities, fields (text, number, date, enum, reference), and relationships
2. **Intent Parser** — Heuristic keyword matching extracts action, entity, filters, sort, and view hints
3. **Interface Builder** — Selects the appropriate view (list, form, detail, chart, dashboard) and generates typed `InterfaceComponent`s
4. **Renderers** — Convert `InterfaceSpec` to HTML, Markdown, or JSON

## API Reference

### `AdaptiveInterface`

```python
class AdaptiveInterface:
    def __init__(self, schema: Schema)
    def render(self, intent_str: str) -> InterfaceSpec
    def render_intent(self, intent: Intent) -> InterfaceSpec
```

The main entry point. Give it a schema, then call `render()` with a natural-language string.

### `Schema`, `Entity`, `Field`

```python
@dataclass
class Schema:
    entities: list[Entity]
    def get_entity(self, name: str) -> Entity | None

@dataclass
class Entity:
    name: str
    fields: list[Field]
    label: str | None = None

@dataclass
class Field:
    name: str
    type: FieldType | str       # text, number, date, enum, reference
    label: str | None = None
    required: bool = False
    unit: str | None = None
    options: list[str] | None = None
    reference: str | None = None
    default: Any = None
```

### `Intent` and `parse_intent`

```python
@dataclass
class Intent:
    action: str          # list, create, edit, detail, delete, chart
    entity: str          # target entity name
    filters: list[Filter]
    sort: Sort | None
    raw: str             # original input
    view_hint: ViewType | None

def parse_intent(text: str, schema: Schema) -> Intent
```

The intent parser detects:
- **Actions**: "show/list/display" → list, "new/create/add" → create, "edit/update" → edit, "chart/graph/plot" → chart
- **Filters**: "over 50ft" → `length > 50`, "active" → `status == "active"`
- **Sort**: "sorted by length" → `Sort(field="length")`, "longest first" → `Sort(field="length", direction="desc")`

### `InterfaceSpec`

```python
@dataclass
class InterfaceSpec:
    title: str
    view_type: ViewType       # list, detail, form, dashboard, chart
    components: list[InterfaceComponent]
    intent: Intent

    def to_html(self) -> str
    def to_markdown(self) -> str
    def to_json(self) -> str
```

### Renderers

```python
from a2ui import HTMLRenderer, MarkdownRenderer, JSONRenderer

HTMLRenderer().render(spec)       # Full HTML page with inline CSS
MarkdownRenderer().render(spec)   # GitHub-flavored Markdown table/list
JSONRenderer().render(spec)       # Structured JSON for API consumption
```

## Testing

```bash
# Install with test dependencies
pip install -e ".[dev]"

# Run the full suite
pytest tests/ -v

# Run specific module tests
pytest tests/test_intent.py -v
pytest tests/test_schema.py -v
```

## Philosophy

A2UI embodies a core principle of Working Animal Architecture: **the operator states intent, the system figures out the interface**. This is the shepherd's whistle — you don't micromanage the dog's paw placement, you give a cue and the dog reads the terrain. Similarly, you don't hand-craft every form and table. You describe your data, whistle your intent, and A2UI generates the appropriate interface.

The LCARS inspiration is deliberate: in Star Trek, crew members don't design their consoles — the computer adapts the interface to the task at hand. A2UI brings that philosophy to real software, treating UI as a derived artifact of schema + intent rather than a hand-built artifact.

For more, see [AI-Writings](https://github.com/SuperInstance/AI-Writings) — essays, fiction, and poetry on the Working Animal Architecture paradigm.

## Ecosystem

| Repo | Role |
|------|------|
| **[a2ui](https://github.com/SuperInstance/a2ui)** | **This repo** — adaptive interface generation |
| [shepherds-console](https://github.com/SuperInstance/shepherds-console) | Operations dashboard (uses A2UI for panel rendering) |
| [whistle](https://github.com/SuperInstance/whistle) | Intent DSL — structured alternative to natural-language intents |
| [breed-registry](https://github.com/SuperInstance/breed-registry) | Model selection (A2UI can render breed comparison interfaces) |
| [pedigree](https://github.com/SuperInstance/pedigree) | Lineage tracking (A2UI can render bloodline trees) |
| [trawl](https://github.com/SuperInstance/trawl) | Commercial fishing operation (real-world A2UI consumer) |

## License

MIT — see [LICENSE](LICENSE).
