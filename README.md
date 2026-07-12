# A2UI — Adaptive Interface Generation

> You don't design the interface. You describe your data, whistle your intent, and the interface generates itself.

A2UI is the adaptive interface layer of Working Animal Architecture. Instead of hand-building CRUD forms, list views, and detail pages, you define a `Schema` of your entities and let the `AdaptiveInterface` generate the right view based on natural-language intent. The output renders to HTML (LCARS-inspired), Markdown, or JSON.

## Why It Exists

Building admin interfaces is tedious and repetitive. Every new entity needs a list view, a create form, an edit form, a detail page, filters, and sorting — all mechanically derivable from the data model. Traditional admin frameworks (Django admin, Rails admin) solve this with code generation or class-based views that are hard to customize and tightly coupled to the backend.

A2UI takes a different approach: **intent-driven generation**. You don't configure which columns appear on which page. You say "show all vessels over 50ft sorted by length" and A2UI parses that intent, maps it to your schema, and generates a complete interface specification with the right columns, filters, sort order, and row actions. The spec is an intermediate representation — render it however you want.

| Traditional Admin | A2UI |
|-------------------|------|
| Configure views per entity | Describe schema once |
| Write forms, columns, filters by hand | Express intent in natural language |
| Tightly coupled to backend framework | Renders to HTML, Markdown, or JSON |
| New view = new code | New view = new intent string |

## Installation

```bash
pip install a2ui
```

Requires Python 3.10+. No external dependencies.

## Quick Start

```python
from a2ui import AdaptiveInterface, Schema, Entity, Field, FieldType

# 1. Define your data schema
schema = Schema(entities=[
    Entity(
        name="vessel",
        label="Fishing Vessel",
        fields=[
            Field(name="name", type=FieldType.TEXT, label="Vessel Name", required=True),
            Field(name="length", type=FieldType.NUMBER, label="Length", unit="ft"),
            Field(name="home_port", type=FieldType.TEXT, label="Home Port"),
            Field(name="status", type=FieldType.ENUM, label="Status",
                  options=["active", "docked", "maintenance"]),
            Field(name="tonnage", type=FieldType.NUMBER, label="Gross Tonnage"),
        ],
    ),
    Entity(
        name="catch",
        label="Catch Log",
        fields=[
            Field(name="species", type=FieldType.TEXT),
            Field(name="pounds", type=FieldType.NUMBER, unit="lbs"),
            Field(name="date", type=FieldType.DATE),
            Field(name="vessel", type=FieldType.REFERENCE, reference="vessel"),
        ],
    ),
])

# 2. Create the adaptive interface
ai = AdaptiveInterface(schema)

# 3. Express intent — A2UI figures out the rest
html = ai.to_html("show all active vessels sorted by length descending")
print(html)  # Complete LCARS-styled HTML document with table, filters, sort

# Different intents generate different views
form_html = ai.to_html("new vessel")              # → create form
detail_md = ai.to_markdown("view vessel")          # → detail view in Markdown
chart_html = ai.to_html("chart vessels by tonnage") # → chart placeholder
data = ai.to_json("list catch where pounds over 5000")  # → structured JSON
```

## How Intent Parsing Works

A2UI uses keyword-matching heuristics (no NLP dependencies) to map natural language to structured `Intent` objects:

```
"show all vessels over 50ft sorted by length"
                    │              │           │
                    ▼              ▼           ▼
              Filter:        Filter:      Sort:
              status=active  length>50    length asc
```

### Action Keywords

| Keyword(s) | Action | View Type |
|------------|--------|-----------|
| show, list, display, dashboard | `list` | LIST |
| view, see | `detail` | DETAIL |
| new, add, create | `create` | FORM |
| edit, modify, update | `edit` | FORM |
| delete, remove | `delete` | LIST |
| chart, plot, graph | `chart` | CHART |

### Filter Syntax

| Expression | Parsed As |
|------------|-----------|
| `over 50` | `gt 50` |
| `under 100` | `lt 100` |
| `at least 10` | `gte 10` |
| `at most 5` | `lte 5` |
| `status is active` | `eq "active"` |
| `status = active` | `eq "active"` |

### Sort Syntax

| Expression | Parsed As |
|------------|-----------|
| `sorted by length` | `Sort(length, asc)` |
| `sorted by length descending` | `Sort(length, desc)` |
| `order by tonnage asc` | `Sort(tonnage, asc)` |

## Architecture

```
 Natural Language Intent
         │
         ▼
┌─────────────────┐
│  Intent Parser  │  ← keyword heuristics, schema-aware field resolution
│  (intent.py)    │     produces Intent{action, entity, filters, sort}
└────────┬────────┘
         │  Intent
         ▼
┌─────────────────┐
│ AdaptiveInterface│ ← maps intent → view type, builds components
│ (interface.py)  │    produces InterfaceSpec
└────────┬────────┘
         │  InterfaceSpec
         ▼
┌─────────────────┐
│    Renderers    │  ← HTMLRenderer (LCARS), MarkdownRenderer, JSONRenderer
│ (renderers.py)  │
└─────────────────┘
```

### Intermediate Representation

The `InterfaceSpec` is the key abstraction — it's a fully-resolved description of the interface, independent of output format:

```python
spec = ai.render("show vessels over 100ft")
# spec.title = "Fishing Vessels"
# spec.view_type = ViewType.LIST
# spec.entity = "vessel"
# spec.filters = [Filter(field="length", operator="gt", value=100)]
# spec.components = [
#     InterfaceComponent(component_type="column", label="Vessel Name", field="name", sortable=True),
#     InterfaceComponent(component_type="column", label="Length", field="length", sortable=True),
#     InterfaceComponent(component_type="column", label="Home Port", ...),
#     InterfaceComponent(component_type="actions", label="Actions", actions=[...]),
# ]
```

This decouples intent from presentation. Add new renderers (React, Vue, terminal) without touching the intent parser.

## API Reference

### `AdaptiveInterface(schema: Schema)`

The main entry point.

| Method | Returns | Description |
|--------|---------|-------------|
| `render(intent_str)` | `InterfaceSpec` | Parse natural language and build interface |
| `render_intent(intent)` | `InterfaceSpec` | Build interface from pre-parsed `Intent` |
| `to_html(intent_str)` | `str` | Convenience: render → HTML |
| `to_markdown(intent_str)` | `str` | Convenience: render → Markdown |
| `to_json(intent_str)` | `str` | Convenience: render → JSON |

### `Schema`, `Entity`, `Field`

```python
Schema(entities=[...])
Entity(name="vessel", label="Vessel", fields=[...], primary_key="name")
Field(name="length", type=FieldType.NUMBER, label="Length", unit="ft",
      required=True, options=None, reference=None, default=None)
```

### `FieldType`

| Value | Use For | HTML Input |
|-------|---------|------------|
| `TEXT` | Strings, names | `<input type="text">` |
| `NUMBER` | Quantities, measurements | `<input type="number">` |
| `DATE` | Dates | `<input type="date">` |
| `ENUM` | Fixed choices | `<select>` |
| `REFERENCE` | Foreign keys | reference picker |

### `ViewType`

| Value | Generated Components |
|-------|---------------------|
| `LIST` | Table columns, row actions, filter/sort display |
| `FORM` | Input fields with types, submit button |
| `DETAIL` | Read-only field display, edit button |
| `CHART` | Chart axis with numeric fields |
| `DASHBOARD` | Card grid |

### `InterfaceSpec`

The intermediate representation.

| Method | Returns |
|--------|---------|
| `to_dict()` | `dict` |
| `to_json(indent=2)` | `str` |
| `to_html()` | `str` (via `HTMLRenderer`) |
| `to_markdown()` | `str` (via `MarkdownRenderer`) |

### Renderers

| Renderer | Output |
|----------|--------|
| `HTMLRenderer` | Self-contained HTML document with inline LCARS-inspired CSS (dark background, bold colors, rounded bars) |
| `MarkdownRenderer` | Clean Markdown with tables, field lists, and bold actions |
| `JSONRenderer` | Structured JSON for programmatic consumption |

## Testing

```bash
git clone https://github.com/SuperInstance/a2ui.git
cd a2ui
pip install -e ".[dev]"
pytest

# With coverage
pytest --cov=a2ui --cov-report=term-missing
```

## Ecosystem

| Repo | Role |
|------|------|
| **`SuperInstance/a2ui`** | **Adaptive interface generation — this repo** |
| `SuperInstance/whistle` | Intent DSL — could use A2UI for admin surfaces |
| `SuperInstance/trawl` | Commercial fishing — A2UI can generate vessel/catch UIs |
| `SuperInstance/shepherds-console` | Operations dashboard (complementary visualization) |
| `SuperInstance/baton` | Generational handoff |
| `SuperInstance/PLATO` | Conversation rooms |
| `SuperInstance/conservation` | Fences |
| `SuperInstance/flux` | Model routing |

## Philosophy

The name comes from working animals — a shepherd's whistle, a falconer's cue. You don't micromanage the dog; you give a cue and the dog figures out the terrain. A2UI does the same for interfaces: you whistle your intent, the system figures out the buttons, fields, filters, and layout.

Traditional UI frameworks assume the developer knows exactly what interface the user needs before the user does. A2UI assumes the opposite — the user knows what they want to see ("show me vessels over 50ft"), and the interface should assemble itself to match. The `InterfaceSpec` intermediate representation ensures the same intent can produce radically different surfaces — an HTML admin panel, a Markdown report, a JSON API response — without changing the intent parser.

The LCARS aesthetic isn't decoration. It's a statement: this interface was generated, not designed. It looks like a computer readout because it was produced by a computer reading your intent.

## License

MIT
