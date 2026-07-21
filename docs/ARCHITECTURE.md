# A2UI Architecture

> How intent becomes interface, and why the pieces are where they are.

A2UI is the **Whistle Layer** of [Working Animal Architecture](https://github.com/SuperInstance) — the way a human operator communicates *what they want to see* to the system without hand-building each view. The architecture reflects that: a small, intent-shaped surface on the input side, an intermediate spec that's deliberately format-agnostic in the middle, and pluggable renderers on the output side.

---

## 1. The Layer Model

A2UI is divided into four layered components, each in its own module:

```
┌──────────────────────────────────────────────────────────┐
│                       USER INTENT                        │
│       "show active vessels over 50ft sorted by length"   │
└────────────────────────┬─────────────────────────────────┘
                         │
        ╔════════════════╧════════════════╗
        ║   1. Intent  (intent.py)        ║   keyword parser
        ║      parse_intent(text, schema) ║
        ╚════════════════╤════════════════╝
                         │
                         ▼  Intent(action, entity, filters, sort)
        ┌────────────────┴────────────────┐
        │   2. Schema  (schema.py)       │   data-shape description
        │      Schema → Entity → Field   │
        └────────────────┬────────────────┘
                         │
                         ▼  Intent + Schema
        ╔════════════════╧════════════════╗
        ║   3. AdaptiveInterface          ║
        ║      (interface.py + __init__)  ║   builder
        ║      render(intent) → spec     ║
        ╚════════════════╤════════════════╝
                         │
                         ▼  InterfaceSpec { title, view_type, components, filters, sort }
        ┌────────────────┴────────────────┐
        │   4. Renderers (renderers.py)   │   output adapters
        │      HTML / Markdown / JSON     │
        └─────────────────────────────────┘
                         │
                         ▼
                   final string output
```

### Layer 1 — Intent Parser (`intent.py`)

**Role.** Maps a natural-language string to a structured `Intent` object.

**Mechanism.** Regex-based keyword matching, schema-aware field resolution. **No** external NLP, ML, or LLM dependency — input works offline, deterministically, and is fully testable.

**Why.** Coupling intent parsing to a model would lose the offline-and-deterministic property. The heuristic parser is enough for the shape of input admins actually type ("show vessels over 50ft"), and it stays auditable.

**Outputs.** An `Intent` carrying:
- `action` — one of `list`, `create`, `edit`, `detail`, `delete`, `chart`
- `entity` — resolved schema entity (with plural/label tolerance)
- `filters` — list of `Filter(field, operator, value)`
- `sort` — optional `Sort(field, direction)`
- `view_hint` — optional `ViewType` derived from action
- `raw` — the original string (kept for round-tripping)

### Layer 2 — Schema (`schema.py`)

**Role.** Describes what data exists. Schema is the contract between the data layer (whatever backend stores it) and the interface layer.

**Why a separate layer?** The schema is the only piece a developer writes once and reuses across many views. Without it, every intent would have to re-declare what fields exist. With it, the intent parser can resolve "vessels" → entity, "over 50ft" → numeric filter, and "sorted by length" → sort directive, all automatically.

**Types.** `Schema → Entity → Field`, with `FieldType` enum (`TEXT`, `NUMBER`, `DATE`, `ENUM`, `REFERENCE`) and `ViewType` enum (`LIST`, `DETAIL`, `FORM`, `CHART`, `DASHBOARD`).

### Layer 3 — AdaptiveInterface (`interface.py` + `__init__.py`)

**Role.** The orchestrator. Takes an `Intent` (parsed or pre-built), consults the schema, and produces an `InterfaceSpec`.

**Why an intermediate spec, not direct rendering?** Because the spec is the natural API surface for everything *else* a developer might want to do with A2UI:
- Custom renderers (React, Vue, terminal, PDF, JSON API responses)
- Server-side specs sent to JS clients
- Tests that assert on spec structure without parsing strings
- Reusing the same intent for multiple output formats

`InterfaceSpec` and its `InterfaceComponent` parts are intentionally simple dataclasses so anyone can produce, consume, or transform them.

### Layer 4 — Renderers (`renderers.py`)

**Role.** Turn an `InterfaceSpec` into a final string.

**Three built-ins:**
- `HTMLRenderer` — self-contained LCARS-styled document with inline CSS
- `MarkdownRenderer` — tables, field lists, bold actions
- `JSONRenderer` — wraps `spec.to_dict()` in `json.dumps`

**Extensible.** Subclass `BaseRenderer` and implement `render(spec)`. Wire it up via `spec.to_html()` / `spec.to_markdown()` etc., or call your renderer directly.

---

## 2. The Whistle Metaphor

A shepherd doesn't hand a dog a turn-by-turn itinerary. The shepherd **whistles a cue** ("go round up the flock"), and the dog figures out the terrain.

A2UI is the whistle. The user expresses *what they want to see*, not *how to assemble the widgets*. The system translates the whistle into a fully-specified interface. Different whistles produce different surfaces; the same whistle can produce HTML, Markdown, or JSON depending on who is listening.

This is more than a branding choice. It has concrete consequences:

- **Developers don't write `views.py`.** They write a `Schema` and stop.
- **Users don't fight the form.** They say "show vessels over 50ft" and it works.
- **The interface is ephemeral.** A new intent = a new spec = a new view. No router. No controller. No migration.
- **The output format is a choice.** Same spec, three renderers. Tomorrow, React.

The LCARS aesthetic is a visual reminder of this: the interface is *generated*, not designed — it looks like a computer readout because that's what it is.

---

## 3. The Three Pluggable Boundaries

A2UI exposes three extension points, one at each layer transition.

### 3.1 Intent parser — `parse_intent`

```python
from a2ui.intent import Intent

def custom_intent(text: str, schema: Schema) -> Intent:
    # Domain-specific parser: maybe pulls action + entity from a JWT claim,
    # or runs a fast local model on edge. Anything that returns Intent.
    ...

ai = AdaptiveInterface(schema)
intent = custom_intent(user_input, schema)
spec = ai.render_intent(intent)
```

The contract is just "returns an `Intent`". If you have a custom grammar (or a fine-tuned model), write a parser and use it.

### 3.2 Spec builder — `_build_*` methods

```python
from a2ui import AdaptiveInterface
from a2ui.interface import InterfaceSpec

class MyInterface(AdaptiveInterface):
    def _build_list(self, entity, intent):
        spec = super()._build_list(entity, intent)
        # Add a "Download CSV" button to every list view
        spec.components.append(
            InterfaceComponent(
                component_type="button",
                label="Download CSV",
                action=f"export {entity.name} csv",
                variant="secondary",
            )
        )
        return spec
```

Or use composition:

```python
ai = AdaptiveInterface(schema)
spec = ai.render("show vessels")
spec.components.append(my_extra_button)
```

### 3.3 Renderers — `BaseRenderer`

```python
from a2ui.renderers import BaseRenderer

class ReactRenderer(BaseRenderer):
    def render(self, spec):
        # Walk spec.components, emit JSX.
        ...
```

Or wrap a generated spec in a server-rendered response:

```python
@app.route("/ui")
def ui():
    intent = request.args.get("intent", "show vessels")
    spec = ai.render(intent)
    return spec.to_html()  # or render via React/HTMX/etc.
```

---

## 4. Data Flow: A Worked Example

Trace `"show active vessels over 50ft sorted by length desc"` through the system.

1. **User input:** `"show active vessels over 50ft sorted by length desc"`
2. **Parser output:**
   ```python
   Intent(
       action="list",
       entity="vessel",
       filters=[
           Filter(field="length", operator="gt", value=50.0),
       ],
       sort=Sort(field="length", direction="desc"),
       raw="show active vessels over 50ft sorted by length desc",
       view_hint=ViewType.LIST,
   )
   ```
   *Note: `status="active"` *would* be in filters too if `status` had been used — the equality parser is `"<field> is <value>"` syntax. The current string "active vessels" doesn't match that pattern.*
3. **AdaptiveInterface decision:** action == `list` → `_build_list`.
4. **Spec produced:**
   ```python
   InterfaceSpec(
       title="Vessels",
       view_type=ViewType.LIST,
       entity="vessel",
       components=[
           InterfaceComponent("column", "Vessel Name", field="name", sortable=True),
           InterfaceComponent("column", "Length", field="length", sortable=True),
           # ... one column per field ...
           InterfaceComponent("actions", "Actions", actions=[
               {"label": "View", "action": "detail vessel"},
               {"label": "Edit", "action": "edit vessel"},
           ]),
       ],
       filters=[Filter(field="length", operator="gt", value=50.0)],
       sort=Sort(field="length", direction="desc"),
       intent=Intent(...),
   )
   ```
5. **Renderer chosen:** user calls `ai.to_html(spec)` or `spec.to_html()`.
6. **Final string:** a complete HTML document with the LCARS styling, a `<table>` matching the components, header rows showing sort direction, and a filter chip for `length > 50.0`.

---

## 5. Where A2UI Stops

A2UI **generates the spec and renders it.** It does **not**:

- Connect to a database. (You bring the data; A2UI tells you how to display it.)
- Handle form submission. (The HTML it produces is unopinionated about your backend.)
- Implement a router. (Each render is independent. Higher-level routing is your concern.)
- Bundle JavaScript. (LCARS HTML is static; if you want interactivity, render to React/Vue/HTMX and own that wiring.)

This keeps the core small, predictable, and easy to drop into any stack: web framework, CLI tool, or LLM agent pipeline.

---

## 6. Component Type Reference

`InterfaceComponent.component_type` is the vocabulary renderers understand.

| Type | Used in | Carries |
|------|---------|---------|
| `column` | LIST | `label`, `field`, `sortable` |
| `field` | DETAIL | `label`, `field` |
| `input` | FORM | `label`, `field`, `input_type`, `options`, `reference`, `default`, `required` |
| `button` | FORM / DETAIL | `label`, `action`, `variant` |
| `actions` | LIST | `label`, `actions: [{label, action}]` |
| `chart_axis` | CHART | `label`, `fields: [field_names]` |
| `nav_item` | LIST (fallback) | `label`, `action` |
| `card` | DASHBOARD | `label`, `field` |

Renderers should gracefully ignore unknown types. Adding a new type means teaching each renderer to handle it (or letting it pass through as silent).

---

## 7. Design Choices Worth Knowing

- **Dataclasses over Pydantic.** Smaller dependency surface, instant startup, easier to mutate specs.
- **No template engine.** HTML is built by f-strings because the output is small and the LCARS CSS ships inline.
- **`str` Enum subclass.** `FieldType.TEXT == "text"` so JSON round-trips naturally.
- **`__post_init__` for sensible defaults.** `field.label` defaults from `name.replace("_", " ").title()`; entity primary_key defaults to first field.
- **Action keywords are a flat dict.** Easy to read, easy to extend, but doesn't support multi-word commands. If your users need richer commands ("give me a CSV of…"), subclass `parse_intent`.

---

## Related Docs

- [API Reference](API.md) — every public symbol documented
- [Examples](EXAMPLES.md) — three working examples
- [Contributing](CONTRIBUTING.md) — how to extend A2UI
